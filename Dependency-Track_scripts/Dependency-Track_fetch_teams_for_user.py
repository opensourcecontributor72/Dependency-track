#!/usr/bin/env python3
"""
OWASP Dependency-Track Users Lister

A professional Python script for fetching all teams associated with a specific user in OWASP Dependency-Track.
Supports command-line arguments and retrieves username from environment variables.

Requirements:
    pip install requests python-dotenv

Environment Variables (.env file):
    DEPENDENCY_TRACK_URL=https://your-dependency-track-instance.com
    DEPENDENCY_TRACK_API_KEY=your-existing-api-key
    USERNAME=username  # Default username to fetch teams for

Usage:
    python Dependency-Track_users_list.py                    # Fetch teams for user from .env
    python Dependency-Track_users_list.py --user "username"  # Override user from .env
    python Dependency-Track_users_list.py --list-teams       # List all teams and exit
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
        """Initialize the Dependency-Track API client."""
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
        """Make an HTTP request to the Dependency-Track API."""
        url = f"{self.base_url}/api{endpoint}"
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
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
    
    def get_teams(self) -> List[Team]:
        """Retrieve all teams from Dependency-Track."""
        self.logger.info("Retrieving teams from Dependency-Track")
        
        response = self._make_request('GET', '/v1/team')
        teams_data = response.json()
        
        teams = []
        for team_data in teams_data:
            team = Team(
                uuid=team_data['uuid'],
                name=team_data['name'],
                permissions=team_data.get('permissions', [])
            )
            teams.append(team)
        
        self.logger.info(f"Retrieved {len(teams)} teams")
        return teams
    
    def get_all_users(self) -> List[User]:
        """Retrieve all users from Dependency-Track."""
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
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieve a user by username."""
        all_users = self.get_all_users()
        for user in all_users:
            if user.username.lower() == username.lower():
                return user
        return None

def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    logs_dir = os.path.join(project_root, "logs")
    
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except PermissionError:
        print(f"Error: No permission to create {logs_dir}. Logging to console only.")
        logs_dir = os.path.dirname(__file__)
    
    log_filename = os.path.join(logs_dir, "dependency_track_client.log")
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def load_environment() -> Dict[str, str]:
    """Load environment variables from .env file."""
    load_dotenv()
    
    required_vars = {
        'DEPENDENCY_TRACK_URL': os.getenv('DEPENDENCY_TRACK_URL'),
        'DEPENDENCY_TRACK_API_KEY': os.getenv('DEPENDENCY_TRACK_API_KEY'),
        'USERNAME': os.getenv('USERNAME')
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value and var != 'USERNAME']
    
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Please create a .env file with:")
        print("   DEPENDENCY_TRACK_URL=https://your-dependency-track-instance.com")
        print("   DEPENDENCY_TRACK_API_KEY=your-existing-api-key")
        print("   USERNAME=username  # Optional, can be overridden with --user")
        sys.exit(1)
    
    return required_vars

def display_teams(teams: List[Team]) -> None:
    """Display teams in a formatted table."""
    if not teams:
        print("No teams found.")
        return
    
    print(f"\n📋 Available Teams ({len(teams)} total):")
    print("=" * 100)
    print(f"{'#':<3} {'Name':<40} {'UUID':<40} {'Permissions'}")
    print("-" * 100)
    
    for i, team in enumerate(teams, 1):
        permissions_str = f"{len(team.permissions)} permissions"
        if team.permissions:
            first_perms = ', '.join(team.permissions[:2])
            if len(team.permissions) > 2:
                permissions_str = f"{first_perms} (+{len(team.permissions)-2} more)"
            else:
                permissions_str = first_perms
        
        print(f"{i:<3} {team.name:<40} {team.uuid:<40} {permissions_str}")
    
    print("-" * 100)

def display_user_teams(user: User) -> None:
    """Display teams associated with a user."""
    if not user or not user.teams:
        print("No teams found for the user.")
        return
    
    print(f"\n📋 Teams for User '{user.username}' ({len(user.teams)} total):")
    print("=" * 100)
    print(f"{'#':<3} {'Team Name':<40}")
    print("-" * 100)
    
    for i, team_name in enumerate(user.teams, 1):
        print(f"{i:<3} {team_name:<40}")
    
    print("-" * 100)

def save_response_to_json(username: str, teams: List[str]) -> None:
    """Save the teams list response to a JSON file."""
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    results_dir = os.path.join(project_root, "results")
    
    try:
        os.makedirs(results_dir, exist_ok=True)
    except PermissionError:
        print(f"Error: No permission to create {results_dir}. Response not saved.")
        return
    
    json_filename = os.path.join(results_dir, "dependency_track_api_response.json")
    
    response_data = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
            "script_name": "users_list.py",
            "description": "OWASP Dependency-Track Teams List Response",
            "version": "1.0",
            "timezone": "IST"
        },
        "user": {
            "username": username,
            "teams": teams
        }
    }
    
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=4)
        print(f"💾 Response saved to: {json_filename}")
    except PermissionError:
        print(f"Error: No permission to write to {json_filename}. Response not saved.")

def fetch_teams_for_user(client: DependencyTrackClient, username: str) -> bool:
    """Fetch and display teams for a specific user."""
    logger = logging.getLogger(__name__)
    
    user = client.get_user_by_username(username)
    if not user:
        print(f"User '{username}' not found.")
        return False
    
    print(f"✅ Found user: {user.username}")
    print(f"   Email: {user.email}")
    print(f"   Full Name: {user.fullname}")
    print(f"   Permissions: {len(user.permissions)}")
    
    try:
        print("\n⏳ Fetching teams for the user...")
        teams = user.teams
        
        print(f"\n🎉 SUCCESS! Retrieved {len(teams)} teams for user '{user.username}':")
        display_user_teams(user)
        save_response_to_json(user.username, teams)
        return True
        
    except DependencyTrackAPIError as e:
        print(f"Failed to fetch teams: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fetch all teams for a specific user in OWASP Dependency-Track",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python Dependency-Track_users_list.py                   # Fetch teams for user from .env
  python Dependency-Track_users_list.py --user "username" # Override user from .env
  python Dependency-Track_users_list.py --list-teams      # List all teams and exit
        """
    )
    
    parser.add_argument('--user', '-u', type=str, help='Username to fetch teams for (overrides .env)')
    parser.add_argument('--list-teams', '-l', action='store_true', help='List all teams and exit')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        print("Dependency-Track Users Lister")
        print("=" * 50)
        
        env_vars = load_environment()
        
        print("🔗 Connecting to Dependency-Track...")
        client = DependencyTrackClient(
            base_url=env_vars['DEPENDENCY_TRACK_URL'],
            api_key=env_vars['DEPENDENCY_TRACK_API_KEY']
        )
        
        teams = client.get_teams()
        print(f"✅ Connected! Found {len(teams)} teams.")
        
        if args.list_teams:
            display_teams(teams)
            sys.exit(0)
        
        username = args.user if args.user else env_vars.get('USERNAME')
        if not username:
            print("Error: No username provided. Please set USERNAME in .env or use --user.")
            sys.exit(1)
        
        success = fetch_teams_for_user(client, username)
        sys.exit(0 if success else 1)
        
    except DependencyTrackAPIError as e:
        logger.error(f"Dependency-Track API error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Script interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()