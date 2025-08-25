import os
import json
import requests
from requests.auth import HTTPBasicAuth

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get creds from environment variables
url = "https://dependency-track.tools.aa.st/api/v1/project"
username = os.getenv("DT_USERNAME")
password = os.getenv("DT_PASSWORD")

# Make API request
response = requests.get(url, auth=HTTPBasicAuth(username, password))

if response.status_code == 200:
    print("Valid credentials")
    data = response.json()
    print("Response:", data)

    # Save response to JSON file
    with open("dtrack_response.json", "w") as f:
        json.dump(data, f, indent=4)
    print("Response saved to dtrack_response.json")

elif response.status_code == 401:
    print("Invalid credentials")
else:
    print(f"Unexpected response: {response.status_code}", response.text)
