import os
import time
import uuid
import threading
import json
from queue import Queue
from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse
from functools import wraps

"""
voir https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
pour wikimedia
"""
class APIRequestManager:
    _instances = {}

    def __new__(cls, api_urls, *args, **kwargs):
        key = tuple(sorted(api_urls))
        if key not in cls._instances:
            cls._instances[key] = super(APIRequestManager, cls).__new__(cls)
        return cls._instances[key]

    def __init__(self, api_urls):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.api_urls = api_urls
        self.CALLS_PER_SECOND = 1  # Default to 1 call per second
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND
        self.request_queue = Queue()
        self.response_store = {}
        self.cache_dir = os.path.join(os.getcwd(), 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.lock = threading.Lock()
        self.worker_thread = threading.Thread(target=self.start_worker, daemon=True)
        self.worker_thread.start()
        self._initialized = True

    def set_rate_limit(self, calls_per_second):
        self.CALLS_PER_SECOND = calls_per_second
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND

    def get_cache_path(self, cache_key):
        return os.path.join(self.cache_dir, f"{hash(cache_key)}.json")

    def process_queue(self):
        while True:
            request_data = self.request_queue.get()
            if request_data is None:
                break

            request_id = request_data['request_id']
            url = request_data['url']
            httpcmd = request_data.get('httpcmd', "GET")
            payload = request_data.get('payload', None)
            headers = request_data.get('headers', None)
            cache_duration = request_data.get('cache_duration', 0)

            cache_key = (url, frozenset(payload.items()) if payload else None)
            cache_path = self.get_cache_path(cache_key)

            if cache_duration > 0 and os.path.exists(cache_path):
                with open(cache_path, 'r') as cache_file:
                    cached_data = json.load(cache_file)
                    if time.time() - cached_data['timestamp'] < cache_duration:
                        with self.lock:
                            self.response_store[request_id] = cached_data['response']
                        self.request_queue.task_done()
                        continue

            try:
                time.sleep(self.CALL_INTERVAL)
                if httpcmd=="GET":
                    response = requests.get(url, json=payload, headers=headers)
                else:
                    response = requests.post(url, json=payload, headers=headers)
                try:
                    api_response = response.json()
                except ValueError:
                    api_response = response.text

                if cache_duration > 0:
                    with open(cache_path, 'w') as cache_file:
                        json.dump({'response': api_response, 'timestamp': time.time()}, cache_file)

                with self.lock:
                    self.response_store[request_id] = api_response

            except Exception as e:
                with self.lock:
                    self.response_store[request_id] = {"error": str(e)}

            self.request_queue.task_done()

    def start_worker(self):
        threading.Thread(target=self.process_queue, daemon=True).start()

    def add_request(self, url, httpcmd, payload, headers, cache_duration=0):
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        if base_url not in self.api_urls:
            raise ValueError("Base URL not managed by this instance")

        request_id = str(uuid.uuid4())

        request_data = {
            'request_id': request_id,
            'url': url,
            'httpcmd': httpcmd,
            'payload': payload,
            "headers": headers,
            'cache_duration': cache_duration
        }
        self.request_queue.put(request_data)

        estimated_delay = self.request_queue.qsize() * self.CALL_INTERVAL
        return request_id, estimated_delay

    def get_response(self, request_id):
        with self.lock:
            return self.response_store.pop(request_id, None)

    def has_request(self, request_id):
        with self.lock:
            return request_id in self.response_store

def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_token = request.headers.get("Authorization")
        if not auth_token or auth_token != "Bearer SECRET_TOKEN":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)

# Managing separate API request managers for different sets of URLs
managers = {}
manager_ids = {}

@app.route("/api/initialize", methods=["POST"])
@authenticate
def initialize_manager():
    if request.method == "GET":
        api_urls = request.args.getlist("api_urls")
    else:
        data = request.json
        api_urls = data.get("api_urls")

    if not api_urls:
        return jsonify({"error": "api_urls are required"}), 400

    manager = APIRequestManager(api_urls)
    manager_id = str(uuid.uuid4())
    managers[manager_id] = manager
    manager_ids[tuple(sorted(api_urls))] = manager_id
    return jsonify({"message": "Manager initialized for the given API URLs.", "manager_id": manager_id})

@app.route("/api/set_rate_limit", methods=["POST"])
@authenticate
def set_rate_limit():
    manager_id = request.args.get("manager_id")
    if not manager_id:
        manager_id = request.json["manager_id"]
    limit = request.args.get("limit", type=float)
    if not limit:
        limit = request.json["limit"]

    if not manager_id or manager_id not in managers:
        return jsonify({"error": "Manager not found for the given ID."}), 404

    if not limit or limit <= 0:
        return jsonify({"error": "A valid limit is required."}), 400

    manager = managers[manager_id]
    manager.set_rate_limit(limit)

    return jsonify({"message": "Rate limit updated."})

@app.route("/api/request", methods=["POST", "GET"])
@authenticate
def api_request():
    manager_id = request.args.get("manager_id", request.json["manager_id"])
    httpcmd = request.args.get("httpcmd", request.json["httpcmd"])
    headers =  request.args.get("headers", request.json["headers"])
    cache_duration = request.args.get("cache_duration", request.json["cache_duration"])

    if not manager_id or manager_id not in managers:
        return jsonify({"error": "Manager not found for the given ID."}), 404

    manager = managers[manager_id]

    if request.method == "POST":
        data = request.json
        url = data.get("url")
        payload = data.get("payload", { "dummy":"dummy" })
        cache_duration = data.get("cache_duration", 0)

        if not url or not payload:
            return jsonify({"error": "URL and payload are required."}), 400

    elif request.method == "GET":
        url = request.args.get("url")
        cache_duration = request.args.get("cache_duration", type=int, default=0)
        if not url:
            return jsonify({"error": "URL is required."}), 400
        payload = {}  # Assume no payload for GET requests

    try:
        request_id, estimated_delay = manager.add_request(url, httpcmd, payload, headers, cache_duration)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "uuid": request_id,
        "status_url": f"/api/status/{request_id}",
        "estimated_delay": estimated_delay,
        "message": "Your request is in the queue. Use the provided URL to check the status."
    })

@app.route("/api/status/<request_id>", methods=["GET"])
@authenticate
def api_status(request_id):
    found_request = False
    for manager in managers.values():
        if manager.has_request(request_id):
            found_request = True
            response = manager.get_response(request_id)
            if response:
                return jsonify({"status": "complete", "response": response})

    if not found_request:
        return jsonify({"error": f"Request ID not found: {request_id}"}), 404

    return jsonify({"status": "pending", "message": "Your request is still being processed."})

@app.route("/api/delete_manager", methods=["DELETE"])
@authenticate
def delete_manager():
    manager_id = request.args.get("manager_id")

    if not manager_id or manager_id not in managers:
        return jsonify({"error": "Manager not found for the given ID."}), 404

    # Supprimer le manager de la liste
    del managers[manager_id]

    # Supprimer l'association des URL triées à cet ID
    for key, value in list(manager_ids.items()):
        if value == manager_id:
            del manager_ids[key]

    return jsonify({"message": f"Manager with ID {manager_id} deleted successfully."})

@app.route("/", methods=["GET"])
def home():
    return "<html><body><h2>Salut, API privée pour gérer des limitations d'accès (nb.Req/mn, ...) sur des web api</h2></body></html>"

if __name__=="__main__":
    app.run(debug=False)