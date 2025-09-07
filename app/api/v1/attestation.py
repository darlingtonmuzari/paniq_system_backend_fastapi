"""
Mobile app attestation API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Optional
import structlog

from app.services.attestation import attestation_service, AttestationError
from app.core.exceptions import APIError, ErrorCodes

logger = structlog.get_logger()

router = APIRouter()


class ChallengeRequest(BaseModel):
    """Request model for attestation challenge"""
    platform: str = Field(..., description="Platform: 'android' or 'ios'")
    device_id: Optional[str] = Field(None, description="Device identifier for tracking")


class ChallengeResponse(BaseModel):
    """Response model for attestation challenge"""
    challenge: str = Field(..., description="Base64 encoded challenge")
    expires_in: int = Field(default=300, description="Challenge expiry time in seconds")


class AndroidAttestationRequest(BaseModel):
    """Request model for Android attestation verification"""
    integrity_token: str = Field(..., description="Google Play Integrity API token")
    nonce: Optional[str] = Field(None, description="Optional nonce for additional security")


class IOSAttestationRequest(BaseModel):
    """Request model for iOS attestation verification"""
    attestation_object: str = Field(..., description="Base64 encoded attestation object")
    key_id: str = Field(..., description="Key identifier from App Attest")
    challenge: str = Field(..., description="Challenge that was attested")


class IOSAssertionRequest(BaseModel):
    """Request model for iOS assertion verification"""
    assertion: str = Field(..., description="Base64 encoded assertion")
    key_id: str = Field(..., description="Key identifier")
    client_data_hash: str = Field(..., description="Hash of client request data")


class AttestationResponse(BaseModel):
    """Response model for attestation verification"""
    verified: bool = Field(..., description="Whether attestation was successful")
    platform: str = Field(..., description="Platform that was verified")
    message: str = Field(..., description="Verification result message")


@router.post("/challenge", response_model=ChallengeResponse)
async def request_attestation_challenge(request: ChallengeRequest):
    """
    Request an attestation challenge for mobile app verification
    
    This endpoint generates a cryptographic challenge that mobile apps
    must include in their attestation to prove authenticity.
    """
    try:
        # Generate a new challenge
        challenge = attestation_service.generate_challenge()
        
        logger.info(
            "attestation_challenge_generated",
            platform=request.platform,
            device_id=request.device_id,
            challenge_length=len(challenge)
        )
        
        return ChallengeResponse(
            challenge=challenge,
            expires_in=300  # 5 minutes
        )
        
    except Exception as e:
        logger.error("Failed to generate attestation challenge", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to generate attestation challenge"
        )


@router.post("/verify/android", response_model=AttestationResponse)
async def verify_android_attestation(
    request: AndroidAttestationRequest,
    x_platform: str = Header(..., alias="X-Platform")
):
    """
    Verify Android app attestation using Google Play Integrity API
    
    This endpoint verifies that the request is coming from a genuine
    Android app installed from Google Play Store.
    """
    if x_platform.lower() != "android":
        raise HTTPException(
            status_code=400,
            detail="Platform header must be 'android' for this endpoint"
        )
    
    try:
        # Verify the integrity token
        is_verified = await attestation_service.verify_android_integrity(
            request.integrity_token,
            request.nonce
        )
        
        if is_verified:
            logger.info(
                "android_attestation_verified",
                nonce=request.nonce[:10] + "..." if request.nonce else None
            )
            
            return AttestationResponse(
                verified=True,
                platform="android",
                message="Android app attestation verified successfully"
            )
        else:
            raise AttestationError("Android attestation verification failed")
            
    except AttestationError as e:
        logger.warning("Android attestation verification failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=f"Android attestation verification failed: {str(e)}"
        )
    except Exception as e:
        logger.error("Android attestation verification error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal error during Android attestation verification"
        )


@router.post("/verify/ios", response_model=AttestationResponse)
async def verify_ios_attestation(
    request: IOSAttestationRequest,
    x_platform: str = Header(..., alias="X-Platform")
):
    """
    Verify iOS app attestation using Apple App Attest
    
    This endpoint verifies that the request is coming from a genuine
    iOS app with valid App Attest attestation.
    """
    if x_platform.lower() != "ios":
        raise HTTPException(
            status_code=400,
            detail="Platform header must be 'ios' for this endpoint"
        )
    
    try:
        # Verify the attestation
        is_verified = await attestation_service.verify_ios_attestation(
            request.attestation_object,
            request.key_id,
            request.challenge
        )
        
        if is_verified:
            logger.info(
                "ios_attestation_verified",
                key_id=request.key_id[:8] + "...",
                challenge=request.challenge[:10] + "..."
            )
            
            return AttestationResponse(
                verified=True,
                platform="ios",
                message="iOS app attestation verified successfully"
            )
        else:
            raise AttestationError("iOS attestation verification failed")
            
    except AttestationError as e:
        logger.warning("iOS attestation verification failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=f"iOS attestation verification failed: {str(e)}"
        )
    except Exception as e:
        logger.error("iOS attestation verification error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal error during iOS attestation verification"
        )


@router.post("/verify/ios/assertion", response_model=AttestationResponse)
async def verify_ios_assertion(
    request: IOSAssertionRequest,
    x_platform: str = Header(..., alias="X-Platform")
):
    """
    Verify iOS app assertion for ongoing requests
    
    This endpoint verifies iOS App Attest assertions for subsequent
    requests after initial attestation is complete.
    """
    if x_platform.lower() != "ios":
        raise HTTPException(
            status_code=400,
            detail="Platform header must be 'ios' for this endpoint"
        )
    
    try:
        # Verify the assertion
        is_verified = await attestation_service.verify_ios_assertion(
            request.assertion,
            request.key_id,
            request.client_data_hash
        )
        
        if is_verified:
            logger.info(
                "ios_assertion_verified",
                key_id=request.key_id[:8] + "...",
                client_data_hash=request.client_data_hash[:10] + "..."
            )
            
            return AttestationResponse(
                verified=True,
                platform="ios",
                message="iOS app assertion verified successfully"
            )
        else:
            raise AttestationError("iOS assertion verification failed")
            
    except AttestationError as e:
        logger.warning("iOS assertion verification failed", error=str(e))
        raise HTTPException(
            status_code=401,
            detail=f"iOS assertion verification failed: {str(e)}"
        )
    except Exception as e:
        logger.error("iOS assertion verification error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal error during iOS assertion verification"
        )