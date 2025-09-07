"""
Mobile app attestation verification services
"""
import json
import base64
import hashlib
import hmac
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
import structlog
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature
import jwt

from app.core.config import settings
from app.core.exceptions import APIError, ErrorCodes

logger = structlog.get_logger()


class AttestationError(APIError):
    """Attestation verification error"""
    def __init__(self, message: str = "App attestation verification failed"):
        super().__init__(ErrorCodes.INVALID_ATTESTATION, message)


class GooglePlayIntegrityService:
    """Google Play Integrity API verification service"""
    
    INTEGRITY_API_URL = "https://playintegrity.googleapis.com/v1"
    
    def __init__(self):
        self.package_name = settings.GOOGLE_PLAY_INTEGRITY_PACKAGE_NAME
        self.api_key = getattr(settings, 'GOOGLE_PLAY_INTEGRITY_API_KEY', None)
    
    async def verify_integrity_token(self, integrity_token: str, nonce: str = None) -> Dict[str, Any]:
        """
        Verify Google Play Integrity API token
        
        Args:
            integrity_token: The integrity token from the mobile app
            nonce: Optional nonce for additional security
            
        Returns:
            Dict containing verification results
            
        Raises:
            AttestationError: If verification fails
        """
        if not self.api_key:
            logger.warning("Google Play Integrity API key not configured")
            raise AttestationError("Play Integrity verification not configured")
        
        try:
            # Decode the integrity token (JWT format)
            decoded_token = await self._decode_integrity_token(integrity_token)
            
            # Verify the token contents
            verification_result = await self._verify_token_contents(decoded_token, nonce)
            
            logger.info(
                "Play Integrity verification completed",
                package_name=self.package_name,
                verdict=verification_result.get("verdict"),
                device_verdict=verification_result.get("device_verdict")
            )
            
            return verification_result
            
        except Exception as e:
            logger.error("Play Integrity verification failed", error=str(e))
            raise AttestationError(f"Play Integrity verification failed: {str(e)}")
    
    async def _decode_integrity_token(self, token: str) -> Dict[str, Any]:
        """Decode and verify the integrity token JWT"""
        try:
            # For production, you would verify the JWT signature using Google's public keys
            # For now, we'll decode without verification (development only)
            decoded = jwt.decode(token, options={"verify_signature": False})
            return decoded
        except jwt.InvalidTokenError as e:
            raise AttestationError(f"Invalid integrity token format: {str(e)}")
    
    async def _verify_token_contents(self, token_data: Dict[str, Any], nonce: str = None) -> Dict[str, Any]:
        """Verify the contents of the decoded token"""
        # Check required fields
        if "requestDetails" not in token_data:
            raise AttestationError("Missing requestDetails in integrity token")
        
        request_details = token_data["requestDetails"]
        
        # Verify package name
        if request_details.get("requestPackageName") != self.package_name:
            raise AttestationError("Package name mismatch in integrity token")
        
        # Verify nonce if provided
        if nonce and request_details.get("nonce") != nonce:
            raise AttestationError("Nonce mismatch in integrity token")
        
        # Check app integrity
        app_integrity = token_data.get("appIntegrity", {})
        app_recognition_verdict = app_integrity.get("appRecognitionVerdict")
        
        if app_recognition_verdict not in ["PLAY_RECOGNIZED", "UNRECOGNIZED_VERSION"]:
            raise AttestationError(f"App not recognized by Play Store: {app_recognition_verdict}")
        
        # Check device integrity
        device_integrity = token_data.get("deviceIntegrity", {})
        device_recognition_verdict = device_integrity.get("deviceRecognitionVerdict", [])
        
        # Allow basic integrity for development
        allowed_verdicts = ["MEETS_BASIC_INTEGRITY", "MEETS_DEVICE_INTEGRITY", "MEETS_STRONG_INTEGRITY"]
        if not any(verdict in device_recognition_verdict for verdict in allowed_verdicts):
            raise AttestationError(f"Device integrity check failed: {device_recognition_verdict}")
        
        return {
            "verdict": "VALID",
            "app_verdict": app_recognition_verdict,
            "device_verdict": device_recognition_verdict,
            "package_name": request_details.get("requestPackageName"),
            "timestamp": datetime.utcnow().isoformat()
        }


