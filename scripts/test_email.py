#!/usr/bin/env python3
"""
Simple script to test email sending functionality
"""
import asyncio
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

# SMTP Configuration from .env
SMTP_SERVER = "mail.paniq.co.za"
SMTP_PORT = 587
SMTP_USERNAME = "no-reply@paniq.co.za"
SMTP_PASSWORD = "14Dmin@2025"
FROM_EMAIL = "no-reply@paniq.co.za"

async def send_test_email(to_email: str) -> bool:
    """
    Send a test email to verify SMTP configuration
    
    Args:
        to_email: Recipient email address
        
    Returns:
        True if email sent successfully
    """
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "Test Email - Panic System SMTP Configuration"
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        
        # Create email content
        text_content = f"""
Hello,

This is a test email to verify the SMTP configuration for the Panic System platform.

If you receive this email, it means the email delivery system is working correctly.

Test Details:
- SMTP Server: {SMTP_SERVER}
- Port: {SMTP_PORT}
- From: {FROM_EMAIL}
- To: {to_email}

Best regards,
Panic System Team
        """
        
        html_content = f"""
<html>
<body>
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #d32f2f;">Test Email - Panic System</h2>
        <p>Hello,</p>
        <p>This is a test email to verify the SMTP configuration for the Panic System platform.</p>
        <p><strong>If you receive this email, it means the email delivery system is working correctly.</strong></p>
        
        <div style="background-color: #f5f5f5; padding: 15px; margin: 20px 0; border-left: 4px solid #d32f2f;">
            <h3>Test Details:</h3>
            <ul>
                <li><strong>SMTP Server:</strong> {SMTP_SERVER}</li>
                <li><strong>Port:</strong> {SMTP_PORT}</li>
                <li><strong>From:</strong> {FROM_EMAIL}</li>
                <li><strong>To:</strong> {to_email}</li>
            </ul>
        </div>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #666; font-size: 12px;">
            Best regards,<br>
            Panic System Team<br>
            This is an automated test message.
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
        
        print(f"Attempting to send test email to {to_email}...")
        print(f"Using SMTP server: {SMTP_SERVER}:{SMTP_PORT}")
        
        # Try different connection methods
        success = False
        
        # Method 1: STARTTLS (most common)
        try:
            print("Trying STARTTLS connection...")
            await aiosmtplib.send(
                message,
                hostname=SMTP_SERVER,
                port=SMTP_PORT,
                username=SMTP_USERNAME,
                password=SMTP_PASSWORD,
                use_tls=True
            )
            print("✅ Email sent successfully via STARTTLS")
            success = True
            
        except Exception as starttls_error:
            print(f"❌ STARTTLS failed: {starttls_error}")
            
            # Method 2: SSL/TLS (port 465 style)
            try:
                print("Trying SSL/TLS connection...")
                await aiosmtplib.send(
                    message,
                    hostname=SMTP_SERVER,
                    port=465,
                    username=SMTP_USERNAME,
                    password=SMTP_PASSWORD,
                    use_tls=False,
                    start_tls=False
                )
                print("✅ Email sent successfully via SSL/TLS")
                success = True
                
            except Exception as ssl_error:
                print(f"❌ SSL/TLS failed: {ssl_error}")
                
                # Method 3: Try without TLS (not recommended for production)
                try:
                    print("Trying plain connection (no TLS)...")
                    await aiosmtplib.send(
                        message,
                        hostname=SMTP_SERVER,
                        port=25,
                        username=SMTP_USERNAME,
                        password=SMTP_PASSWORD,
                        use_tls=False,
                        start_tls=False
                    )
                    print("✅ Email sent successfully via plain connection")
                    success = True
                    
                except Exception as plain_error:
                    print(f"❌ Plain connection failed: {plain_error}")
        
        return success
        
    except Exception as e:
        print(f"❌ Failed to send test email: {str(e)}")
        return False

async def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python test_email.py <email_address>")
        print("Example: python test_email.py darlingtonmuzari@gmail.com")
        sys.exit(1)
    
    to_email = sys.argv[1]
    
    print("=" * 60)
    print("PANIC SYSTEM - EMAIL CONFIGURATION TEST")
    print("=" * 60)
    
    success = await send_test_email(to_email)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED: Email sent successfully!")
        print(f"Check {to_email} for the test message.")
    else:
        print("❌ TEST FAILED: Could not send email.")
        print("Please check SMTP configuration and network connectivity.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())