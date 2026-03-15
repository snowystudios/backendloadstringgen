from flask import Flask, request, jsonify, session
from flask_cors import CORS
import requests
import base64
import random
import string
import os
from functools import wraps

app = Flask(__name__)

# Security settings for cross-site sessions
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True

# Secret key for session signing
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

# Enable CORS with credentials support
CORS(app, supports_credentials=True)

# GitHub settings
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER = "snowystudios"
REPO = "saasd"
BRANCH = "main"

# Admin credentials
ADMIN_USER = os.environ.get("ADMIN_USER")
ADMIN_PASS = os.environ.get("ADMIN_PASS")

# Generator config controlled by admin
config = {
    "max_gens_per_user": 20,
    "file_content_mode": "user_content",
    "permanent_content": "Snowy Test"
}

def random_name(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return wrapper


@app.route("/")
def home():
    return "Snowy Lua Generator API running"


# ----------------------
# ADMIN LOGIN
# ----------------------

@app.route("/admin/login", methods=["POST"])
def admin_login():
    try:
        data = request.json

        if not data:
            return jsonify({"error": "Missing JSON"}), 400

        username = data.get("username")
        password = data.get("password")

        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin_logged_in"] = True
            return jsonify({"success": True})

        return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/logout", methods=["POST"])
@login_required
def admin_logout():
    session.clear()
    return jsonify({"success": True})


# ----------------------
# ADMIN CONFIG
# ----------------------

@app.route("/admin/config", methods=["GET", "POST"])
@login_required
def admin_config():

    if request.method == "GET":
        return jsonify(config)

    try:
        data = request.json

        max_gens = int(data.get("max_gens_per_user", config["max_gens_per_user"]))
        mode = data.get("file_content_mode", config["file_content_mode"])
        permanent_content = data.get("permanent_content", config["permanent_content"])

        config["max_gens_per_user"] = max_gens
        config["file_content_mode"] = mode
        config["permanent_content"] = permanent_content

        return jsonify({"success": True, "config": config})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------
# GENERATOR
# ----------------------

@app.route("/generate", methods=["POST"])
def generate():

    try:
        data = request.json

        if not data:
            return jsonify({"error": "Missing JSON"}), 400

        file_count = int(data.get("fileCount", 1))

        if file_count > config["max_gens_per_user"]:
            return jsonify({
                "error": f"Too many files requested. Max allowed: {config['max_gens_per_user']}"
            }), 400

        # Decide content mode
        if config["file_content_mode"] == "permanent_content":
            file_content = config["permanent_content"]
        else:
            file_content = data.get("fileContent", "test")

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }

        links = []

        for _ in range(file_count):

            filename = random_name() + ".lua"
            encoded = base64.b64encode(file_content.encode()).decode()

            url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{filename}"

            payload = {
                "message": f"create {filename}",
                "content": encoded,
                "branch": BRANCH
            }

            r = requests.put(url, headers=headers, json=payload)

            if r.status_code in [200, 201]:

                raw = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{filename}"

                links.append(
                    f"loadstring(game:HttpGet('{raw}'))()"
                )

            else:
                return jsonify({"error": r.text}), 400

        return jsonify({"links": links})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()
