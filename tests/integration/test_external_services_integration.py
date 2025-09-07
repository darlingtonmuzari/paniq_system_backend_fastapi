"""
External Services Integration Tests
Tests integration with external services using mocks and contracts
"""
import pytest
import json
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.services.attestation import AttestationService
from app.services.otp_delivery import OTPDeliveryService
from app.services.notification import NotificationService
from app.services.credit import CreditService
from app.services.geolocation import GeolocationService


class TestAttestationServiceIntegration:
    """Test mobile app attestation service integration"""
    
    @pytest.mark.asyncio
    async def test_android_attestation_integration(self, mock_external_services):
        """Test Android Play Integrity API integration"""
        service = AttestationService()
        
        # Mock successful attestation
        mock_external_services['android_attestation'].return_value = {
            "tokenPayloadExternal": {
                "requestDetails": {
                    "requestPackageName": "com.panic.system",
                    "timestampMillis": str(int(datetime.utcnow().timestamp() * 1000))
                },
                "appIntegrity": {
                    "appRecognitionVerdict": "PLAY_RECOGNIZED",
                    "packageName": "com.panic.system",
                    "certificateSha256Digest": ["valid_cert_hash"],
                    "versionCode": 1
                },
                "deviceIntegrity": {
                    "deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY"]
                }
            }
        }
        
        # Test valid attestation
        token = "valid.android.attestation.token"
        result = await service.verify_android_integrity(token)
        
        assert result["valid"] is True
        assert result["package_name"] == "com.panic.system"
        assert result["app_recognized"] is True
        assert result["device_integrity"] is True
        
        # Test invalid attestation
        mock_external_services['android_attestation'].return_value = {
            "tokenPayloadExternal": {
                "appIntegrity": {
                    "appRecognitionVerdict": "UNKNOWN_APP"
                },
                "deviceIntegrity": {
                    "deviceRecognitionVerdict": ["MEETS_BASIC_INTEGRITY"]
                }
            }
        }
        
        result = await service.verify_android_integrity("invalid.token")
        
        assert result["valid"] is False
        assert result["app_recognized"] is False
    
    @pytest.mark.asyncio
    async def test_ios_attestation_integration(self, mock_external_services):
        """Test iOS App Attest integration"""
        service = AttestationService()
        
        # Mock successful attestation
        mock_external_services['ios_attestation'].return_value = {
            "valid": True,
            "app_id": "com.panic.system",
            "team_id": "TEAM123456",
            "counter": 1,
            "receipt_type": "production"
        }
        
        # Test valid attestation
        attestation_data = {
            "key_id": "test_key_id",
            "assertion": "test_assertion_data",
            "client_data_hash": "test_client_hash"
        }
        
        result = await service.verify_ios_attestation(attestation_data)
        
        assert result["valid"] is True
        assert result["app_id"] == "com.panic.system"
        assert result["receipt_type"] == "production"
        
        # Test invalid attestation
        mock_external_services['ios_attestation'].return_value = {
            "valid": False,
            "error": "Invalid assertion"
        }
        
        result = await service.verify_ios_attestation({"invalid": "data"})
        
        assert result["valid"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_attestation_caching(self, mock_external_services):
        """Test attestation result caching"""
        service = AttestationService()
        
        # Mock successful attestation
        mock_external_services['android_attestation'].return_value = {
            "tokenPayloadExternal": {
                "appIntegrity": {
                    "appRecognitionVerdict": "PLAY_RECOGNIZED"
                },
                "deviceIntegrity": {
                    "deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY"]
                }
            }
        }
        
        token = "cacheable.token"
        
        # First call should hit external service
        result1 = await service.verify_android_integrity(token)
        assert result1["valid"] is True
        assert mock_external_services['android_attestation'].call_count == 1
        
        # Second call should use cache
        result2 = await service.verify_android_integrity(token)
        assert result2["valid"] is True
        assert mock_external_services['android_attestation'].call_count == 1  # No additional call