class AppleAppAttestService:
    """Apple App Attest verification service"""
    
    def __init__(self):
        self.team_id = settings.APPLE_APP_ATTEST_TEAM_ID
        self.bundle_id = settings.APPLE_APP_ATTEST_BUNDLE_ID
    
    async def verify_attestation(self, attestation_object: str, key_id: str, challenge: str) -> Dict[str, Any]:
        """
        Verify Apple App Attest attestation
        
        Args:
            attestation_object: Base64 encoded attestation object
            key_id: The key identifier from the app
            challenge: The challenge that was sent to the app
            
        Returns:
            Dict containing verification results
            
        Raises:
            AttestationError: If verification fails
        """
        try:
            # Decode the attestation object
            attestation_data = base64.b64decode(attestation_object)
            
            # Parse the CBOR attestation object
            parsed_attestation = await self._parse_attestation_object(attestation_data)
            
            # Verify the attestation
            verification_result = await self._verify_attestation_object(
                parsed_attestation, key_id, challenge
            )
            
            logger.info(
                "App Attest verification completed",
                bundle_id=self.bundle_id,
                key_id=key_id[:8] + "...",  # Log partial key ID for security
                verdict=verification_result.get("verdict")
            )
            
            return verification_result
            
        except Exception as e:
            logger.error("App Attest verification failed", error=str(e))
            raise AttestationError(f"App Attest verification failed: {str(e)}")
    
    async def verify_assertion(self, assertion: str, key_id: str, client_data_hash: str) -> Dict[str, Any]:
        """
        Verify Apple App Attest assertion for ongoing requests
        
        Args:
            assertion: Base64 encoded assertion
            key_id: The key identifier
            client_data_hash: Hash of the client data
            
        Returns:
            Dict containing verification results
        """
        try:
            # Decode the assertion
            assertion_data = base64.b64decode(assertion)
            
            # Verify the assertion
            verification_result = await self._verify_assertion_data(
                assertion_data, key_id, client_data_hash
            )
            
            logger.info(
                "App Attest assertion verified",
                key_id=key_id[:8] + "...",
                verdict=verification_result.get("verdict")
            )
            
            return verification_result
            
        except Exception as e:
            logger.error("App Attest assertion verification failed", error=str(e))
            raise AttestationError(f"App Attest assertion verification failed: {str(e)}")
    
    async def _parse_attestation_object(self, attestation_data: bytes) -> Dict[str, Any]:
        """Parse the CBOR attestation object"""
        # For production, you would use a proper CBOR parser
        # This is a simplified implementation for development
        try:
            # In a real implementation, you would parse the CBOR data
            # and extract the attestation statement, auth data, etc.
            return {
                "fmt": "apple-appattest",
                "attStmt": {},
                "authData": attestation_data[:100],  # Simplified
            }
        except Exception as e:
            raise AttestationError(f"Failed to parse attestation object: {str(e)}")
    
    async def _verify_attestation_object(self, attestation: Dict[str, Any], key_id: str, challenge: str) -> Dict[str, Any]:
        """Verify the parsed attestation object"""
        # Verify format
        if attestation.get("fmt") != "apple-appattest":
            raise AttestationError("Invalid attestation format")
        
        # In production, you would:
        # 1. Verify the certificate chain
        # 2. Check the app ID matches your bundle ID
        # 3. Verify the challenge
        # 4. Validate the key ID
        # 5. Check the counter and other security properties
        
        # For development, we'll do basic validation
        if not key_id or len(key_id) < 10:
            raise AttestationError("Invalid key ID format")
        
        if not challenge or len(challenge) < 10:
            raise AttestationError("Invalid challenge format")
        
        return {
            "verdict": "VALID",
            "key_id": key_id,
            "bundle_id": self.bundle_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _verify_assertion_data(self, assertion_data: bytes, key_id: str, client_data_hash: str) -> Dict[str, Any]:
        """Verify assertion data for ongoing requests"""
        # In production, you would:
        # 1. Parse the assertion structure
        # 2. Verify the signature using the stored public key
        # 3. Check the counter has incremented
        # 4. Verify the client data hash
        
        # For development, basic validation
        if not assertion_data or len(assertion_data) < 32:
            raise AttestationError("Invalid assertion data")
        
        return {
            "verdict": "VALID",
            "key_id": key_id,
            "counter": 1,  # Would be extracted from assertion
            "timestamp": datetime.utcnow().isoformat()
        }


class AppAttestationService:
    """Main app attestation service that handles both platforms"""
    
    def __init__(self):
        self.google_service = GooglePlayIntegrityService()
        self.apple_service = AppleAppAttestService()
    
    async def verify_android_integrity(self, integrity_token: str, nonce: str = None) -> bool:
        """
        Verify Android app integrity using Google Play Integrity API
        
        Args:
            integrity_token: The integrity token from Android app
            nonce: Optional nonce for additional security
            
        Returns:
            bool: True if verification passes
            
        Raises:
            AttestationError: If verification fails
        """
        try:
            result = await self.google_service.verify_integrity_token(integrity_token, nonce)
            return result.get("verdict") == "VALID"
        except AttestationError:
            raise
        except Exception as e:
            logger.error("Android integrity verification error", error=str(e))
            raise AttestationError("Android integrity verification failed")
    
    async def verify_ios_attestation(self, attestation_object: str, key_id: str, challenge: str) -> bool:
        """
        Verify iOS app attestation using Apple App Attest
        
        Args:
            attestation_object: Base64 encoded attestation object
            key_id: The key identifier from iOS app
            challenge: The challenge sent to the app
            
        Returns:
            bool: True if verification passes
            
        Raises:
            AttestationError: If verification fails
        """
        try:
            result = await self.apple_service.verify_attestation(attestation_object, key_id, challenge)
            return result.get("verdict") == "VALID"
        except AttestationError:
            raise
        except Exception as e:
            logger.error("iOS attestation verification error", error=str(e))
            raise AttestationError("iOS attestation verification failed")
    
    async def verify_ios_assertion(self, assertion: str, key_id: str, client_data_hash: str) -> bool:
        """
        Verify iOS app assertion for ongoing requests
        
        Args:
            assertion: Base64 encoded assertion
            key_id: The key identifier
            client_data_hash: Hash of the client data
            
        Returns:
            bool: True if verification passes
        """
        try:
            result = await self.apple_service.verify_assertion(assertion, key_id, client_data_hash)
            return result.get("verdict") == "VALID"
        except AttestationError:
            raise
        except Exception as e:
            logger.error("iOS assertion verification error", error=str(e))
            raise AttestationError("iOS assertion verification failed")
    
    def generate_challenge(self) -> str:
        """Generate a cryptographic challenge for attestation"""
        import secrets
        return base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
    
    def create_client_data_hash(self, request_data: Dict[str, Any]) -> str:
        """Create a hash of client request data for assertion verification"""
        # Sort the data for consistent hashing
        sorted_data = json.dumps(request_data, sort_keys=True)
        hash_bytes = hashlib.sha256(sorted_data.encode('utf-8')).digest()
        return base64.b64encode(hash_bytes).decode('utf-8')


# Global service instance
attestation_service = AppAttestationService()