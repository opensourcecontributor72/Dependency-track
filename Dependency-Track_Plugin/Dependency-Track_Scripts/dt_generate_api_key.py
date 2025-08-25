# Dependency-Track_Plugin/Dependency-Track_Scripts/dt_generate_api_key.py
#!/usr/bin/env python3
"""
OWASP Dependency-Track API Key Generator

Generates an API token for a specific team.
"""

import os
import sys
import argparse
import logging
import requests
from typing import List, Optional
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

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
            'User-Agent': 'DependencyTrack-APIKeyGenerator/1.0'
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
    
    def get_teams(self) -> List[dict]:
        self.logger.info("Retrieving teams from Dependency-Track")
        response = self._make_request('GET', '/v1/team')
        return response.json()
    
    def find_team_by_name(self, team_name: str) -> Optional[dict]:
        teams = self.get_teams()
        for team in teams:
            if team.get('name', '').lower() == team_name.lower():
                return team
        return None
    
    def generate_api_key(self, team_uuid: str) -> str:
        self.logger.info(f"Generating API key for team: {team_uuid}")
        response = self._make_request('PUT', f'/v1/team/{team_uuid}/key')
        if response.text:
            api_key_data = response.json()
            api_key = api_key_data.get('key', f"DT-Token-{team_uuid}-{datetime.now().timestamp()}")
            self.logger.info("API key generated successfully")
            return api_key
        raise DependencyTrackAPIError("No API key returned in response")

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('logs/dependency_track_client.log', encoding='utf-8')
        ],
        force=True  # Ensures previous handlers (e.g., StreamHandler) are cleared
    )

def load_environment() -> dict:
    load_dotenv()
    required_vars = {
        'DEPENDENCY_TRACK_URL': os.getenv('DEPENDENCY_TRACK_URL'),
        'DEPENDENCY_TRACK_API_KEY': os.getenv('DEPENDENCY_TRACK_API_KEY')
    }
    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")
    return required_vars

def save_response_to_json(team_name: str, api_key: str) -> None:
    """Save the API key generation response to a JSON file."""
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    results_dir = os.path.join(project_root, "results")
    
    try:
        os.makedirs(results_dir, exist_ok=True)
    except PermissionError:
        print(f"Error: No permission to create {results_dir}. Response not saved.", file=sys.stdout)
        return
    
    json_filename = os.path.join(results_dir, "dependency_track_api_response.json")
    
    response_data = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
            "script_name": "dt_generate_api_key.py",
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
    except PermissionError:
        print(f"Error: No permission to write to {json_filename}. Response not saved.", file=sys.stdout)

def generate_api_key_for_team(client: DependencyTrackClient, team_name: str, auto_confirm: bool = False) -> bool:
    """Generate API key for a specific team."""
    logger = logging.getLogger(__name__)
    
    # Find the team
    team = client.find_team_by_name(team_name)
    if not team:
        print(json.dumps({"error": f"Team '{team_name}' not found."}), file=sys.stdout)
        return False
    
    logger.info(f"Found team: {team['name']}")
    logger.info(f"   UUID: {team['uuid']}")
    logger.info(f"   Permissions: {len(team.get('permissions', []))}")
    
    if not auto_confirm:
        print(f"\nWARNING: This will generate a new API key for team '{team['name']}'", file=sys.stdout)
        print("   Any existing API key for this team will be invalidated!", file=sys.stdout)
        print(f"   Team UUID: {team['uuid']}", file=sys.stdout)
        response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Operation cancelled.", file=sys.stdout)
            return False
    
    try:
        logger.info("Generating API key...")
        new_api_key = client.generate_api_key(team['uuid'])
        
        logger.info(f"SUCCESS! New API key generated for team '{team['name']}':")
        result = {"api_key": new_api_key}
        print(json.dumps(result), end='', file=sys.stdout)  # Output only JSON, no extra newline
        
        save_response_to_json(team['name'], new_api_key)
        return True
        
    except DependencyTrackAPIError as e:
        logger.error(f"Failed to generate API key: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stdout)
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate API token for a team")
    parser.add_argument('--team', '-t', type=str, required=True, help='Team name to generate token for')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--yes', '-y', action='store_true', help='Auto-confirm without prompts')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        env_vars = load_environment()
        client = DependencyTrackClient(
            base_url=env_vars['DEPENDENCY_TRACK_URL'],
            api_key=env_vars['DEPENDENCY_TRACK_API_KEY']
        )
        
        success = generate_api_key_for_team(client, args.team, args.yes)
        sys.exit(0 if success else 1)
        
    except DependencyTrackAPIError as e:
        logger.error(f"Dependency-Track API error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()