class TestOTPDeliveryServiceIntegration:
    """Test OTP delivery service integration"""
    
    @pytest.mark.asyncio
    async def test_sms_delivery_integration(self, mock_external_services):
        """Test SMS OTP delivery integration"""
        service = OTPDeliveryService()
        
        # Mock successful SMS delivery
        mock_external_services['sms_service'].return_value = {
            "success": True,
            "message_id": "sms_123456",
            "status": "sent"
        }
        
        # Test SMS delivery
        result = await service.send_sms_otp("+1234567890", "123456")
        
        assert result["success"] is True
        assert result["message_id"] == "sms_123456"
        assert result["delivery_method"] == "sms"
        
        # Verify SMS service was called with correct parameters
        mock_external_services['sms_service'].assert_called_once_with(
            phone="+1234567890",
            message="Your verification code is: 123456. This code expires in 10 minutes."
        )
        
        # Test SMS delivery failure
        mock_external_services['sms_service'].return_value = {
            "success": False,
            "error": "Invalid phone number"
        }
        
        result = await service.send_sms_otp("+invalid", "123456")
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_email_delivery_integration(self, mock_external_services):
        """Test email OTP delivery integration"""
        service = OTPDeliveryService()
        
        # Mock successful email delivery
        mock_external_services['email_service'].return_value = {
            "success": True,
            "message_id": "email_789012",
            "status": "sent"
        }
        
        # Test email delivery
        result = await service.send_email_otp("user@test.com", "654321")
        
        assert result["success"] is True
        assert result["message_id"] == "email_789012"
        assert result["delivery_method"] == "email"
        
        # Verify email service was called with correct parameters
        mock_external_services['email_service'].assert_called_once_with(
            to_email="user@test.com",
            subject="Panic System - Verification Code",
            body="Your verification code is: 654321. This code expires in 10 minutes."
        )
    
    @pytest.mark.asyncio
    async def test_otp_rate_limiting(self, mock_external_services):
        """Test OTP delivery rate limiting"""
        service = OTPDeliveryService()
        
        # Mock successful delivery
        mock_external_services['sms_service'].return_value = {
            "success": True,
            "message_id": "sms_rate_test"
        }
        
        phone = "+1234567890"
        
        # First OTP should succeed
        result1 = await service.send_sms_otp(phone, "111111")
        assert result1["success"] is True
        
        # Second OTP within rate limit window should fail
        result2 = await service.send_sms_otp(phone, "222222")
        assert result2["success"] is False
        assert "rate limit" in result2["error"].lower()
        
        # Verify external service was only called once
        assert mock_external_services['sms_service'].call_count == 1


