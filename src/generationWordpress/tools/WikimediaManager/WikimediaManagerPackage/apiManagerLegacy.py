from datetime import datetime
import threading
#print("Threads at start:", threading.enumerate())
import sys
#print("First imports:", list(sys.modules.keys())[:30])
#print("Threads after monkey_patch:", threading.enumerate())
import asyncio
import json
import os
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

API_IP_ADDRESS = "127.0.0.1"
API_PORT = 6000

# Variables globales pour le monitoring
start_time = time.time()

"""
voir https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
pour wikimedia
"""
class APIRequestScheduler:
    _instances = {}

    def __new__(cls, api_patterns, *args, **kwargs):
        key = tuple(sorted(api_patterns))
        if key not in cls._instances:
            cls._instances[key] = super(APIRequestScheduler, cls).__new__(cls)
        return cls._instances[key]

    def __init__(self, api_patterns):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.api_patterns = api_patterns
        self.CALLS_PER_SECOND = 1  # Default to 1 call per second
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND
        self.request_queue = Queue()
        self.response_store = {}
        self.request_dict = {} # ghost of the queue, for debug
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

    def validate_url(self, base_url):
        """Valide l'URL contre les patterns autorisés"""
        for pattern in self.api_patterns:
            if hasattr(pattern, "pattern"):
                # Pattern regex
                if re.match(pattern, base_url):
                    return True
            else:
                # URL exacte ou préfixe
                if base_url.startswith(str(pattern)):
                    return True
        return False

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
                        resurl = f"http://{API_IP_ADDRESS}:{API_PORT}/send_message"
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
                resurl = f"http://{API_IP_ADDRESS}:{API_PORT}/send_message"
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
                resurl = f"http://{API_IP_ADDRESS}:{API_PORT}/send_message"
                data = {"client_id": f"{client_id}", "message": {
                    "request_id": request_id,
                    "message": "error",
                    "error": str(e)
                }}
                response = requests.post(resurl, json=data)
                print(response.json())
        finally:
            #await asyncio.to_thread(self.request_queue.task_done)
            pass

    def start_worker(self):
        threading.Thread(target=self.process_queue, daemon=True).start()

    def add_request(self, url, payload=None, cache_duration=0, method="POST", client_id=None, headers={},
                    **request_kwargs):
        if request_kwargs is None:
            request_kwargs = {}
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        if not self.validate_url(base_url):
            raise ValueError(f"URL non gérée par cette instance: {base_url}")

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
        self.request_dict[request_id] = request_data # il faudra vider ce dict quand une requête est enlevée de request_queue

        estimated_delay = self.request_queue.qsize() * self.CALL_INTERVAL
        return request_id, estimated_delay

    def get_response(self, request_id):
        with self.lock:
            return self.response_store.pop(request_id, None)

    def has_request(self, request_id):
        with self.lock:
            #return request_id in self.response_store
            return request_id in self.request_dict


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
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

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
        return {"status": f"Message sent {message}", "client_id": client_id}, 200
    else:
        return {"error": "Client not found"}, 404


# Managing separate API request schedulers for different sets of URLs
schedulers = {}
scheduler_ids = {}


@app.route("/api/initialize", methods=["GET", "POST"])
@authenticate
def initialize_scheduler():
    #logging.debug(f"debut de création d'un manager par {request.method}")
    if request.method == "GET":
        api_patterns = request.args.getlist("api_patterns")
    else:
        data = request.json
        api_patterns = data.get("api_patterns")

    if not api_patterns:
        return jsonify({"error": "api_patterns are required"}), 400

    scheduler_id = str(uuid.uuid4())
    scheduler = APIRequestScheduler(api_patterns)
    schedulers[scheduler_id] = scheduler
    scheduler_ids[tuple(sorted(api_patterns))] = scheduler_id

    # Start a thread for the manager's queue
    threading.Thread(target=lambda: asyncio.run(scheduler.process_queue()), daemon=True).start()

    return jsonify({"message": "Manager initialized for the given API URLs.", "scheduler_id": scheduler_id})

