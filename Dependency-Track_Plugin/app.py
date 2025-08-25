# Dependency-Track_Plugin/app.py
import os
import subprocess
import json
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, session
from flask_session import Session
from dotenv import load_dotenv
import logging
from datetime import datetime

load_dotenv()
app = Flask(__name__, static_folder='client', template_folder='client')

# Configure Flask-Session to use filesystem (or another store like Redis)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Replace with a secure key or set in .env
Session(app)

# Set up main logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('logs/dependency_track_client.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Set up user activity logger
user_activity_logger = logging.getLogger('user_activity')
user_activity_logger.setLevel(logging.INFO)
if not user_activity_logger.handlers:
    user_activity_handler = logging.FileHandler('logs/user_activity_tracking.log', encoding='utf-8')
    user_activity_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    user_activity_logger.addHandler(user_activity_handler)

def run_script(script_name, args=[]):
    env = os.environ.copy()
    cmd = ['python', os.path.join('Dependency-Track_Scripts', script_name)] + args
    logger.debug(f"Executing command: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Script failed: {result.stderr}")
        raise Exception(result.stderr)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.warning(f"Non-JSON output from {script_name}: {result.stdout} (Error: {e})")
        return {"output": result.stdout.strip()}  # Fallback, but should not be needed

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('get_token_page'))
    return render_template('components/auth.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required"}), 400

    try:
        output = run_script('dt_user_login.py', ['--user', username,'--password', password,'--verbose'])
        data = output
        if 'error' in data:
            return jsonify({"success": False, "message": data['error']}), 404

        session['logged_in'] = True
        session['username'] = username
        user_activity_logger.info(f"username: {username}, email: {data.get('email')}")
        logger.info(f"Successfully verified user {username}")
        return jsonify({
            "success": True,
            "message": f"User '{username}' logged in",
            "username": data.get('username'),
            "email": data.get('email'),
            "fullname": data.get('fullname')
        })
    except Exception as e:
        logger.error(f"Error checking user: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/getToken')
def get_token_page():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    username = session.get('username', '')
    return render_template('getToken.html', username=username)

@app.route('/api/fetch_teams', methods=['GET'])
def fetch_teams():
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username is required"}), 400
    logger.info(f"Fetching teams for username: {username}")
    try:
        output = run_script('dt_fetch_teams_for_user.py', ['--user', username, '--verbose'])
        data = output
        if 'error' in data:
            return jsonify(data), 404

        user_activity_logger.info(f"username: {username}, email: {data.get('email')}")
        logger.info(f"Successfully fetched {len(data.get('teams', []))} teams")
        return jsonify({"teams": data.get('teams', [])})
    except Exception as e:
        logger.error(f"Error fetching teams: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_token', methods=['GET'])
def generate_token():
    team = request.args.get('team')
    username = request.args.get('username')
    email = request.args.get('email', 'not_provided')
    if not team:
        return jsonify({"error": "Team is required"}), 400
    logger.info(f"Generating API token for team: {team}")
    try:
        output = run_script('dt_generate_api_key.py', ['--team', team, '--yes', '--verbose'])
        data = output
        if 'error' in data:
            return jsonify(data), 404
        api_key = data.get('api_key')
        if api_key is None:
            logger.warning(f"No 'api_key' found in response: {data}")
            return jsonify({"error": "Token generation failed"}), 500
        
        user_activity_logger.info(f"username: {username}, email: {email}")
        
        logger.info(f"Successfully generated API token for team {team}")
        return jsonify({"token": api_key})
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/check_user', methods=['GET'])
def check_user():
    username = request.args.get('username')
    if not username:
        return jsonify({"success": False, "message": "Username is required"}), 400
    logger.info(f"Checking user: {username}")
    try:
        output = run_script('dt_user_login.py', ['--user', username, '--verbose'])
        data = output
        if 'error' in data:
            return jsonify({"success": False, "message": data['error']}), 404

        user_activity_logger.info(f"username: {username}, email: {data.get('email')}")
        logger.info(f"Successfully verified user {username}")
        return jsonify({
            "success": True,
            "message": f"User '{username}' found",
            "username": data.get('username'),
            "email": data.get('email'),
            "fullname": data.get('fullname')
        })
    except Exception as e:
        logger.error(f"Error checking user: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('client', path)

if __name__ == "__main__":
    if not os.path.exists('logs'):
        os.makedirs('logs')
    if not os.path.exists('results'):
        os.makedirs('results')
    port = int(os.getenv('PORT', 5000))  # Default to 5000 if PORT is not set in .env
    app.run(host='0.0.0.0', port=port, debug=True)