from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import random
import string
import os

app = Flask(__name__)
CORS(app)  # Allow your frontend to call this API

# GitHub token stored as Render environment variable
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

OWNER = "snowystudios"
REPO = "saasd"
BRANCH = "main"

def random_name(length=10):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

@app.route("/")
def home():
    return "API running"

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.json
        file_count = int(data.get("fileCount", 1))
        file_content = data.get("fileContent", "test")

        # Prevent abuse
        if file_count > 20:
            return jsonify({"error":"Too many files requested"}), 400

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

if __name__ == "__main__":
    app.run()
