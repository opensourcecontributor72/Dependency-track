#!/usr/bin/env python3
"""
OWASP Dependency-Track User Authentication Checker

Checks if a user exists in OWASP Dependency-Track by username or email.
Uses JWT authentication with username/password.
"""

import os
import sys
import argparse
import logging
import requests
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import json
import base64
from datetime import datetime

@dataclass
class User:
    """Data class representing a Dependency-Track user."""
    username: str
    email: str
    fullname: str
    last_login: Optional[str] = None
    created: Optional[str] = None
    suspended: bool = False
    force_password_change: bool = False
    non_expiry_password: bool = False

class DependencyTrackAPIError(Exception):
    """Custom exception for Dependency-Track API errors."""
    pass

class DependencyTrackClient:
    """Client for OWASP Dependency-Track API operations."""
    
    def __init__(self, base_url: str, admin_api_key: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.admin_api_key = admin_api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.jwt_token = None
        
        # Setup admin session for user lookups
        self.admin_session = requests.Session()
        self.admin_session.headers.update({
            'X-API-Key': self.admin_api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'DependencyTrack-UserAuthChecker/1.0'
        })
        
        self.logger = logging.getLogger(__name__)
    
    def decode_jwt_payload(self, token):
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
            self.logger.debug(f"Could not decode JWT payload: {e}")
            return None
    
    def _authenticate(self, username: str, password: str):
        """Authenticate with Dependency-Track and get JWT token"""
        login_url = f"{self.base_url}/api/v1/user/login"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "username": username,
            "password": password
        }
        
        try:
            self.logger.info(f"Authenticating with Dependency-Track using username: {username}")
            response = requests.post(login_url, headers=headers, data=data, timeout=self.timeout)
            
            if response.status_code == 200:
                token = response.text.strip()
                
                if token.startswith('eyJ'):
                    self.jwt_token = token
                    self.logger.info("JWT Token received successfully!")
                    self.logger.debug(f"Token length: {len(token)} characters")
                    
                    # Update session headers with the JWT token
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.jwt_token}',
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'User-Agent': 'DependencyTrack-UserAuthChecker/1.0'
                    })
                    
                    # Decode token payload for inspection
                    payload = self.decode_jwt_payload(token)
                    if payload:
                        self.logger.debug("Token Information:")
                        self.logger.debug(f"Subject: {payload.get('sub', 'N/A')}")
                        self.logger.debug(f"Issued at: {datetime.fromtimestamp(payload.get('iat', 0))}")
                        self.logger.debug(f"Expires at: {datetime.fromtimestamp(payload.get('exp', 0))}")
                else:
                    raise DependencyTrackAPIError(f"Unexpected response format: {token[:100]}...")
            else:
                raise DependencyTrackAPIError(f"Authentication failed with status {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise DependencyTrackAPIError(f"Authentication request failed: {e}")
    
    def _make_admin_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request using admin API key"""
        url = f"{self.base_url}/api{endpoint}"
        try:
            self.logger.debug(f"Making admin {method} request to {url}")
            response = self.admin_session.request(method=method, url=url, timeout=self.timeout, **kwargs)
            self.logger.debug(f"Admin response status: {response.status_code}")
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            error_msg = f"Admin API request failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except (ValueError, KeyError):
                    error_msg += f" - HTTP {e.response.status_code}"
            self.logger.error(error_msg)
            raise DependencyTrackAPIError(error_msg) from e
    
    def get_username_from_email(self, email: str) -> Optional[str]:
        """
        Get username from email using admin API key to lookup all users.
        
        Args:
            email: Email address to lookup
            
        Returns:
            Username if found, None otherwise
        """
        self.logger.info(f"Looking up username for email: {email}")
        try:
            response = self._make_admin_request('GET', '/v1/user/managed')
            all_users = response.json()
            
            email_lower = email.lower().strip()
            
            for user_data in all_users:
                if user_data.get('email').lower() == email_lower:
                    username = user_data.get('username')
                    self.logger.info(f"Found username '{username}' for email: {email}")
                    return username
            
            self.logger.warning(f"No username found for email: {email}")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to lookup username for email {email}: {e}")
            return None
    
    def authenticate_with_identifier(self, identifier: str, password: str) -> str:
        """
        Authenticate with either username or email, always returning the actual username.
        
        Args:
            identifier: Username or email address
            password: User's password
            
        Returns:
            The actual username used for authentication
            
        Raises:
            DependencyTrackAPIError: If authentication fails
        """
        # First, try to authenticate directly with the identifier (assuming it's a username)
        try:
            self._authenticate(identifier, password)
            self.logger.info(f"Successfully authenticated with identifier as username: {identifier}")
            return identifier
        except DependencyTrackAPIError as e:
            self.logger.debug(f"Direct authentication failed: {e}")
        
        # If direct authentication failed and identifier looks like an email, lookup the username
        if '@' in identifier:
            username = self.get_username_from_email(identifier)
            if username:
                try:
                    self._authenticate(username, password)
                    self.logger.info(f"Successfully authenticated with username: {username} (looked up from email: {identifier})")
                    return username
                except DependencyTrackAPIError as e:
                    self.logger.error(f"Authentication failed with looked-up username '{username}': {e}")
                    raise DependencyTrackAPIError(f"Authentication failed for email {identifier}. Username '{username}' found but authentication failed.")
            else:
                raise DependencyTrackAPIError(f"No username found for email: {identifier}")
        
        # If all attempts failed, raise an error
        raise DependencyTrackAPIError(f"Authentication failed for identifier: {identifier}. Please ensure you're using the correct username or email and password.")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request to Dependency-Track API"""
        if not self.jwt_token:
            raise DependencyTrackAPIError("No valid JWT token available")
        
        url = f"{self.base_url}/api{endpoint}"
        try:
            self.logger.debug(f"Making {method} request to {url}")
            response = self.session.request(method=method, url=url, timeout=self.timeout, **kwargs)
            self.logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except (ValueError, KeyError):
                    error_msg += f" - HTTP {e.response.status_code}"
            self.logger.error(error_msg)
            raise DependencyTrackAPIError(error_msg) from e
    
    def get_all_users(self) -> list:
        """Get all managed users from Dependency-Track using admin API key"""
        self.logger.info("Retrieving all users from Dependency-Track using admin API key")
        response = self._make_admin_request('GET', '/v1/user/managed')
        return response.json()
    
    def get_user_by_username_or_email(self, identifier: str) -> Optional[User]:
        """
        Search for a user by username or email address.
        
        Args:
            identifier: Username or email address to search for
            
        Returns:
            User object if found, None otherwise
        """
        self.logger.info(f"Searching for user by identifier: {identifier}")
        all_users = self.get_all_users()
        
        # Convert identifier to lowercase for case-insensitive comparison
        identifier_lower = identifier.lower().strip()
        
        for user_data in all_users:
            # Check if identifier matches username (case-insensitive)
            if user_data.get('username', '').lower() == identifier_lower:
                self.logger.info(f"Found user by username: {user_data.get('username')}")
                return User(
                    username=user_data.get('username', ''),
                    email=user_data.get('email', ''),
                    fullname=user_data.get('fullname', ''),
                    last_login=user_data.get('lastLogin'),
                    created=user_data.get('created'),
                    suspended=user_data.get('suspended', False),
                    force_password_change=user_data.get('forcePasswordChange', False),
                    non_expiry_password=user_data.get('nonExpiryPassword', False)
                )
            
            # Check if identifier matches email (case-insensitive)
            if user_data.get('email', '').lower() == identifier_lower:
                self.logger.info(f"Found user by email: {user_data.get('email')}")
                return User(
                    username=user_data.get('username', ''),
                    email=user_data.get('email', ''),
                    fullname=user_data.get('fullname', ''),
                    last_login=user_data.get('lastLogin'),
                    created=user_data.get('created'),
                    suspended=user_data.get('suspended', False),
                    force_password_change=user_data.get('forcePasswordChange', False),
                    non_expiry_password=user_data.get('nonExpiryPassword', False)
                )
        
        self.logger.warning(f"No user found with username or email: {identifier}")
        return None

def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def load_environment() -> dict:
    """Load and validate environment variables"""
    load_dotenv()
    required_vars = {
        'DEPENDENCY_TRACK_URL': os.getenv('DEPENDENCY_TRACK_URL'),
        'DEPENDENCY_TRACK_ADMIN_API_KEY': os.getenv('DEPENDENCY_TRACK_ADMIN_API_KEY')
    }
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")
    return required_vars

def main():
    parser = argparse.ArgumentParser(
        description="Check if a user exists in OWASP Dependency-Track by username or email",
        epilog="The script accepts either a username or email address to verify user existence."
    )
    parser.add_argument(
        '--user', '-u', 
        type=str, 
        required=True, 
        help='Username or email address to check'
    )
    parser.add_argument(
        '--password', '-p',
        type=str,
        required=True,
        help='Password for authentication'
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        env_vars = load_environment()
        client = DependencyTrackClient(
            base_url=env_vars['DEPENDENCY_TRACK_URL'],
            admin_api_key=env_vars['DEPENDENCY_TRACK_ADMIN_API_KEY']
        )
        
        # Authenticate and get the actual username used for authentication
        actual_username = client.authenticate_with_identifier(args.user, args.password)
        
        # Now search for the user (could be different from actual_username if email was provided)
        user = client.get_user_by_username_or_email(args.user)
        if not user:
            error_msg = f"User with username or email '{args.user}' not found."
            logger.error(error_msg)
            print(json.dumps({"success": False, "message": error_msg}), file=sys.stdout)
            sys.exit(1)
        
        result = {
            "success": True,
            "message": f"User '{user.username}' found",
            "username": user.username,
            "email": user.email,
            "fullname": user.fullname,
            "authenticated_as": actual_username  # Shows which username was used for JWT auth
        }
        
        logger.info(f"Successfully verified user {user.username} (authenticated as: {actual_username})")
        print(json.dumps(result), file=sys.stdout)
        sys.exit(0)
        
    except DependencyTrackAPIError as e:
        logger.error(f"Dependency-Track API error: {e}")
        print(json.dumps({"success": False, "message": str(e)}), file=sys.stdout)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(json.dumps({"success": False, "message": str(e)}), file=sys.stdout)
        sys.exit(1)

if __name__ == "__main__":
    main()