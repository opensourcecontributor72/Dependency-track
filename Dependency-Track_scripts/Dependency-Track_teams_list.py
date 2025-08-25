#!/usr/bin/env python3
"""
OWASP Dependency-Track API Client

A professional Python script for managing teams and API keys in OWASP Dependency-Track.
Supports listing teams and generating API keys with proper error handling and logging.

Requirements:
    pip install requests python-dotenv

Environment Variables (.env file):
    DEPENDENCY_TRACK_URL=https://your-dependency-track-instance.com
    DEPENDENCY_TRACK_API_KEY=your-existing-api-key
"""

import os
import sys
import logging
import requests
import json
import platform
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Team:
    """Data class representing a Dependency-Track team."""
    uuid: str
    name: str
    permissions: List[Any]  # Changed to Any to handle dict or str


class DependencyTrackAPIError(Exception):
    """Custom exception for Dependency-Track API errors."""
    pass


class DependencyTrackClient:
    """
    Professional client for OWASP Dependency-Track API operations.
    
    Handles authentication, error handling, and provides methods for
    team management and API key generation.
    """
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        """
        Initialize the Dependency-Track API client.
        
        Args:
            base_url: Base URL of the Dependency-Track instance
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'DependencyTrack-Python-Client/1.0'
        })
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make an HTTP request to the Dependency-Track API.
        
        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests
            
        Returns:
            requests.Response: The HTTP response
            
        Raises:
            DependencyTrackAPIError: If the request fails
        """
        url = f"{self.base_url}/api{endpoint}"
        
        try:
            self.logger.debug(f"Making {method} request to {url}")
            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            
            # Log response details
            self.logger.debug(f"Response status: {response.status_code}")
            
            # Raise for HTTP errors
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
        """
        Retrieve all teams from Dependency-Track.
        
        Returns:
            List[Team]: List of Team objects
            
        Raises:
            DependencyTrackAPIError: If the request fails
        """
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
    
    def generate_api_key(self, team_uuid: str) -> str:
        """
        Generate a new API key for the specified team.
        
        Args:
            team_uuid: UUID of the team
            
        Returns:
            str: The newly generated API key
            
        Raises:
            DependencyTrackAPIError: If the request fails
        """
        self.logger.info(f"Generating API key for team: {team_uuid}")
        
        response = self._make_request('PUT', f'/v1/team/{team_uuid}/key')
        
        # The response should contain the new API key
        if response.text:
            api_key = response.text.strip('"')  # Remove quotes if present
            self.logger.info("API key generated successfully")
            return api_key
        else:
            raise DependencyTrackAPIError("No API key returned in response")
    
    def find_team_by_name(self, team_name: str) -> Optional[Team]:
        """
        Find a team by its name.
        
        Args:
            team_name: Name of the team to find
            
        Returns:
            Optional[Team]: Team object if found, None otherwise
        """
        teams = self.get_teams()
        for team in teams:
            if team.name.lower() == team_name.lower():
                return team
        return None


