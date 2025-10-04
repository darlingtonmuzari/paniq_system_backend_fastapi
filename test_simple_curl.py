#!/usr/bin/env python3
"""
Direct curl test for password reset endpoint
"""

import subprocess
import json

# Simple curl request
def test_with_curl():
    """Test password reset with curl"""
    
    url = "http://localhost:8000/api/v1/auth/mobile/password-reset/request"
    
    payload = {
        "email": "darlingtonmuzari@gmail.com",
        "device_info": {
            "device_id": "curl-test-device",
            "device_type": "web",
            "device_model": "curl",
            "os_version": "Linux",
            "app_version": "1.0.0",
            "platform_version": "curl-1.0"
        }
    }
    
    curl_command = [
        "curl", "-X", "POST",
        "-H", "Content-Type: application/json",
        "-H", "X-Platform: web",
        "-d", json.dumps(payload),
        "-v",  # verbose output
        url
    ]
    
    print("Running curl command:")
    print(" ".join(curl_command))
    print("-" * 50)
    
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, timeout=10)
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        print("curl command timed out after 10 seconds")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_with_curl()