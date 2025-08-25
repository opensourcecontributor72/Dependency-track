# Dependency-Track_Plugin/run_script.py
#!/usr/bin/env python3
"""
Runner script to launch the Dependency-Track Plugin Flask application.

This script sets up the environment, creates necessary directories, and starts the Flask server
defined in app.py with a single command.

Usage:
    python run_script.py
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_environment():
    """Set up directories and environment for the application."""
    # Create logs and results directories if they don't exist
    for directory in ['logs', 'results']:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        except PermissionError:
            print(f"Warning: No permission to create {directory}. Using current directory.")
    
    # Verify required environment variables
    required_vars = ['DEPENDENCY_TRACK_URL', 'DEPENDENCY_TRACK_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file with:")
        for var in missing_vars:
            print(f"   {var}=your_value")
        sys.exit(1)

def run_application():
    """Run the Flask application defined in app.py."""
    try:
        # Use the Python interpreter from the virtual environment
        venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dtenv', 'Scripts', 'python.exe')
        cmd = [venv_python, 'app.py']
        print("Starting Dependency-Track Plugin application...")
        process = subprocess.run(cmd, check=True, text=True, env=os.environ.copy())
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to start application - {e.stderr}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")
        sys.exit(0)

if __name__ == "__main__":
    setup_environment()
    run_application()