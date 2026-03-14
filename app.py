from flask import Flask, request, jsonify
import requests
import base64
import random
import string
import os

app = Flask(__name__)

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

    data = request.json

    file_count = int(data.get("fileCount",1))
    file_content = data.get("fileContent","test")

    if file_count > 20:
        return {"error":"Too many files"},400

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

        if r.status_code in [200,201]:

            raw = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/{filename}"

            links.append(f"loadstring(game:HttpGet('{raw}'))()")

    return jsonify({"links":links})

if __name__ == "__main__":
    app.run()
