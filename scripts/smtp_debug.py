#!/usr/bin/env python3
"""
Debug SMTP connection issues
"""
import socket
import ssl
import base64
import sys

def test_smtp_manual(server, port, username, password):
    """
    Manually test SMTP connection step by step
    """
    print(f"Testing SMTP connection to {server}:{port}")
    print("=" * 50)
    
    try:
        # Create socket connection
        print("1. Creating socket connection...")
        sock = socket.create_connection((server, port), timeout=30)
        print("✅ Socket connection established")
        
        # Read initial response
        response = sock.recv(1024).decode()
        print(f"Server greeting: {response.strip()}")
        
        # Send EHLO
        print("\n2. Sending EHLO...")
        sock.send(b"EHLO localhost\r\n")
        response = sock.recv(1024).decode()
        print(f"EHLO response: {response.strip()}")
        
        # Check if STARTTLS is supported
        if "STARTTLS" in response:
            print("\n3. STARTTLS is supported, attempting to start TLS...")
            sock.send(b"STARTTLS\r\n")
            response = sock.recv(1024).decode()
            print(f"STARTTLS response: {response.strip()}")
            
            if "220" in response:
                print("4. Wrapping socket with TLS...")
                try:
                    # Create SSL context
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    
                    # Wrap socket
                    tls_sock = context.wrap_socket(sock, server_hostname=server)
                    print("✅ TLS connection established")
                    
                    # Send EHLO again after TLS
                    tls_sock.send(b"EHLO localhost\r\n")
                    response = tls_sock.recv(1024).decode()
                    print(f"EHLO after TLS: {response.strip()}")
                    
                    # Try authentication
                    if username and password:
                        print("\n5. Attempting authentication...")
                        tls_sock.send(b"AUTH LOGIN\r\n")
                        response = tls_sock.recv(1024).decode()
                        print(f"AUTH LOGIN response: {response.strip()}")
                        
                        if "334" in response:
                            # Send username
                            username_b64 = base64.b64encode(username.encode()).decode()
                            tls_sock.send(f"{username_b64}\r\n".encode())
                            response = tls_sock.recv(1024).decode()
                            print(f"Username response: {response.strip()}")
                            
                            # Send password
                            password_b64 = base64.b64encode(password.encode()).decode()
                            tls_sock.send(f"{password_b64}\r\n".encode())
                            response = tls_sock.recv(1024).decode()
                            print(f"Password response: {response.strip()}")
                            
                            if "235" in response:
                                print("✅ Authentication successful!")
                                
                                # Try to send a test email
                                print("\n6. Sending test email...")
                                recipient = "darlingtonmuzari@gmail.com"
                                
                                # MAIL FROM
                                tls_sock.send(f"MAIL FROM:<{username}>\r\n".encode())
                                response = tls_sock.recv(1024).decode()
                                print(f"MAIL FROM response: {response.strip()}")
                                
                                # RCPT TO
                                tls_sock.send(f"RCPT TO:<{recipient}>\r\n".encode())
                                response = tls_sock.recv(1024).decode()
                                print(f"RCPT TO response: {response.strip()}")
                                
                                # DATA
                                tls_sock.send(b"DATA\r\n")
                                response = tls_sock.recv(1024).decode()
                                print(f"DATA response: {response.strip()}")
                                
                                if "354" in response:
                                    # Send email content
                                    email_content = f"""From: {username}
To: {recipient}
Subject: Test Email from Panic System

Hello,

This is a test email sent directly via SMTP to verify the email configuration.

If you receive this email, it means the SMTP setup is working correctly.

Best regards,
Panic System Team
.
"""
                                    tls_sock.send(email_content.encode())
                                    response = tls_sock.recv(1024).decode()
                                    print(f"Email send response: {response.strip()}")
                                    
                                    if "250" in response:
                                        print("✅ Email sent successfully!")
                                        return True
                            else:
                                print("❌ Authentication failed")
                    
                    tls_sock.close()
                    
                except ssl.SSLError as e:
                    print(f"❌ TLS error: {e}")
            else:
                print("❌ STARTTLS not accepted by server")
        else:
            print("❌ STARTTLS not supported by server")
        
        sock.close()
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    return False

def main():
    server = "mail.paniq.co.za"
    port = 587
    username = "no-reply@paniq.co.za"
    password = "14Dmin@2025"
    
    print("SMTP DEBUG TEST")
    print("=" * 50)
    print(f"Server: {server}")
    print(f"Port: {port}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print("=" * 50)
    
    success = test_smtp_manual(server, port, username, password)
    
    print("\n" + "=" * 50)
    if success:
        print("✅ SMTP test completed successfully!")
        print("Email should have been sent to darlingtonmuzari@gmail.com")
    else:
        print("❌ SMTP test failed")
        print("Check the error messages above for details")
    print("=" * 50)

if __name__ == "__main__":
    main()