@app.route("/api/health", methods=["GET"])
def health_check():
    """Endpoint de santé pour monitoring"""
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.1.0",
            "schedulers_active": len(schedulers),
            "connected_clients": len(connected_clients),
            "uptime_seconds": time.time() - start_time if 'start_time' in globals() else 0
        }

        return jsonify(health_data)

    except Exception as e:
        #logger.error(f"Erreur dans le health check: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/api/set_rate_limit", methods=["POST"])
@authenticate
def set_rate_limit():
    scheduler_id = request.args.get("scheduler_id")
    if not scheduler_id:
        scheduler_id = request.json["scheduler_id"]
    limit = request.args.get("limit", type=float)
    if not limit:
        limit = request.json["limit"]

    if not scheduler_id or scheduler_id not in schedulers:
        return jsonify({"error": "Manager not found for the given ID."}), 404

    if not limit or limit <= 0:
        return jsonify({"error": "A valid limit is required."}), 400

    scheduler = schedulers[scheduler_id]
    scheduler.set_rate_limit(limit)

    return jsonify({"message": "Rate limit updated."})

def getRequestParam(request, paramName):
    param = None
    param = request.args.get(paramName, None)
    if not param and paramName in request.json:
        param = request.json[paramName]
    return param

@app.route("/api/request", methods=["POST", "GET"])
@authenticate
def api_request():

    scheduler_id = getRequestParam(request, "scheduler_id")
    if not scheduler_id or scheduler_id not in schedulers:
        return jsonify({"error": "Scheduler not found for the given ID."}), 404

    scheduler = schedulers[scheduler_id]
    client_id = getRequestParam(request, "client_id")
    url = getRequestParam(request, "url")
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
        request_id, estimated_delay = scheduler.add_request(
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



@app.route("/api/openstatus", methods=["GET"])
# status sans authentification pour debug; fournit la liste des requêtes en cours
def api_openstatus():
    try:
        #stat = {"status": "request ids", "schedulerids": str(len(scheduler_ids)), "requestIds": []}
        stat = {"status": "request ids", "schedulers_count": str(len(schedulers)), "requestIds": []}
        for scheduler in schedulers.values():
            reqids = scheduler.request_dict
            stat["requestIds"].append(reqids)
        return jsonify(stat)
    except Exception as e:
        print(f"Erreur dans l'interrogation du status:\n {e}")
        return None

@app.route("/api/status/<request_id>", methods=["GET"])
@authenticate
def api_status(request_id):
    found_request = False
    try:
        for scheduler in schedulers.values():
            if scheduler.has_request(request_id):
                found_request = True
                response = scheduler.get_response(request_id)
                if response:
                    # scheduler.request_dict.pop(request_id) # remove from the ghost dict
                    return jsonify({"status": "complete", "response": response})

        if not found_request:
            return jsonify({"error": f"Request ID not found: {request_id}"}), 404

        return jsonify({"status": "pending", "message": "Your request is still being processed."})
    except Exception as e:
        print(f"Erreur dans l'interrogation du status:\n {e}")
        return None

@app.route("/api/delete_scheduler", methods=["DELETE"])
@authenticate
def delete_scheduler():
    scheduler_id = request.args.get("scheduler_id")

    if not scheduler_id or scheduler_id not in schedulers:
        return jsonify({"error": "scheduler not found for the given ID."}), 404

    scheduler = schedulers[scheduler_id]

    # Supprimer le scheduler de la liste
    del schedulers[scheduler_id]

    # Supprimer l'association des URL associées à cet ID
    for key, value in list(scheduler_ids.items()):
        if value == scheduler_id:
            del scheduler_ids[key]

    return jsonify({"message": f"scheduler with ID {scheduler_id} deleted successfully."})


@app.route("/", methods=["GET"])
def home():
    return "<html><body><h2>Salut, API privée pour gérer des limitations d'accès (nb.Req/mn, ...) sur des web api; avec Socket.IO server running with client_id support</h2></body></html>"


if __name__ == "__main__":
    # app.run(debug=False)
    # socketio.run(app, debug=False)
    socketio.run(app, host=API_IP_ADDRESS, port=API_PORT, debug=False)
