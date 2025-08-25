#!/usr/bin/env python3
"""
OWASP Dependency-Track Users Lister

Fetches all teams for a specific user in OWASP Dependency-Track and outputs as JSON.
Supports searching by both username and email.
"""

import os
import sys
import argparse
import logging
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import json
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
    teams: List[str] = None
    permissions: List[dict] = None
    
    def __post_init__(self):
        if self.teams is None:
            self.teams = []
        if self.permissions is None:
            self.permissions = []

@dataclass
class Team:
    """Data class representing a Dependency-Track team."""
    uuid: str
    name: str
    permissions: List[str]

class DependencyTrackAPIError(Exception):
    """Custom exception for Dependency-Track API errors."""
    pass

class DependencyTrackClient:
    """Client for OWASP Dependency-Track API operations."""
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'DependencyTrack-UsersLister/1.0'
        })
        
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
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
    
    def get_all_users(self) -> List[User]:
        self.logger.info("Retrieving all users from Dependency-Track")
        response = self._make_request('GET', '/v1/user/managed')
        users_data = response.json()
        users = []
        for user_data in users_data:
            user = User(
                username=user_data.get('username', ''),
                email=user_data.get('email', ''),
                fullname=user_data.get('fullname', ''),
                last_login=user_data.get('lastLogin'),
                created=user_data.get('created'),
                suspended=user_data.get('suspended', False),
                force_password_change=user_data.get('forcePasswordChange', False),
                non_expiry_password=user_data.get('nonExpiryPassword', False),
                teams=[t.get('name', '') for t in user_data.get('teams', [])],
                permissions=user_data.get('permissions', [])
            )
            users.append(user)
        self.logger.info(f"Retrieved {len(users)} total users")
        return users
    
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
        
        for user in all_users:
            # Check if identifier matches username (case-insensitive)
            if user.username and user.username.lower() == identifier_lower:
                self.logger.info(f"Found user by username: {user.username}")
                return user
            
            # Check if identifier matches email (case-insensitive)
            if user.email and user.email.lower() == identifier_lower:
                self.logger.info(f"Found user by email: {user.email}")
                return user
        
        self.logger.warning(f"No user found with username or email: {identifier}")
        return None

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def load_environment() -> Dict[str, str]:
    load_dotenv()
    required_vars = {
        'DEPENDENCY_TRACK_URL': os.getenv('DEPENDENCY_TRACK_URL'),
        'DEPENDENCY_TRACK_API_KEY': os.getenv('DEPENDENCY_TRACK_API_KEY')
    }
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")
    return required_vars

def main():
    parser = argparse.ArgumentParser(
        description="Fetch all teams for a specific user in OWASP Dependency-Track",
        epilog="The script accepts either a username or email address to identify the user."
    )
    parser.add_argument(
        '--user', '-u', 
        type=str, 
        required=True, 
        help='Username or email address to fetch teams for'
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        env_vars = load_environment()
        client = DependencyTrackClient(
            base_url=env_vars['DEPENDENCY_TRACK_URL'],
            api_key=env_vars['DEPENDENCY_TRACK_API_KEY']
        )
        
        user = client.get_user_by_username_or_email(args.user)
        if not user:
            error_msg = f"User with username or email '{args.user}' not found."
            logger.error(error_msg)
            print(json.dumps({"error": error_msg}), file=sys.stdout)
            sys.exit(1)
        
        result = {
            "username": user.username,
            "email": user.email,
            "fullname": user.fullname,
            "teams": user.teams,
            "found_by": "username" if user.username.lower() == args.user.lower().strip() else "email"
        }
        
        logger.info(f"Successfully found user {user.username} with {len(user.teams)} teams")
        print(json.dumps(result), file=sys.stdout)
        sys.exit(0)
        
    except DependencyTrackAPIError as e:
        logger.error(f"Dependency-Track API error: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        sys.exit(1)

if __name__ == "__main__":
    main()