class TestNotificationServiceIntegration:
    """Test notification service integration"""
    
    @pytest.mark.asyncio
    async def test_push_notification_integration(self, mock_external_services):
        """Test push notification integration"""
        service = NotificationService()
        
        # Mock successful push notification
        mock_external_services['push_service'].return_value = {
            "success": True,
            "notification_id": "push_123456",
            "delivered_count": 1
        }
        
        # Test push notification
        notification_data = {
            "user_id": uuid4(),
            "title": "Emergency Request Update",
            "body": "Your emergency request has been accepted",
            "data": {
                "request_id": str(uuid4()),
                "status": "accepted"
            }
        }
        
        result = await service.send_push_notification(**notification_data)
        
        assert result["success"] is True
        assert result["notification_id"] == "push_123456"
        assert result["delivered_count"] == 1
        
        # Verify push service was called with correct parameters
        mock_external_services['push_service'].assert_called_once_with(
            user_id=notification_data["user_id"],
            title=notification_data["title"],
            body=notification_data["body"],
            data=notification_data["data"]
        )
    
    @pytest.mark.asyncio
    async def test_notification_templates(self, mock_external_services):
        """Test notification template system"""
        service = NotificationService()
        
        # Mock successful delivery
        mock_external_services['push_service'].return_value = {
            "success": True,
            "notification_id": "template_test"
        }
        
        # Test emergency request notification template
        template_data = {
            "template": "emergency_request_accepted",
            "user_id": uuid4(),
            "variables": {
                "request_id": "REQ123",
                "service_type": "security",
                "eta_minutes": 15
            }
        }
        
        result = await service.send_templated_notification(**template_data)
        
        assert result["success"] is True
        
        # Verify template was processed correctly
        call_args = mock_external_services['push_service'].call_args[1]
        assert "security" in call_args["body"]
        assert "15" in call_args["body"]
        assert call_args["data"]["request_id"] == "REQ123"
    
    @pytest.mark.asyncio
    async def test_notification_retry_logic(self, mock_external_services):
        """Test notification retry logic"""
        service = NotificationService()
        
        # Mock initial failure then success
        mock_external_services['push_service'].side_effect = [
            {"success": False, "error": "Temporary failure"},
            {"success": False, "error": "Still failing"},
            {"success": True, "notification_id": "retry_success"}
        ]
        
        notification_data = {
            "user_id": uuid4(),
            "title": "Retry Test",
            "body": "Testing retry logic"
        }
        
        result = await service.send_push_notification_with_retry(**notification_data)
        
        assert result["success"] is True
        assert result["notification_id"] == "retry_success"
        assert result["retry_count"] == 2
        
        # Verify service was called 3 times (initial + 2 retries)
        assert mock_external_services['push_service'].call_count == 3


class TestCreditServiceIntegration:
    """Test credit/payment service integration"""
    
    @pytest.mark.asyncio
    async def test_payment_processing_integration(self, mock_external_services):
        """Test payment gateway integration"""
        service = CreditService()
        
        # Mock successful payment
        mock_external_services['payment_service'].return_value = {
            "success": True,
            "transaction_id": "txn_123456789",
            "amount": 500.00,
            "currency": "USD",
            "status": "completed",
            "gateway_response": {
                "authorization_code": "AUTH123",
                "reference_number": "REF456"
            }
        }
        
        # Test credit purchase
        payment_data = {
            "firm_id": uuid4(),
            "amount": 500.00,
            "payment_method": "credit_card",
            "card_details": {
                "number": "4111111111111111",
                "expiry_month": 12,
                "expiry_year": 2025,
                "cvv": "123",
                "holder_name": "Test User"
            }
        }
        
        result = await service.process_credit_purchase(**payment_data)
        
        assert result["success"] is True
        assert result["transaction_id"] == "txn_123456789"
        assert result["amount"] == 500.00
        assert result["status"] == "completed"
        
        # Verify payment gateway was called with correct parameters
        call_args = mock_external_services['payment_service'].call_args[1]
        assert call_args["amount"] == 500.00
        assert call_args["payment_method"] == "credit_card"
        assert "4111111111111111" in call_args["card_details"]["number"]
    
    @pytest.mark.asyncio
    async def test_payment_failure_handling(self, mock_external_services):
        """Test payment failure handling"""
        service = CreditService()
        
        # Mock payment failure
        mock_external_services['payment_service'].return_value = {
            "success": False,
            "error_code": "CARD_DECLINED",
            "error_message": "Your card was declined",
            "gateway_response": {
                "decline_reason": "insufficient_funds"
            }
        }
        
        payment_data = {
            "firm_id": uuid4(),
            "amount": 1000.00,
            "payment_method": "credit_card",
            "card_details": {
                "number": "4000000000000002",  # Test card that gets declined
                "expiry_month": 12,
                "expiry_year": 2025,
                "cvv": "123"
            }
        }
        
        result = await service.process_credit_purchase(**payment_data)
        
        assert result["success"] is False
        assert result["error_code"] == "CARD_DECLINED"
        assert "declined" in result["error_message"].lower()
    
    @pytest.mark.asyncio
    async def test_refund_processing(self, mock_external_services):
        """Test refund processing integration"""
        service = CreditService()
        
        # Mock successful refund
        mock_external_services['payment_service'].return_value = {
            "success": True,
            "refund_id": "refund_789012",
            "original_transaction_id": "txn_123456789",
            "refund_amount": 250.00,
            "status": "processed"
        }
        
        refund_data = {
            "transaction_id": "txn_123456789",
            "refund_amount": 250.00,
            "reason": "Partial service cancellation"
        }
        
        result = await service.process_refund(**refund_data)
        
        assert result["success"] is True
        assert result["refund_id"] == "refund_789012"
        assert result["refund_amount"] == 250.00
        assert result["status"] == "processed"


