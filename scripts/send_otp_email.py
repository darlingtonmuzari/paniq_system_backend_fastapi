#!/usr/bin/env python3
"""
Script to send OTP verification emails for user registration
"""
import asyncio
import sys
import requests
import json
from typing import Optional

API_BASE_URL = "http://localhost:8000"

def send_verification_otp(email: str) -> dict:
    """
    Send verification OTP to the specified email address
    
    Args:
        email: Email address to send OTP to
        
    Returns:
        Response from the API
    """
    url = f"{API_BASE_URL}/api/v1/auth/resend-verification"
    
    payload = {
        "email": email
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json(),
                "message": "OTP sent successfully"
            }
        else:
            return {
                "success": False,
                "error": response.json(),
                "message": f"Failed to send OTP: {response.status_code}"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Network error occurred"
        }

def verify_otp(email: str, otp: str) -> dict:
    """
    Verify OTP for the specified email address
    
    Args:
        email: Email address
        otp: OTP code to verify
        
    Returns:
        Response from the API
    """
    url = f"{API_BASE_URL}/api/v1/auth/verify-account"
    
    payload = {
        "email": email,
        "otp": otp
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json(),
                "message": "OTP verified successfully"
            }
        else:
            return {
                "success": False,
                "error": response.json(),
                "message": f"Failed to verify OTP: {response.status_code}"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Network error occurred"
        }

def register_user(email: str, phone: str, first_name: str, last_name: str) -> dict:
    """
    Register a new user
    
    Args:
        email: User email
        phone: User phone number
        first_name: User first name
        last_name: User last name
        
    Returns:
        Response from the API
    """
    url = f"{API_BASE_URL}/api/v1/users/register"
    
    payload = {
        "email": email,
        "phone": phone,
        "first_name": first_name,
        "last_name": last_name
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json(),
                "message": "User registered successfully"
            }
        else:
            return {
                "success": False,
                "error": response.json(),
                "message": f"Failed to register user: {response.status_code}"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Network error occurred"
        }

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python send_otp_email.py send <email>")
        print("  python send_otp_email.py verify <email> <otp>")
        print("  python send_otp_email.py register <email> <phone> <first_name> <last_name>")
        print("\nExamples:")
        print("  python send_otp_email.py send user@example.com")
        print("  python send_otp_email.py verify user@example.com 123456")
        print("  python send_otp_email.py register user@example.com +1234567890 John Doe")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "send":
        if len(sys.argv) != 3:
            print("Usage: python send_otp_email.py send <email>")
            sys.exit(1)
        
        email = sys.argv[2]
        print(f"Sending OTP to {email}...")
        
        result = send_verification_otp(email)
        
        if result["success"]:
            print("✅ " + result["message"])
            print(f"Response: {json.dumps(result['data'], indent=2)}")
        else:
            print("❌ " + result["message"])
            print(f"Error: {json.dumps(result['error'], indent=2)}")
    
    elif command == "verify":
        if len(sys.argv) != 4:
            print("Usage: python send_otp_email.py verify <email> <otp>")
            sys.exit(1)
        
        email = sys.argv[2]
        otp = sys.argv[3]
        print(f"Verifying OTP {otp} for {email}...")
        
        result = verify_otp(email, otp)
        
        if result["success"]:
            print("✅ " + result["message"])
            print(f"Response: {json.dumps(result['data'], indent=2)}")
        else:
            print("❌ " + result["message"])
            print(f"Error: {json.dumps(result['error'], indent=2)}")
    
    elif command == "register":
        if len(sys.argv) != 6:
            print("Usage: python send_otp_email.py register <email> <phone> <first_name> <last_name>")
            sys.exit(1)
        
        email = sys.argv[2]
        phone = sys.argv[3]
        first_name = sys.argv[4]
        last_name = sys.argv[5]
        
        print(f"Registering user {first_name} {last_name} with email {email}...")
        
        result = register_user(email, phone, first_name, last_name)
        
        if result["success"]:
            print("✅ " + result["message"])
            print(f"Response: {json.dumps(result['data'], indent=2)}")
            
            # Automatically send verification OTP
            print("\nSending verification OTP...")
            otp_result = send_verification_otp(email)
            
            if otp_result["success"]:
                print("✅ Verification OTP sent")
                print("Check the application logs for the OTP code (since SMTP is not configured)")
            else:
                print("❌ Failed to send verification OTP")
        else:
            print("❌ " + result["message"])
            print(f"Error: {json.dumps(result['error'], indent=2)}")
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: send, verify, register")
        sys.exit(1)

if __name__ == "__main__":
    main()