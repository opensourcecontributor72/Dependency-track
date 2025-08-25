#!/usr/bin/env python3
"""
OWASP Dependency-Track Users Lister

A professional Python script for fetching all users of a specific team in OWASP Dependency-Track.
Supports command-line arguments and retrieves team name from environment variables.

Requirements:
    pip install requests python-dotenv

Environment Variables (.env file):
    DEPENDENCY_TRACK_URL=https://your-dependency-track-instance.com
    DEPENDENCY_TRACK_API_KEY=your-existing-api-key
    TEAM_NAME=TeamName  # Default team name to fetch users for

Usage:
    python Dependency-Track_users_list.py                    # Fetch users for team from .env
    python Dependency-Track_users_list.py --team "TeamName"  # Override team from .env
    python Dependency-Track_users_list.py --list-teams       # List all teams
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
    permissions: List[str] = None
    
    def __post_init__(self):
        if self.teams is None:
            self.teams = []
        if self.permissions is None:
            self.permissions = []
    
    @property
    def is_active(self) -> bool:
        """Check if user is active (not suspended)."""
        return not self.suspended
    
    @property
    def last_login_formatted(self) -> str:
        """Format last login date for display."""
        if not self.last_login:
            return "Never"
        try:
            date_obj = datetime.fromisoformat(self.last_login.replace('Z', '+00:00'))
            return date_obj.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            return self.last_login

@dataclass
class Team:
    """Data class representing a Dependency-Track team."""
    uuid: str
    name: str
    permissions: List[str]
    users: List[User] = None
    
    def __post_init__(self):
        if self.users is None:
            self.users = []
    
    @property
    def user_count(self) -> int:
        """Get the number of users in the team."""
        return len(self.users)

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
    
    def find_team_by_name(self, team_name: str) -> Optional[Team]:
        """Find a team by its name (case-insensitive)."""
        teams = self.get_teams()
        for team in teams:
            if team.name.lower() == team_name.lower():
                return team
        return None
    
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
    
    def get_team_users(self, team_name: str) -> List[User]:
        """Retrieve all users for a specific team by filtering all users."""
        all_users = self.get_all_users()
        team = self.find_team_by_name(team_name)
        if not team:
            return []
        
        return [user for user in all_users if team_name.lower() in [t.lower() for t in user.teams]]

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
        'TEAM_NAME': os.getenv('TEAM_NAME')
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value and var != 'TEAM_NAME']
    
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Please create a .env file with:")
        print("   DEPENDENCY_TRACK_URL=https://your-dependency-track-instance.com")
        print("   DEPENDENCY_TRACK_API_KEY=your-existing-api-key")
        print("   TEAM_NAME=TeamName  # Optional, can be overridden with --team")
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

def display_users(users: List[User]) -> None:
    """Display users in a formatted table."""
    if not users:
        print("No users found for the team.")
        return
    
    print(f"\n📋 Users for the Team ({len(users)} total):")
    print("=" * 150)
    print(f"{'#':<3} {'Username':<30} {'Full Name':<30} {'Email':<40} {'Status':<10} {'Last Login'}")
    print("-" * 150)
    
    for i, user in enumerate(users, 1):
        status = "🟢 Active" if user.is_active else "🔴 Suspended"
        if user.force_password_change:
            status += " (Pwd Reset)"
        
        print(f"{i:<3} {user.username:<30} {user.fullname[:29] + '...' if len(user.fullname) > 29 else user.fullname:<30} "
              f"{user.email[:39] + '...' if len(user.email) > 39 else user.email:<40} {status:<10} {user.last_login_formatted}")

def save_response_to_json(team_name: str, users: List[User]) -> None:
    """Save the users list response to a JSON file."""
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
            "description": "OWASP Dependency-Track Users List Response",
            "version": "1.0",
            "timezone": "CEST"
        },
        "team": {
            "name": team_name,
            "users": [
                {
                    "username": user.username,
                    "email": user.email,
                    "fullname": user.fullname,
                    "last_login": user.last_login,
                    "created": user.created,
                    "suspended": user.suspended,
                    "force_password_change": user.force_password_change,
                    "non_expiry_password": user.non_expiry_password,
                    "teams": user.teams,
                    "permissions": user.permissions
                } for user in users
            ]
        }
    }
    
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=4)
        print(f"💾 Response saved to: {json_filename}")
    except PermissionError:
        print(f"Error: No permission to write to {json_filename}. Response not saved.")

def fetch_users_for_team(client: DependencyTrackClient, team_name: str) -> bool:
    """Fetch and display users for a specific team."""
    logger = logging.getLogger(__name__)
    
    team = client.find_team_by_name(team_name)
    if not team:
        print(f"Team '{team_name}' not found.")
        teams = client.get_teams()
        similar_teams = [t for t in teams if team_name.lower() in t.name.lower()]
        if similar_teams:
            print(f"\n💡 Did you mean one of these teams?")
            for t in similar_teams:
                print(f"   - {t.name}")
        return False
    
    print(f"✅ Found team: {team.name}")
    print(f"   UUID: {team.uuid}")
    print(f"   Permissions: {len(team.permissions)}")
    
    try:
        print("\n⏳ Fetching users for the team...")
        users = client.get_team_users(team.name)
        team.users = users
        
        print(f"\n🎉 SUCCESS! Retrieved {len(users)} users for team '{team.name}':")
        display_users(users)
        save_response_to_json(team.name, users)
        return True
        
    except DependencyTrackAPIError as e:
        print(f"Failed to fetch users: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fetch all users for a specific team in OWASP Dependency-Track",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python Dependency-Track_users_list.py                   # Fetch users for team from .env
  python Dependency-Track_users_list.py --team "TeamName" # Override team from .env
  python Dependency-Track_users_list.py --list-teams      # List all teams
        """
    )
    
    parser.add_argument('--team', '-t', type=str, help='Team name to fetch users for (overrides .env)')
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
        
        team_name = args.team if args.team else env_vars.get('TEAM_NAME')
        if not team_name:
            print("Error: No team name provided. Please set TEAM_NAME in .env or use --team.")
            sys.exit(1)
        
        success = fetch_users_for_team(client, team_name)
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