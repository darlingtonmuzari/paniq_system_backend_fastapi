#!/usr/bin/env python3
"""
Test email sending using Gmail SMTP as a fallback
"""
import asyncio
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

async def send_test_email_gmail(to_email: str) -> bool:
    """
    Send a test email using Gmail SMTP (for testing purposes)
    Note: This requires an app password, not your regular Gmail password
    """
    try:
        # Gmail SMTP configuration
        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        # Note: You would need to provide Gmail credentials here
        # This is just for testing connectivity
        
        message = MIMEMultipart("alternative")
        message["Subject"] = "Test Email - Panic System (via Gmail SMTP)"
        message["From"] = "test@example.com"  # Placeholder
        message["To"] = to_email
        
        text_content = f"""
Hello,

This is a connectivity test to verify if SMTP works from this environment.

If you receive this, it means the network allows SMTP connections.

Test Details:
- SMTP Server: {SMTP_SERVER}
- Port: {SMTP_PORT}
- To: {to_email}

This is just a connectivity test.
        """
        
        text_part = MIMEText(text_content, "plain")
        message.attach(text_part)
        
        print(f"Testing SMTP connectivity to {SMTP_SERVER}:{SMTP_PORT}...")
        
        # Just test the connection without credentials
        try:
            # This will fail at auth but will tell us if we can connect
            await aiosmtplib.send(
                message,
                hostname=SMTP_SERVER,
                port=SMTP_PORT,
                username="test@gmail.com",  # Dummy credentials
                password="dummy",
                use_tls=True
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "authentication" in error_msg or "username and password not accepted" in error_msg:
                print("✅ SMTP connection successful (authentication failed as expected)")
                print("This means the network allows SMTP connections.")
                return True
            else:
                print(f"❌ SMTP connection failed: {e}")
                return False
        
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

async def test_network_connectivity():
    """Test basic network connectivity"""
    import socket
    
    print("Testing network connectivity...")
    
    # Test Gmail SMTP
    try:
        sock = socket.create_connection(("smtp.gmail.com", 587), timeout=10)
        sock.close()
        print("✅ Can connect to smtp.gmail.com:587")
    except Exception as e:
        print(f"❌ Cannot connect to smtp.gmail.com:587 - {e}")
    
    # Test your mail server
    try:
        sock = socket.create_connection(("mail.paniq.co.za", 587), timeout=10)
        sock.close()
        print("✅ Can connect to mail.paniq.co.za:587")
    except Exception as e:
        print(f"❌ Cannot connect to mail.paniq.co.za:587 - {e}")
    
    # Test port 25
    try:
        sock = socket.create_connection(("mail.paniq.co.za", 25), timeout=10)
        sock.close()
        print("✅ Can connect to mail.paniq.co.za:25")
    except Exception as e:
        print(f"❌ Cannot connect to mail.paniq.co.za:25 - {e}")
    
    # Test port 465
    try:
        sock = socket.create_connection(("mail.paniq.co.za", 465), timeout=10)
        sock.close()
        print("✅ Can connect to mail.paniq.co.za:465")
    except Exception as e:
        print(f"❌ Cannot connect to mail.paniq.co.za:465 - {e}")

async def main():
    """Main function"""
    print("=" * 60)
    print("NETWORK CONNECTIVITY TEST")
    print("=" * 60)
    
    await test_network_connectivity()
    
    print("\n" + "=" * 60)
    print("SMTP CONNECTIVITY TEST")
    print("=" * 60)
    
    if len(sys.argv) == 2:
        to_email = sys.argv[1]
        await send_test_email_gmail(to_email)
    else:
        print("Skipping email test (no recipient provided)")
    
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS:")
    print("=" * 60)
    print("1. If Gmail SMTP works but mail.paniq.co.za doesn't:")
    print("   - Check if mail.paniq.co.za is accessible from your network")
    print("   - Verify firewall settings")
    print("   - Contact your hosting provider")
    print("")
    print("2. If neither works:")
    print("   - Your network may block outbound SMTP")
    print("   - Try from a different network")
    print("   - Check corporate firewall settings")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())