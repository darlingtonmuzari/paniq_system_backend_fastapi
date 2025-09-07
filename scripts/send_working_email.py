#!/usr/bin/env python3
"""
Working email sender using standard smtplib
"""
import smtplib
import ssl
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_test_email(to_email: str) -> bool:
    """
    Send a test email using standard smtplib
    """
    # SMTP Configuration
    SMTP_SERVER = "mail.paniq.co.za"
    SMTP_PORT = 587
    SMTP_USERNAME = "no-reply@paniq.co.za"
    SMTP_PASSWORD = "14Dmin@2025"
    FROM_EMAIL = "no-reply@paniq.co.za"
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = "Test Email - Paniq Platform"
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        
        # Create email content
        text_content = f"""
Hello,

This is a test email from the Paniq platform to verify email delivery.

✅ If you receive this email, it means the SMTP configuration is working correctly!

Test Details:
- SMTP Server: {SMTP_SERVER}
- Port: {SMTP_PORT}
- From: {FROM_EMAIL}
- To: {to_email}
- Sent using: Python smtplib

The email delivery system is now functional and ready for OTP delivery.

Best regards,
Paniq Team
        """
        
        html_content = f"""
<html>
<body>
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #d32f2f; text-align: center;">✅ Email Test Successful!</h2>
        <div style="background-color: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Hello,</strong></p>
            <p>This is a test email from the <strong>Paniq platform</strong> to verify email delivery.</p>
            <p style="font-size: 18px; color: #2e7d32;"><strong>✅ If you receive this email, it means the SMTP configuration is working correctly!</strong></p>
        </div>
        
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #333; margin-top: 0;">Test Details:</h3>
            <ul style="color: #666;">
                <li><strong>SMTP Server:</strong> {SMTP_SERVER}</li>
                <li><strong>Port:</strong> {SMTP_PORT}</li>
                <li><strong>From:</strong> {FROM_EMAIL}</li>
                <li><strong>To:</strong> {to_email}</li>
                <li><strong>Sent using:</strong> Python smtplib</li>
            </ul>
        </div>
        
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
            <p><strong>📧 The email delivery system is now functional and ready for OTP delivery.</strong></p>
        </div>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #666; font-size: 12px; text-align: center;">
            Best regards,<br>
            <strong>Paniq Team</strong><br>
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
        
        print(f"Sending test email to {to_email}...")
        print(f"Using SMTP server: {SMTP_SERVER}:{SMTP_PORT}")
        
        # Create SMTP session
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        
        # Enable debug output
        server.set_debuglevel(1)
        
        # Start TLS encryption
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        server.starttls(context=context)
        
        # Login
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        # Send email
        text = message.as_string()
        server.sendmail(FROM_EMAIL, to_email, text)
        
        # Quit
        server.quit()
        
        print("✅ Email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python send_working_email.py <email_address>")
        print("Example: python send_working_email.py darlingtonmuzari@gmail.com")
        sys.exit(1)
    
    to_email = sys.argv[1]
    
    print("=" * 60)
    print("PANIC SYSTEM - WORKING EMAIL TEST")
    print("=" * 60)
    
    success = send_test_email(to_email)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ SUCCESS: Test email sent successfully!")
        print(f"📧 Check {to_email} for the test message.")
        print("🎉 Email delivery system is working correctly!")
    else:
        print("❌ FAILED: Could not send email.")
        print("Please check the error messages above.")
    print("=" * 60)

if __name__ == "__main__":
    main()