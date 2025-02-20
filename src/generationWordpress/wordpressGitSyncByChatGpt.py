import difflib
import json
import os
from datetime import datetime

import git
import requests
from flask import Flask, request, jsonify, redirect, url_for, session
from flask_httpauth import HTTPBasicAuth
from flask_oauthlib.client import OAuth
from flask_session import Session
import configPrivee2 as configPrivee

# Configuration
WORDPRESS_API_URL = "https://grains-de-culture.fr/wp-json/wp/v2/pages"
WORDPRESS_USERNAME = configPrivee.WORDPRESS_O2_API2USERNAME
WORDPRESS_PASSWORD = configPrivee.WORDPRESS_O2_PASSWORD_APP
GIT_REPO_PATH = "D:\wamp64\www\givingsense.eu\datamusee\scrutart"
GIT_PAGE_PATH = "wpPages/testsync/page.json"  # Updated to handle multiple components
LOG_FILE = "data/scrutart_sync_log.txt"
ALERT_FILE = "data/scrutart_alert_log.txt"
ALLOWED_USERS_FILE = "data/allowed_users.json"

# WordPress authentication
wp_auth = (WORDPRESS_USERNAME, WORDPRESS_PASSWORD)

# Flask and authentication setup
app = Flask(__name__)
app.secret_key = 'random_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
auth = HTTPBasicAuth()
oauth = OAuth(app)

# User credentials (store securely in production)
users = {
    "admin": configPrivee.WORDPRESS_O2_PASSWORD_APP
}

# Google OAuth configuration
google = oauth.remote_app(
    'google',
    consumer_key='GOOGLE_CLIENT_ID',
    consumer_secret='GOOGLE_CLIENT_SECRET',
    request_token_params={
        'scope': 'email profile'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth'
)


# Initialize allowed users
def initialize_allowed_users():
    try:
        with open(ALLOWED_USERS_FILE, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


allowed_users = initialize_allowed_users()


@auth.get_password
def get_pw(username):
    if username in users:
        return users.get(username)
    return None


@app.route('/login')
def login():
    return google.authorize(callback=url_for('authorized', _external=True))


@app.route('/logout')
def logout():
    session.pop('google_token', None)
    return jsonify({"status": "Logged out"})


@app.route('/login/authorized')
def authorized():
    response = google.authorized_response()
    if response is None or response.get('access_token') is None:
        return jsonify({"error": "Access denied: reason={} error={}".format(
            request.args.get('error_reason', 'Unknown'),
            request.args.get('error_description', 'Unknown')
        )})

    session['google_token'] = (response['access_token'], '')
    user_info = google.get('userinfo')

    if user_info.data['email'] not in allowed_users:
        return jsonify({"error": "Unauthorized user"}), 403

    return jsonify({"status": "Login successful", "user": user_info.data})


@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')


def get_wordpress_page(page_id):
    """Fetch the current version of a page from WordPress."""
    response = requests.get(f"{WORDPRESS_API_URL}/{page_id}", auth=wp_auth)
    response.raise_for_status()
    data = response.json()
    return {
        'title': data['title']['rendered'],
        'content': data['content']['rendered'],
        'featured_media': data.get('featured_media', None)
    }


def get_git_page_content():
    """Read the current version of the page from the Git repository."""
    with open(os.path.join(GIT_REPO_PATH, GIT_PAGE_PATH), 'r') as file:
        return json.load(file)


def update_wordpress_page(page_id, title, content, featured_media):
    """Update the WordPress page with new content."""
    data = {
        'title': title,
        'content': content,
        'featured_media': featured_media
    }
    response = requests.post(f"{WORDPRESS_API_URL}/{page_id}", auth=wp_auth, json=data)
    response.raise_for_status()


def update_git_page(content):
    """Update the page in the Git repository."""
    with open(os.path.join(GIT_REPO_PATH, GIT_PAGE_PATH), 'w') as file:
        json.dump(content, file, indent=4)

    repo = git.Repo(GIT_REPO_PATH)
    repo.git.add(GIT_PAGE_PATH)
    repo.index.commit("Update page content")
    repo.git.push()


def log_message(file_path, message):
    """Log a message to a specified file."""
    with open(file_path, 'a') as file:
        file.write(f"{datetime.now()}: {message}\n")


def generate_new_version():
    """Placeholder function for generating a new version of the page."""
    return {
        'title': "New Title",
        'content': "New page content",
        'featured_media': None
    }


def apply_content_differences(old_content, new_content):
    """Apply differences by detecting added or removed blocks."""
    diff = list(difflib.ndiff(old_content.splitlines(), new_content.splitlines()))
    result = []

    for line in diff:
        if line.startswith('- '):
            # Line removed in the new content
            continue
        elif line.startswith('+ '):
            # Line added in the new content
            result.append(line[2:])
        elif not line.startswith('? '):
            # Unchanged line
            result.append(line[2:])

    return '\n'.join(result)


def synchronize_page(page_id):
    try:
        wp_page = get_wordpress_page(page_id)
        git_page = get_git_page_content()
        new_version = generate_new_version()

        differences = []

        for key in ['title', 'content', 'featured_media']:
            if wp_page[key] != git_page.get(key, None):
                differences.append(key)

        if not differences:
            update_git_page(new_version)
            update_wordpress_page(page_id, new_version['title'], new_version['content'], new_version['featured_media'])
            log_message(LOG_FILE, "Pages were identical; new version applied.")
        else:
            diff_details = {key: {
                'wordpress': wp_page[key],
                'git': git_page.get(key, None)
            } for key in differences}

            log_message(LOG_FILE, f"Differences detected:\n{diff_details}")

            try:
                combined_version = {
                    'title': new_version['title'] if 'title' in differences else wp_page['title'],
                    'content': new_version['content'] if 'content' in differences else apply_content_differences(
                        wp_page['content'], git_page.get('content', '')),
                    'featured_media': new_version['featured_media'] if 'featured_media' in differences else wp_page[
                        'featured_media']
                }

                update_git_page(combined_version)
                update_wordpress_page(page_id, combined_version['title'], combined_version['content'],
                                      combined_version['featured_media'])
                log_message(LOG_FILE, "Differences integrated successfully.")
            except Exception as e:
                log_message(ALERT_FILE, f"Failed to integrate differences: {e}")
    except Exception as e:
        log_message(ALERT_FILE, f"Error during synchronization: {e}")


@app.route('/synchronize', methods=['POST'])
@auth.login_required
def synchronize():
    data = request.get_json()
    page_id = data.get('page_id')
    if not page_id:
        return jsonify({"error": "page_id is required"}), 400

    try:
        synchronize_page(page_id)
        return jsonify({"status": "Synchronization successful"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
    # app.run(debug=True)
