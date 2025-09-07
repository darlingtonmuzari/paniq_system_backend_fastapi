"""
OTP delivery services for SMS and email notifications.
"""
import asyncio
import logging
import smtplib
import ssl
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings

# settings is imported directly from config
logger = logging.getLogger(__name__)


class OTPDeliveryService:
    """Service for delivering OTP codes via SMS and email."""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        
        # SMS service configuration (placeholder for actual SMS provider)
        self.sms_api_key = getattr(settings, 'SMS_API_KEY', None)
        self.sms_api_url = getattr(settings, 'SMS_API_URL', None)
    
    def _send_email_sync(self, message: MIMEMultipart, to_email: str) -> bool:
        """
        Synchronous email sending using smtplib
        """
        try:
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            # Start TLS encryption
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            server.starttls(context=context)
            
            # Login
            server.login(self.smtp_username, self.smtp_password)
            
            # Send email
            text = message.as_string()
            server.sendmail(self.from_email, to_email, text)
            
            # Quit
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_email_otp(self, email: str, otp: str, account_type: str = "account") -> bool:
        """
        Send OTP via email.
        
        Args:
            email: Recipient email address
            otp: OTP code to send
            account_type: Type of account (user/security_firm)
            
        Returns:
            True if email sent successfully
        """
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = "Account Unlock Code - Paniq"
            message["From"] = self.from_email
            message["To"] = email
            
            # Create email content
            text_content = f"""
Your account unlock code is: {otp}

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

Paniq Security Team
            """
            
            html_content = f"""
<html>
<body>
    <h2>Account Unlock Code</h2>
    <p>Your account unlock code is: <strong>{otp}</strong></p>
    <p>This code will expire in 10 minutes.</p>
    <p>If you did not request this code, please ignore this email.</p>
    <br>
    <p>Paniq Security Team</p>
</body>
</html>
            """
            
            # Attach parts
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                success = await loop.run_in_executor(
                    executor, 
                    self._send_email_sync, 
                    message, 
                    email
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {str(e)}")
            return False
    
    async def send_sms_otp(self, mobile_number: str, otp: str) -> bool:
        """
        Send OTP via SMS.
        
        Args:
            mobile_number: Recipient mobile number
            otp: OTP code to send
            
        Returns:
            True if SMS sent successfully
        """
        try:
            if not self.sms_api_key or not self.sms_api_url:
                logger.warning("SMS service not configured, skipping SMS OTP")
                return False
            
            message = f"Your Paniq account unlock code is: {otp}. This code expires in 10 minutes."
            
            # Placeholder for actual SMS service integration
            # This would typically use a service like Twilio, AWS SNS, etc.
            
            # For now, we'll simulate SMS sending
            logger.info(f"SMS OTP would be sent to {mobile_number}: {otp}")
            
            # TODO: Implement actual SMS service integration
            # Example with Twilio:
            # client = Client(account_sid, auth_token)
            # message = client.messages.create(
            #     body=message,
            #     from_='+1234567890',
            #     to=mobile_number
            # )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS OTP to {mobile_number}: {str(e)}")
            return False
    
    async def send_password_reset_email(self, email: str, otp: str) -> bool:
        """
        Send password reset OTP via email.
        
        Args:
            email: Recipient email address
            otp: OTP code to send
            
        Returns:
            True if email sent successfully
        """
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = "Password Reset Code - Paniq"
            message["From"] = self.from_email
            message["To"] = email
            
            # Create email content
            text_content = f"""
Your password reset code is: {otp}

This code will expire in 10 minutes.

If you did not request a password reset, please ignore this email and your password will remain unchanged.

For security reasons, please do not share this code with anyone.

Paniq Security Team
            """
            
            html_content = f"""
<html>
<body>
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #d32f2f;">Password Reset Code</h2>
        <p>Your password reset code is:</p>
        <div style="background-color: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
            <span style="font-size: 24px; font-weight: bold; color: #d32f2f; letter-spacing: 3px;">{otp}</span>
        </div>
        <p><strong>This code will expire in 10 minutes.</strong></p>
        <p>If you did not request a password reset, please ignore this email and your password will remain unchanged.</p>
        <p>For security reasons, please do not share this code with anyone.</p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #666; font-size: 12px;">
            Paniq Security Team<br>
            This is an automated message, please do not reply.
        </p>
    </div>
</body>
</html>
            """
            
            # Attach parts
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                success = await loop.run_in_executor(
                    executor, 
                    self._send_email_sync, 
                    message, 
                    email
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {str(e)}")
            return False
    
    async def send_otp(self, identifier: str, otp: str, delivery_method: str = "email") -> bool:
        """
        Send OTP using specified delivery method.
        
        Args:
            identifier: Email or mobile number
            otp: OTP code to send
            delivery_method: 'email' or 'sms'
            
        Returns:
            True if OTP sent successfully
        """
        if delivery_method == "email":
            return await self.send_email_otp(identifier, otp)
        elif delivery_method == "sms":
            return await self.send_sms_otp(identifier, otp)
        else:
            logger.error(f"Unknown delivery method: {delivery_method}")
            return False
    
    async def send_verification_email(self, email: str, otp: str) -> bool:
        """
        Send account verification OTP via email.
        
        Args:
            email: Recipient email address
            otp: OTP code to send
            
        Returns:
            True if email sent successfully
        """
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = "Account Verification Code - Paniq"
            message["From"] = self.from_email
            message["To"] = email
            
            # Create email content
            text_content = f"""
Welcome to Paniq!

Your account verification code is: {otp}

This code will expire in 10 minutes.

Please enter this code in the app to verify your account and complete your registration.

If you did not create an account with us, please ignore this email.

Paniq Team
            """
            
            html_content = f"""
<html>
<body>
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #d32f2f;">Welcome to Paniq!</h2>
        <p>Thank you for registering with us. To complete your account setup, please verify your email address.</p>
        <p>Your verification code is:</p>
        <div style="background-color: #f5f5f5; padding: 20px; text-align: center; margin: 20px 0;">
            <span style="font-size: 24px; font-weight: bold; color: #d32f2f; letter-spacing: 3px;">{otp}</span>
        </div>
        <p><strong>This code will expire in 10 minutes.</strong></p>
        <p>Please enter this code in the app to verify your account and complete your registration.</p>
        <p>If you did not create an account with us, please ignore this email.</p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #666; font-size: 12px;">
            Paniq Team<br>
            This is an automated message, please do not reply.
        </p>
    </div>
</body>
</html>
            """
            
            # Attach parts
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                success = await loop.run_in_executor(
                    executor, 
                    self._send_email_sync, 
                    message, 
                    email
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {str(e)}")
            return False
    
    async def send_personnel_credentials_email(
        self, 
        email: str, 
        first_name: str, 
        last_name: str, 
        password: str, 
        firm_name: str,
        role: str
    ) -> bool:
        """
        Send personnel enrollment credentials via email.
        
        Args:
            email: Personnel email address
            first_name: Personnel first name
            last_name: Personnel last name
            password: Generated password
            firm_name: Security firm name
            role: Personnel role
            
        Returns:
            True if email sent successfully
        """
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = "Welcome to Paniq - Your Account Credentials"
            message["From"] = self.from_email
            message["To"] = email
            
            # Create email content
            text_content = f"""
Welcome to Paniq, {first_name}!

You have been enrolled as personnel for {firm_name} with the role of {role}.

Your login credentials are:
Email: {email}
Password: {password}

Please log in to the Paniq system and change your password immediately for security reasons.

Login URL: https://app.paniq.co.za/login

For security reasons, please do not share these credentials with anyone.

If you have any questions, please contact your administrator.

Paniq Security Team
            """
            
            html_content = f"""
<html>
<body>
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #d32f2f;">Welcome to Paniq!</h2>
        <p>Hello {first_name} {last_name},</p>
        <p>You have been enrolled as personnel for <strong>{firm_name}</strong> with the role of <strong>{role}</strong>.</p>
        
        <div style="background-color: #f5f5f5; padding: 20px; margin: 20px 0; border-left: 4px solid #d32f2f;">
            <h3 style="margin-top: 0;">Your Login Credentials</h3>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Password:</strong> <span style="font-family: monospace; background-color: #fff; padding: 2px 4px; border: 1px solid #ddd;">{password}</span></p>
        </div>
        
        <p><strong>Important:</strong> Please log in to the system and change your password immediately for security reasons.</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://app.paniq.co.za/login" style="background-color: #d32f2f; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">Login to Paniq</a>
        </div>
        
        <p>For security reasons, please do not share these credentials with anyone.</p>
        <p>If you have any questions, please contact your administrator.</p>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #666; font-size: 12px;">
            Paniq Security Team<br>
            This is an automated message, please do not reply.
        </p>
    </div>
</body>
</html>
            """
            
            # Attach parts
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                success = await loop.run_in_executor(
                    executor, 
                    self._send_email_sync, 
                    message, 
                    email
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send personnel credentials email to {email}: {str(e)}")
            return False