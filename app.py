from flask import Flask, request, jsonify, session
from flask_cors import CORS
import requests, base64, random, string, os

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", ''.join(random.choices(string.ascii_letters + string.digits, k=32)))

# GitHub token stored as Render environment variable
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

OWNER = "snowystudios"
REPO = "saasd"
BRANCH = "main"

# Admin credentials (store in Render env variables)
ADMIN_USER = os.environ.get("ADMIN_USER")
ADMIN_PASS = os.environ.get("ADMIN_PASS")
OWNER_USER = os.environ.get("OWNER_USER")  # Optional owner role

# Config (can be updated by admin)
config = {
    "max_gens_per_user": 20,
    "file_content_mode": "user_content",  # "permanent_content" or "user_content"
    "permanent_content": "Snowy Test"
}

def random_name(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

# Simple login_required decorator
def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return wrapper

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if (username == ADMIN_USER and password == ADMIN_PASS) or (username == OWNER_USER and password == ADMIN_PASS):
        session["admin_logged_in"] = True
        session["admin_username"] = username
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route("/admin/logout", methods=["POST"])
@login_required
def admin_logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/admin/config", methods=["GET", "POST"])
@login_required
def admin_config():
    if request.method == "POST":
        data = request.json
        max_gens = int(data.get("max_gens_per_user", config["max_gens_per_user"]))
        mode = data.get("file_content_mode", config["file_content_mode"])
        permanent_content = data.get("permanent_content", config["permanent_content"])

        config.update({
            "max_gens_per_user": max_gens,
            "file_content_mode": mode,
            "permanent_content": permanent_content
        })
        return jsonify({"success": True, "config": config})
    else:
        return jsonify(config)

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.json
        file_count = int(data.get("fileCount", 1))

        # Determine content mode
        if config["file_content_mode"] == "permanent_content":
            file_content = config["permanent_content"]
        else:
            file_content = data.get("fileContent", "test")

        # Prevent abuse
        if file_count > config["max_gens_per_user"]:
            return jsonify({"error": f"Too many files requested. Max allowed: {config['max_gens_per_user']}"}), 400

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
                links.append(f"loadstring(game:HttpGet('{raw}'))()")
            else:
                return jsonify({"error": r.text}), 400

        return jsonify({"links": links})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "API running"

if __name__ == "__main__":
    app.run()
