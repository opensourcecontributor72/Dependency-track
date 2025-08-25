#!/usr/bin/env python3
"""
OWASP Dependency-Track API Key Generator

A professional Python script for generating API keys for specific teams in OWASP Dependency-Track.
Supports command-line arguments and retrieves team name from environment variables.

Requirements:
    pip install requests python-dotenv

Environment Variables (.env file):
    DEPENDENCY_TRACK_URL=https://your-dependency-track-instance.com
    DEPENDENCY_TRACK_API_KEY=your-existing-api-key
    TEAM_NAME=TeamName  # Default team name to generate API key for

Usage:
    python generate_api_key.py                    # Generate API key for team from .env
    python generate_api_key.py --team "TeamName"  # Override team from .env
    python generate_api_key.py --list-teams       # List all teams
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
class Team:
    """Data class representing a Dependency-Track team."""
    uuid: str
    name: str
    permissions: List[str]
    
    def has_permission(self, permission: str) -> bool:
        """Check if team has a specific permission."""
        return permission in self.permissions


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
        
        # Set default headers
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'DependencyTrack-APIKeyGenerator/1.0'
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
    
    def generate_api_key(self, team_uuid: str) -> str:
        """Generate a new API key for the specified team."""
        self.logger.info(f"Generating API key for team: {team_uuid}")
        
        response = self._make_request('PUT', f'/v1/team/{team_uuid}/key')
        
        if response.text:
            api_key_data = response.json()  # Parse JSON response
            api_key = api_key_data.get('key', 'No key field found')  # Extract the 'key' field
            self.logger.info("API key generated successfully")
            return api_key
        else:
            raise DependencyTrackAPIError("No API key returned in response")


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Get the root project directory (parent of the script directory)
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    logs_dir = os.path.join(project_root, "logs")
    
    # Create logs directory
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except PermissionError:
        print(f"Error: No permission to create {logs_dir}. Logging to console only.")
        logs_dir = os.path.dirname(__file__)
    
    log_filename = os.path.join(logs_dir, "dependency_track_client.log")
    
    # Configure logger
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
        'TEAM_NAME': os.getenv('TEAM_NAME')  # New: Default team name from .env
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


def confirm_action(team: Team) -> bool:
    """Confirm API key generation action."""
    print(f"\n⚠️  WARNING: This will generate a new API key for team '{team.name}'")
    print("   Any existing API key for this team will be invalidated!")
    print(f"   Team UUID: {team.uuid}")
    print(f"   Team has {len(team.permissions)} permissions")
    
    while True:
        try:
            response = input("\n❓ Do you want to proceed? (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                print("Please enter 'yes' or 'no'")
        except KeyboardInterrupt:
            print("\n\n👋 Operation cancelled!")
            return False


def save_api_key_to_file(team_name: str, api_key: str) -> None:
    """Save the generated API key to a file."""
    try:
        filename = f"api_key_{team_name.replace(' ', '_').lower()}.txt"
        with open(filename, 'w') as f:
            f.write(f"Team: {team_name}\n")
            f.write(f"Generated: {os.popen('date').read().strip()}\n")
            f.write(f"API Key: {api_key}\n")
        
        print(f"💾 API key saved to: {filename}")
    except Exception as e:
        print(f"⚠️  Could not save API key to file: {e}")


def save_response_to_json(team_name: str, api_key: str) -> None:
    """Save the API key generation response to a JSON file."""
    # Get the root project directory (parent of the script directory)
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    results_dir = os.path.join(project_root, "results")
    
    # Create results directory
    try:
        os.makedirs(results_dir, exist_ok=True)
    except PermissionError:
        print(f"Error: No permission to create {results_dir}. Response not saved.")
        return
    
    # Use fixed JSON filename
    json_filename = os.path.join(results_dir, "dependency_track_api_response.json")
    
    response_data = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
            "script_name": "generate_api_key.py",
            "description": "OWASP Dependency-Track API Key Generation Response",
            "version": "1.0",
            "timezone": "CEST"
        },
        "team": {
            "name": team_name,
            "api_key": api_key
        }
    }
    
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=4)
        print(f"💾 Response saved to json")
    except PermissionError:
        print(f"Error: No permission to write to {json_filename}. Response not saved.")


def generate_api_key_for_team(client: DependencyTrackClient, team_name: str, 
                            save_to_file: bool = False, auto_confirm: bool = False) -> bool:
    """Generate API key for a specific team."""
    logger = logging.getLogger(__name__)
    
    # Find the team
    team = client.find_team_by_name(team_name)
    if not team:
        print(f"Team '{team_name}' not found.")
        
        # Suggest similar team names
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
    
    # Confirm action unless auto-confirm is enabled
    if not auto_confirm and not confirm_action(team):
        print("Operation cancelled.")
        return False
    
    try:
        # Generate the API key
        print("\n⏳ Generating API key...")
        new_api_key = client.generate_api_key(team.uuid)
        
        print(f"\n🎉 SUCCESS! New API key generated for team '{team.name}':")
        print(f"🔑 API Key: {new_api_key}")
        print("\n⚠️  IMPORTANT: Save this API key securely!")
        print("   This key cannot be retrieved again and any existing key is now invalid.")
        
        if save_to_file:
            save_api_key_to_file(team.name, new_api_key)
        
        # Save response to JSON
        save_response_to_json(team.name, new_api_key)
        
        return True
        
    except DependencyTrackAPIError as e:
        print(f"Failed to generate API key: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Generate API keys for OWASP Dependency-Track teams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_api_key.py                           # Generate for team from .env
  python generate_api_key.py --team "Security Team"    # Override team from .env
  python generate_api_key.py --list-teams              # List all teams
  python generate_api_key.py --team "Dev Team" --save  # Generate and save to file
        """
    )
    
    parser.add_argument('--team', '-t', type=str, help='Team name to generate API key for (overrides .env)')
    parser.add_argument('--list-teams', '-l', action='store_true', help='List all teams and exit')
    parser.add_argument('--save', '-s', action='store_true', help='Save API key to file')
    parser.add_argument('--yes', '-y', action='store_true', help='Auto-confirm without prompts')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        print("🚀 Dependency-Track API Key Generator")
        print("=" * 50)
        
        # Load environment variables
        env_vars = load_environment()
        
        # Initialize the client
        print("🔗 Connecting to Dependency-Track...")
        client = DependencyTrackClient(
            base_url=env_vars['DEPENDENCY_TRACK_URL'],
            api_key=env_vars['DEPENDENCY_TRACK_API_KEY']
        )
        
        # Test connection
        teams = client.get_teams()
        print(f"✅ Connected! Found {len(teams)} teams.")
        
        # Handle list-teams command
        if args.list_teams:
            display_teams(teams)
            sys.exit(0)
        
        # Determine team name (from --team or .env)
        team_name = args.team if args.team else env_vars.get('TEAM_NAME')
        if not team_name:
            print("Error: No team name provided. Please set TEAM_NAME in .env or use --team.")
            sys.exit(1)
        
        # Generate API key for the specified team
        success = generate_api_key_for_team(
            client, team_name, args.save, args.yes
        )
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