def setup_logging(level: str = 'INFO') -> logging.Logger:
    """
    Set up logging configuration with both file and console output.
    Creates log file in the root project directory's logs folder.
    
    Args:
        level: Logging level (default: 'INFO')
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Get the root project directory (parent of the script directory)
    script_dir = os.path.dirname(__file__)
    project_root = os.path.dirname(script_dir)
    logs_dir = os.path.join(project_root, "logs")
    
    # Create logs directory
    try:
        os.makedirs(logs_dir, exist_ok=True)
    except PermissionError:
        print(f"Error: No permission to create {logs_dir}. Logging to console only.")
        logs_dir = os.path.join(script_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
    
    # Use fixed log filename
    log_filename = os.path.join(logs_dir, "dependency_track_client.log")
    
    # Configure logger
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler
    try:
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(file_handler)
    except PermissionError:
        print(f"Error: No permission to write to {log_filename}. Logging to console only.")
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(console_handler)
    
    return logger


def load_environment() -> Dict[str, str]:
    """
    Load environment variables from .env file.
    
    Returns:
        Dict[str, str]: Dictionary containing required environment variables
        
    Raises:
        SystemExit: If required environment variables are missing
    """
    # Load .env file
    load_dotenv()
    
    # Required environment variables
    required_vars = {
        'DEPENDENCY_TRACK_URL': os.getenv('DEPENDENCY_TRACK_URL'),
        'DEPENDENCY_TRACK_API_KEY': os.getenv('DEPENDENCY_TRACK_API_KEY')
    }
    
    # Check for missing variables
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease create a .env file with the following variables:")
        print("DEPENDENCY_TRACK_URL=https://your-dependency-track-instance.com")
        print("DEPENDENCY_TRACK_API_KEY=your-existing-api-key")
        sys.exit(1)
    
    return required_vars


def display_teams(teams: List[Team]) -> List[str]:
    """
    Display teams in a formatted table and return the output as a list of strings.
    
    Args:
        teams: List of Team objects
        
    Returns:
        List[str]: Lines of the formatted table
    """
    output = []
    if not teams:
        output.append("No teams found.")
        print("No teams found.")
        return output
    
    output.append("\n" + "="*80)
    output.append("DEPENDENCY-TRACK TEAMS")
    output.append("="*80)
    output.append(f"{'Name':<30} {'UUID':<38} {'Permissions'}")
    output.append("-"*80)
    
    for team in teams:
        # Handle permissions as list of dicts or strings
        permissions = team.permissions
        if permissions and isinstance(permissions[0], dict):
            # Extract 'name' from dicts (e.g., [{'name': 'ADMIN'}, ...])
            permission_names = [perm.get('name', 'Unknown') for perm in permissions[:3]]
        else:
            # Assume permissions are strings
            permission_names = permissions[:3]
        
        permissions_str = ', '.join(permission_names)
        if len(permissions) > 3:
            permissions_str += f" (+{len(permissions)-3} more)"
        
        output.append(f"{team.name:<30} {team.uuid:<38} {permissions_str}")
    
    output.append("-"*80)
    output.append(f"Total teams: {len(teams)}")
    output.append("")
    
    # Print to console
    for line in output:
        print(line)
    
    return output


def save_response_to_json(teams: List[Team], log_messages: List[str]) -> None:
    """
    Save the script's response to a JSON file in the root project directory's results folder.
    
    Args:
        teams: List of Team objects
        log_messages: List of captured log messages
    """
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
    
    # Prepare teams data for JSON, handling permissions as dicts or strings
    teams_data = []
    for team in teams:
        permissions = team.permissions
        if permissions and isinstance(permissions[0], dict):
            permission_names = [perm.get('name', 'Unknown') for perm in permissions]
        else:
            permission_names = permissions
        teams_data.append({
            "name": team.name,
            "uuid": team.uuid,
            "permissions": permission_names
        })
    
    response_data = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
            "script_name": "dependency_track_client.py",
            "description": "OWASP Dependency-Track API Client response",
            "version": "1.0",
            "timezone": "CEST"
        },
        "console_output": display_teams(teams),
        "log_output": log_messages,
        "teams_data": teams_data
    }
    
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=4)
        print(f"Response saved to {json_filename}")
    except PermissionError:
        print(f"Error: No permission to write to {json_filename}. Response not saved.")


def main():
    """Main function to demonstrate the API client usage."""
    # Setup logging with file and console output, and capture logs
    log_messages = []
    class ListHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(self.format(record))
    
    logger = setup_logging()
    list_handler = ListHandler()
    list_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(list_handler)
    
    try:
        # Load environment variables
        env_vars = load_environment()
        
        # Initialize the client
        client = DependencyTrackClient(
            base_url=env_vars['DEPENDENCY_TRACK_URL'],
            api_key=env_vars['DEPENDENCY_TRACK_API_KEY']
        )
        
        # Test connection by retrieving teams
        logger.info("Testing connection to Dependency-Track...")
        teams = client.get_teams()
        
        # Save response to JSON
        save_response_to_json(teams, log_messages)
        
        logger.info("Script completed successfully")
        
    except DependencyTrackAPIError as e:
        logger.error(f"Dependency-Track API error: {e}")
        error_output = [f"Error: {e}"]
        save_response_to_json([], log_messages + [f"Error: {e}"])
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        save_response_to_json([], log_messages + ["Script interrupted by user"])
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        save_response_to_json([], log_messages + [f"Unexpected error: {e}"])
        sys.exit(1)


if __name__ == "__main__":
    main()