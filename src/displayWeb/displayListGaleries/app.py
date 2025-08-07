from flask import Flask, render_template, jsonify, request
import requests
import os
import json
import time

app = Flask(__name__)

CACHE_DIR = "cache"
CACHE_DURATION = 3600  # 1h

API_ENDPOINTS = {
    "artistes": "https://example.com/api/artistes",
    "styles": "https://example.com/api/styles",
    "mouvements": "https://example.com/api/mouvements",
    "themes": "https://example.com/api/themes",
}

def get_cached_data(data_type, force=False):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{data_type}.json").replace("\\", "/")

    if not force and os.path.exists(cache_path):
        if time.time() - os.path.getmtime(cache_path) < CACHE_DURATION:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
    url = API_ENDPOINTS.get(data_type)
    if not url:
        return []

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    except Exception as e:
        print(f"Erreur API: {e}")
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/apiManager")
def index():
    return render_template("index.html")

@app.route("/apiManager/data")
def data():
    return api_data()

@app.route("/api/data")
def api_data():
    data_type = request.args.get("type")
    force = request.args.get("force") == "1"
    if data_type not in API_ENDPOINTS:
        return jsonify({"error": "Type inconnu"}), 400
    data = get_cached_data(data_type, force=force)
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
