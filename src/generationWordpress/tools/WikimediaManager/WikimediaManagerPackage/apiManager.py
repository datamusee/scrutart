import asyncio
import json
import os
import threading
import time
import uuid
from functools import wraps
from queue import Queue
from urllib.parse import urlparse
import logging
import requests
from aiohttp import ClientSession
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room

from configPrivee  import config


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
        # Create a new asyncio event loop
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.start_event_loop, daemon=True)
        self.loop_thread.start()
        self._initialized = True

    def start_event_loop(self):
        """
        Run the event loop in a separate thread.
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def set_rate_limit(self, calls_per_second):
        self.CALLS_PER_SECOND = calls_per_second
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND

    def get_cache_path(self, cache_key):
        return os.path.join(self.cache_dir, f"{hash(cache_key)}.json")

    async def process_queue(self):
        """
        Process requests from the queue asynchronously.
        """
        while True:
            # request_data = await asyncio.to_thread(self.request_queue.get)
            request_data = self.request_queue.get()
            if request_data is None:
                break
            await self.perform_request(request_data)

    async def perform_request(self, request_data):
        request_id = request_data['request_id']
        url = request_data['url']
        payload = request_data.get('payload', None)
        method = request_data.get('method', 'POST').upper()
        cache_duration = request_data.get('cache_duration', 0)
        request_kwargs = request_data.get('request_kwargs', {})
        client_id = request_data.get('client_id')
        headers = request_data.get('headers', {})

        # Construct a cache key based on URL, payload, and request kwargs
        cache_key = (url, frozenset(payload.items()) if payload else None,
                     frozenset(request_kwargs.items()) if request_kwargs else None)
        cache_path = self.get_cache_path(cache_key)

        if cache_duration > 0 and os.path.exists(cache_path):
            with open(cache_path, 'r') as cache_file:
                cached_data = json.load(cache_file)
                if time.time() - cached_data['timestamp'] < cache_duration:
                    with self.lock:
                        self.response_store[request_id] = cached_data['response']

                    # Notifier le client si connecté
                    if client_id in connected_clients:
                        resurl = "http://localhost:5000/send_message"
                        data = {
                            "client_id": f"{client_id}", "message": {
                                "request_id": request_id,
                                "response": cached_data['response'],
                                "message": "voir response"
                            }}
                        response = requests.post(resurl, json=data)
                        print(response.json())
                    await asyncio.to_thread(self.request_queue.task_done)

        # Effectue l'appel HTTP de manière asynchrone
        try:
            await asyncio.sleep(self.CALL_INTERVAL)

            # Dynamically call the appropriate HTTP method
            if method == "POST":
                # response = await asyncio.to_thread(requests.post(url, json=payload, **request_kwargs))
                async with ClientSession() as session:
                    async with session.post(url, params=payload, headers=headers, **request_kwargs) as rep:
                        response = await rep.json()
            elif method == "GET":
                # response = await asyncio.to_thread(requests.get(url, params=payload, **request_kwargs))
                async with ClientSession() as session:
                    async with session.get(url, params=payload, headers=headers, **request_kwargs) as rep:
                        response = await rep.json()
            elif method == "PUT":
                response = await asyncio.to_thread(requests.put(url, json=payload, **request_kwargs))
            elif method == "DELETE":
                response = await asyncio.to_thread(requests.delete(url, **request_kwargs))
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Handle response as JSON or raw text
            try:
                api_response = response  # response.json()
            except ValueError:
                api_response = response.text

            # Cache the response if caching is enabled
            if cache_duration > 0:
                with open(cache_path, 'w') as cache_file:
                    json.dump({'response': api_response, 'timestamp': time.time()}, cache_file)

            # Store the response
            with self.lock:
                self.response_store[request_id] = api_response

            # Notifier le client si connecté
            if client_id in connected_clients:
                resurl = "http://localhost:5000/send_message"
                data = {"client_id": f"{client_id}", "message": {
                    "request_id": request_id,
                    "message": api_response
                }}
                response = requests.post(resurl, json=data)
                print(response.json())

        except Exception as e:
            with self.lock:
                self.response_store[request_id] = {"error": str(e)}

            # Notifier le client en cas d'erreur
            if client_id in connected_clients:
                resurl = "http://localhost:5000/send_message"
                data = {"client_id": f"{client_id}", "message": {
                    "request_id": request_id,
                    "message": "error",
                    "error": str(e)
                }}
                response = requests.post(resurl, json=data)
                print(response.json())
        finally:
            await asyncio.to_thread(self.request_queue.task_done)

    def start_worker(self):
        threading.Thread(target=self.process_queue, daemon=True).start()

    def add_request(self, url, payload=None, cache_duration=0, method="POST", client_id=None, headers={},
                    **request_kwargs):
        if request_kwargs is None:
            request_kwargs = {}
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        if base_url not in self.api_urls:
            raise ValueError("Base URL not managed by this instance")

        request_id = str(uuid.uuid4())

        request_data = {
            'request_id': request_id,
            'url': url,
            'payload': payload,
            'cache_duration': cache_duration,
            'method': method.upper(),
            'headers': headers,
            'request_kwargs': request_kwargs or {},  # Additional parameters for requests
            'client_id': client_id
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
        bearer = config['admin']['Bearer']
        if not auth_token or auth_token != f"Bearer {bearer}":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated_function


# Initialise Flask-SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Gérer les connexions WebSocket (optionnel, pour garder une trace des clients connectés)
connected_clients = {}

@socketio.on('custom_event') # pour test avec trialSOcketIOInClass
def handle_custom_event():
    emit('custom_event', data={"message": "Custom event reçu."})


@socketio.on('response_ready')
def handle_resquest_response(client_id, response):
    emit('response_ready', data=response)


@socketio.on('connect')
def handle_connect():
    print("Client connected")
    emit("connect", data={"message": "Connected successfully."})


@socketio.on('register')
def handle_register(data):
    """
    Enregistre un client avec un client_id donné.
    """
    client_id = data.get('client_id')
    if client_id:
        connected_clients[client_id] = request.sid  # Associe le client_id au socket ID
        join_room(client_id)  # Ajoute le client à une "room" identifiée par client_id
        print(f"Client registered with client_id: {client_id}")
        emit('message', {'data': f'You are registered with client_id: {client_id}'}, room=client_id)


@socketio.on('disconnect')
def handle_disconnect():
    """
    Supprime le client_id lors de la déconnexion.
    """
    disconnected_client = None
    for client_id, sid in list(connected_clients.items()):
        if sid == request.sid:
            disconnected_client = client_id
            del connected_clients[client_id]
            leave_room(client_id)
            break
    print(f"Client disconnected: {disconnected_client}")


@app.route('/send_message', methods=['POST'])
def send_message():
    """
    Envoie un message à un client spécifique identifié par son client_id.
    """
    data = request.json
    client_id = data.get('client_id')
    message = data.get('message')

    if client_id in connected_clients:
        emit('message', {'data': message}, room=client_id, namespace='/')
        return {"status": "Message sent", "client_id": client_id}, 200
    else:
        return {"error": "Client not found"}, 404


# Managing separate API request managers for different sets of URLs
managers = {}
manager_ids = {}


@app.route("/api/initialize", methods=["GET", "POST"])
@authenticate
def initialize_manager():
    logging.debug(f"debut de création d'un manager par {request.method}")
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

    # Start a thread for the manager's queue
    threading.Thread(target=lambda: asyncio.run(manager.process_queue()), daemon=True).start()

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
    manager_id = request.args.get("manager_id")
    if not manager_id and "manager_id" in request.json:
        manager_id = request.json["manager_id"]
    if not manager_id or manager_id not in managers:
        return jsonify({"error": "Manager not found for the given ID."}), 404

    manager = managers[manager_id]
    client_id = request.args.get("client_id")
    if not client_id and "client_id" in request.json:
        client_id = request.json["client_id"]
    url = request.args.get("url", None)
    if not url and "url" in request.json:
        url = request.json["url"]
    if request.method == "POST":
        data = request.json
        headers = data.get("headers", {})
        payload = data.get("payload", None)
        cache_duration = data.get("cache_duration", 0)
        api_method = data.get("method", "POST").upper()  # Default to POST for Web API
        request_kwargs = data.get("request_kwargs", {})
    elif request.method == "GET":
        headers = request.args.get("headers", None) if request.args.get("headers", None) else request.json.get("headers", None)
        cache_duration = max(request.args.get("cache_duration", type=int, default=0), request.json["cache_duration"])
        api_method = request.args.get("method", "GET")  # Default to GET for Web API
        api_method = api_method.upper() if api_method else request.json("method", "GET").upper()
        request_kwargs = {}  # Assume no additional kwargs for GET requests
        payload = None  # GET requests usually don't have a payload

    if not url:
        return jsonify({"error": "URL is required."}), 400

    try:
        request_id, estimated_delay = manager.add_request(
            url=url,
            payload=payload,
            cache_duration=cache_duration,
            method=api_method,
            client_id=client_id,
            headers=headers,
            **request_kwargs
        )
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
    return "<html><body><h2>Salut, API privée pour gérer des limitations d'accès (nb.Req/mn, ...) sur des web api; avec Socket.IO server running with client_id support</h2></body></html>"


if __name__ == "__main__":
    # app.run(debug=False)
    # socketio.run(app, debug=False)
    socketio.run(app, host='127.0.0.1', port=6000, debug=False)