class TestGeolocationServiceIntegration:
    """Test geolocation service integration"""
    
    @pytest.mark.asyncio
    async def test_address_geocoding_integration(self, mock_external_services):
        """Test address geocoding integration"""
        service = GeolocationService()
        
        # Mock successful geocoding
        with patch('app.services.geolocation.geocoding_client') as mock_client:
            mock_client.geocode.return_value = {
                "results": [{
                    "geometry": {
                        "location": {
                            "lat": 40.7484,
                            "lng": -73.9857
                        }
                    },
                    "formatted_address": "Times Square, New York, NY 10036, USA",
                    "place_id": "ChIJmQJIxlVYwokRLgeuocVOGVU"
                }],
                "status": "OK"
            }
            
            # Test address geocoding
            address = "Times Square, New York, NY"
            result = await service.geocode_address(address)
            
            assert result["success"] is True
            assert result["latitude"] == 40.7484
            assert result["longitude"] == -73.9857
            assert "Times Square" in result["formatted_address"]
            
            # Verify geocoding service was called
            mock_client.geocode.assert_called_once_with(address)
    
    @pytest.mark.asyncio
    async def test_reverse_geocoding_integration(self, mock_external_services):
        """Test reverse geocoding integration"""
        service = GeolocationService()
        
        # Mock successful reverse geocoding
        with patch('app.services.geolocation.geocoding_client') as mock_client:
            mock_client.reverse_geocode.return_value = {
                "results": [{
                    "formatted_address": "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
                    "address_components": [
                        {"long_name": "1600", "types": ["street_number"]},
                        {"long_name": "Amphitheatre Parkway", "types": ["route"]},
                        {"long_name": "Mountain View", "types": ["locality"]},
                        {"long_name": "CA", "types": ["administrative_area_level_1"]},
                        {"long_name": "94043", "types": ["postal_code"]}
                    ]
                }],
                "status": "OK"
            }
            
            # Test reverse geocoding
            result = await service.reverse_geocode(37.4224, -122.0842)
            
            assert result["success"] is True
            assert "Amphitheatre Parkway" in result["formatted_address"]
            assert result["city"] == "Mountain View"
            assert result["state"] == "CA"
            assert result["postal_code"] == "94043"
    
    @pytest.mark.asyncio
    async def test_distance_calculation_integration(self, mock_external_services):
        """Test distance calculation integration"""
        service = GeolocationService()
        
        # Mock successful distance calculation
        with patch('app.services.geolocation.distance_client') as mock_client:
            mock_client.distance_matrix.return_value = {
                "rows": [{
                    "elements": [{
                        "distance": {"text": "2.1 mi", "value": 3379},
                        "duration": {"text": "8 mins", "value": 480},
                        "status": "OK"
                    }]
                }],
                "status": "OK"
            }
            
            # Test distance calculation
            origin = (40.7484, -73.9857)  # Times Square
            destination = (40.7589, -73.9851)  # Central Park
            
            result = await service.calculate_distance_and_duration(origin, destination)
            
            assert result["success"] is True
            assert result["distance_meters"] == 3379
            assert result["duration_seconds"] == 480
            assert result["distance_text"] == "2.1 mi"
            assert result["duration_text"] == "8 mins"
    
    @pytest.mark.asyncio
    async def test_geofencing_integration(self, mock_external_services):
        """Test geofencing integration"""
        service = GeolocationService()
        
        # Test point in polygon calculation
        polygon_coordinates = [
            [-74.0479, 40.6829],  # SW corner
            [-73.9067, 40.6829],  # SE corner
            [-73.9067, 40.8176],  # NE corner
            [-74.0479, 40.8176],  # NW corner
            [-74.0479, 40.6829]   # Close polygon
        ]
        
        # Point inside polygon (Manhattan)
        point_inside = (-73.9857, 40.7484)  # Times Square
        result = await service.is_point_in_polygon(point_inside, polygon_coordinates)
        assert result["inside"] is True
        
        # Point outside polygon (Brooklyn)
        point_outside = (-73.9442, 40.6782)  # Brooklyn
        result = await service.is_point_in_polygon(point_outside, polygon_coordinates)
        assert result["inside"] is False


