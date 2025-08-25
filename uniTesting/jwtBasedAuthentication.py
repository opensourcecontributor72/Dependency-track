import os
import requests
import json
from datetime import datetime
import base64
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

def decode_jwt_payload(token):
    """Decode JWT payload for inspection (without verification)"""
    try:
        # JWT structure: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        # Decode payload (second part)
        payload = parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        
        decoded_bytes = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded_bytes.decode('utf-8'))
        
        return payload_data
    except Exception as e:
        print(f"Could not decode JWT payload: {e}")
        return None

def get_jwt_token_simple():
    """Simple JWT token authentication for DTrack"""
    
    # Configuration
    BASE_URL = "https://dependency-track.tools.aa.st"
    USERNAME = os.getenv("DT_USERNAME")
    PASSWORD = os.getenv("DT_PASSWORD")
    
    login_url = f"{BASE_URL}/api/v1/user/login"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    
    try:
        print("🔐 Authenticating with DTrack...")
        print(f"URL: {login_url}")
        
        response = requests.post(login_url, headers=headers, data=data, timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            token = response.text.strip()
            
            if token.startswith('eyJ'):
                print("JWT Token received successfully!")
                print(f"Token length: {len(token)} characters")
                print(f"Token preview: {token[:50]}...")
                
                # Decode token payload for inspection
                payload = decode_jwt_payload(token)
                if payload:
                    print("\nToken Information:")
                    print(f"   Subject: {payload.get('sub', 'N/A')}")
                    print(f"   Issuer: {payload.get('iss', 'N/A')}")
                    print(f"   Issued at: {datetime.fromtimestamp(payload.get('iat', 0))}")
                    print(f"   Expires at: {datetime.fromtimestamp(payload.get('exp', 0))}")
                
                # Create response structure
                response_data = {
                    "timestamp": datetime.now().isoformat(),
                    "status_code": response.status_code,
                    "url": login_url,
                    "authentication_successful": True,
                    "jwt_token": token,
                    "token_type": "Bearer",
                    "token_length": len(token),
                    "decoded_payload": payload
                }
                
                # Save to JSON file
                output_file = "jwt_token.json"
                with open(output_file, 'w') as f:
                    json.dump(response_data, f, indent=2)
                
                print(f"\n💾 Response saved to: {output_file}")
                
                # Also save just the token for easy access
                token_file = "token.txt"
                with open(token_file, 'w') as f:
                    f.write(token)
                print(f"Token saved to: {token_file}")
                
                return token
            else:
                print(f"Unexpected response format: {token[:100]}...")
                return None
        else:
            print(f"Authentication failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def test_token_usage(token):
    """Test using the JWT token to make an API call"""
    if not token:
        return
    
    print("\nTesting token with API call...")
    
    # Try to get projects (common DTrack endpoint)
    test_url = "https://dependency-track.tools.aa.st/api/v1/project"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(test_url, headers=headers, timeout=30)
        print(f"Test API call status: {response.status_code}")
        
        if response.status_code == 200:
            print("Token is valid and working!")
            data = response.json()
            print(f"Retrieved {len(data)} projects")
        else:
            print(f"Token test failed: {response.text[:200]}")
            
    except Exception as e:
        print(f"Token test error: {e}")

if __name__ == "__main__":
    print("DTrack JWT Authentication")
    print("=" * 40)
    
    # Get JWT token
    jwt_token = get_jwt_token_simple()
    
    if jwt_token:
        # Test the token
        test_token_usage(jwt_token)
        
        print("\nAuthentication complete!")
        print("You can now use the token for API calls:")
        print(f"Authorization: Bearer {jwt_token[:50]}...")
    else:
        print("\nAuthentication failed!")