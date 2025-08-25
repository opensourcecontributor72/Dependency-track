import requests
import json
from datetime import datetime

class DTrackTeamAPIManager:
    def __init__(self, base_url, jwt_token):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
    
    def get_teams(self):
        """Get all teams the user has access to"""
        url = f"{self.base_url}/api/v1/team"
        
        try:
            print("🔍 Fetching teams...")
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                teams = response.json()
                print(f"Found {len(teams)} teams")
                
                print("\n📋 Available Teams:")
                for i, team in enumerate(teams, 1):
                    print(f"{i}. {team['name']} (UUID: {team['uuid']})")
                return teams
            else:
                print(f"Failed to fetch teams: {response.status_code}")
                print(f"Response: {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching teams: {e}")
            return []
    
    def get_team_by_name(self, team_name):
        """Find team by name"""
        teams = self.get_teams()
        for team in teams:
            if team['name'].lower() == team_name.lower():
                return team
        return None
    
    def get_team_api_keys(self, team_uuid):
        """Get existing API keys for a team - Note: This endpoint may not be available in all DTrack versions"""
        # Try multiple possible endpoints
        possible_endpoints = [
            f"{self.base_url}/api/v1/team/{team_uuid}/key",
            f"{self.base_url}/api/v1/team/{team_uuid}/keys",
            f"{self.base_url}/api/v1/team/{team_uuid}"
        ]
        
        for endpoint in possible_endpoints:
            try:
                print(f"🔍 Trying endpoint: {endpoint}")
                response = requests.get(endpoint, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    print(data)
                    
                    # Check if this is team data with keys embedded
                    if isinstance(data, dict) and 'apiKeys' in data:
                        keys = data['apiKeys']
                    elif isinstance(data, list):
                        keys = data
                    else:
                        keys = []
                    
                    print(f"Found {len(keys)} API keys using {endpoint}")
                    
                    if keys:
                        print("\n🔑 Existing API Keys:")
                        for i, key in enumerate(keys, 1):
                            print(f"{i}. Key ID: {key.get('uuid', 'N/A')}")
                            print(f"Created: {key.get('created', 'N/A')}")
                            print(f"Comment: {key.get('comment', 'N/A')}")
                    
                    return keys
                    
                elif response.status_code == 404:
                    print(f"   Endpoint not found: {endpoint}")
                    continue
                elif response.status_code == 405:
                    print(f"   Method not allowed: {endpoint}")
                    continue
                else:
                    print(f"   Error {response.status_code}: {endpoint}")
                    continue
                    
            except requests.exceptions.RequestException as e:
                print(f"   Request error for {endpoint}: {e}")
                continue
        
        print("⚠️  Unable to retrieve API keys - this feature may not be available")
        print("   You can still create new API keys, but existing ones won't be listed")
        print("   This is common in DTrack as API keys are hashed and hidden after creation")
        return []
    
    def create_team_api_key(self, team_uuid, comment="Generated via API"):
        """Create a new API key for a team"""
        url = f"{self.base_url}/api/v1/team/{team_uuid}/key"
        
        payload = {
            "comment": comment
        }
        
        try:
            print(f"🔐 Creating API key for team {team_uuid}...")
            response = requests.put(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 201:
                key_data = response.json()
                print("✅ API key created successfully!")
                
                # Save the key data immediately (it won't be visible later)
                key_info = {
                    "timestamp": datetime.now().isoformat(),
                    "team_uuid": team_uuid,
                    "comment": comment,
                    "api_key_data": key_data,
                    "warning": "This API key will not be visible again after this response"
                }
                
                filename = f"team_api_key_{team_uuid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump(key_info, f, indent=2)
                
                print(f"💾 API key saved to: {filename}")
                print(f"🔑 API Key: {key_data.get('key', 'Not found in response')}")
                print("⚠️  IMPORTANT: Save this key now - it won't be visible again!")
                
                return key_data
                
            elif response.status_code == 403:
                print("Access denied - insufficient permissions to create API key")
                print("   You need PORTFOLIO_MANAGEMENT permission for this team")
                return None
            else:
                print(f"Failed to create API key: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error creating API key: {e}")
            return None
    
    def delete_team_api_key(self, team_uuid, key_uuid):
        """Delete an API key"""
        url = f"{self.base_url}/api/v1/team/{team_uuid}/key/{key_uuid}"
        
        try:
            print(f"Deleting API key {key_uuid} for team {team_uuid}...")
            response = requests.delete(url, headers=self.headers, timeout=30)
            
            if response.status_code == 204:
                print("API key deleted successfully!")
                return True
            else:
                print(f"Failed to delete API key: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Error deleting API key: {e}")
            return False

def main():
    print("DTrack Team API Key Manager")
    print("=" * 50)
    
    # Load JWT token from file or enter manually
    jwt_token = None
    
    try:
        with open('token.txt', 'r') as f:
            jwt_token = f.read().strip()
        print("JWT token loaded from token.txt")
    except FileNotFoundError:
        jwt_token = input("Enter your JWT token: ").strip()
    
    if not jwt_token:
        print("No JWT token provided")
        return
    
    base_url = "https://dependency-track.tools.aa.st"
    manager = DTrackTeamAPIManager(base_url, jwt_token)
    
    while True:
        print("\n🎯 Options:")
        print("1. List teams")
        print("2. Create API key for team")
        print("3. List API keys for team")
        print("4. Delete API key")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            teams = manager.get_teams()
            
        elif choice == "2":
            teams = manager.get_teams()
            if not teams:
                continue
                
            try:
                team_choice = int(input(f"\nSelect team (1-{len(teams)}): ")) - 1
                if 0 <= team_choice < len(teams):
                    selected_team = teams[team_choice]
                    comment = input("Enter comment for API key (optional): ").strip()
                    if not comment:
                        comment = f"Generated for {selected_team['name']} on {datetime.now().strftime('%Y-%m-%d')}"
                    
                    manager.create_team_api_key(selected_team['uuid'], comment)
                else:
                    print("Invalid team selection")
            except ValueError:
                print("Invalid input")
                
        elif choice == "3":
            teams = manager.get_teams()
            if not teams:
                continue
                
            try:
                team_choice = int(input(f"\nSelect team (1-{len(teams)}): ")) - 1
                if 0 <= team_choice < len(teams):
                    selected_team = teams[team_choice]
                    manager.get_team_api_keys(selected_team['uuid'])
                else:
                    print("Invalid team selection")
            except ValueError:
                print("Invalid input")
                
        elif choice == "4":
            teams = manager.get_teams()
            if not teams:
                continue
                
            try:
                team_choice = int(input(f"\nSelect team (1-{len(teams)}): ")) - 1
                if 0 <= team_choice < len(teams):
                    selected_team = teams[team_choice]
                    keys = manager.get_team_api_keys(selected_team['uuid'])
                    
                    if keys:
                        key_choice = int(input(f"\nSelect API key to delete (1-{len(keys)}): ")) - 1
                        if 0 <= key_choice < len(keys):
                            selected_key = keys[key_choice]
                            confirm = input(f"Are you sure you want to delete key {selected_key.get('uuid')}? (y/N): ")
                            if confirm.lower() == 'y':
                                manager.delete_team_api_key(selected_team['uuid'], selected_key['uuid'])
                        else:
                            print("Invalid key selection")
                else:
                    print("Invalid team selection")
            except ValueError:
                print("Invalid input")
                
        elif choice == "5":
            print("👋 Goodbye!")
            break
            
        else:
            print("Invalid option")

if __name__ == "__main__":
    main()