class TestExternalServiceErrorHandling:
    """Test error handling for external service failures"""
    
    @pytest.mark.asyncio
    async def test_service_timeout_handling(self, mock_external_services):
        """Test handling of service timeouts"""
        service = NotificationService()
        
        # Mock timeout exception
        import asyncio
        mock_external_services['push_service'].side_effect = asyncio.TimeoutError("Service timeout")
        
        notification_data = {
            "user_id": uuid4(),
            "title": "Timeout Test",
            "body": "Testing timeout handling"
        }
        
        result = await service.send_push_notification(**notification_data)
        
        assert result["success"] is False
        assert "timeout" in result["error"].lower()
        assert result["error_type"] == "timeout"
    
    @pytest.mark.asyncio
    async def test_service_unavailable_handling(self, mock_external_services):
        """Test handling of service unavailability"""
        service = OTPDeliveryService()
        
        # Mock service unavailable
        mock_external_services['sms_service'].side_effect = Exception("Service unavailable")
        
        result = await service.send_sms_otp("+1234567890", "123456")
        
        assert result["success"] is False
        assert "unavailable" in result["error"].lower()
        assert result["error_type"] == "service_error"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, mock_external_services):
        """Test circuit breaker pattern for external services"""
        service = CreditService()
        
        # Mock consecutive failures to trigger circuit breaker
        mock_external_services['payment_service'].side_effect = [
            Exception("Service error"),
            Exception("Service error"),
            Exception("Service error"),
            Exception("Service error"),
            Exception("Service error")
        ]
        
        payment_data = {
            "firm_id": uuid4(),
            "amount": 100.00,
            "payment_method": "credit_card",
            "card_details": {"number": "4111111111111111"}
        }
        
        # Make multiple requests to trigger circuit breaker
        for i in range(5):
            result = await service.process_credit_purchase(**payment_data)
            assert result["success"] is False
        
        # Circuit breaker should now be open
        result = await service.process_credit_purchase(**payment_data)
        assert result["success"] is False
        assert "circuit breaker" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_fallback_mechanisms(self, mock_external_services):
        """Test fallback mechanisms when primary services fail"""
        service = NotificationService()
        
        # Mock primary push service failure
        mock_external_services['push_service'].side_effect = Exception("Push service down")
        
        # Mock fallback SMS service success
        mock_external_services['sms_service'].return_value = {
            "success": True,
            "message_id": "fallback_sms_123"
        }
        
        notification_data = {
            "user_id": uuid4(),
            "phone": "+1234567890",
            "title": "Fallback Test",
            "body": "Testing fallback mechanism"
        }
        
        result = await service.send_notification_with_fallback(**notification_data)
        
        assert result["success"] is True
        assert result["delivery_method"] == "sms"  # Used fallback
        assert result["message_id"] == "fallback_sms_123"
        assert result["fallback_used"] is True