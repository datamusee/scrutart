import threading
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

from configPrivee import config

API_IP_ADDRESS = "127.0.0.1"
API_PORT = 6000

"""
voir https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
pour wikimedia
"""
class APIRequestScheduler:
    _instances = {}

    def __new__(cls, api_urls, *args, **kwargs):
        key = tuple(sorted(api_urls))
        if key not in cls._instances:
            cls._instances[key] = super(APIRequestScheduler, cls).__new__(cls)
        return cls._instances[key]

    def __init__(self, api_urls):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.api_urls = api_urls
        self.CALLS_PER_SECOND = 1  # Default to 1 call per second
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND
        self.request_queue = Queue()
        self.response_store = {}
        self.request_dict = {}  # ghost of the queue, for debug
        self.cache_dir = os.path.join(os.getcwd(), 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.lock = threading.Lock()
        
        # ✅ CORRECTION 1: Démarrer correctement le worker
        self.worker_thread = threading.Thread(target=self._run_async_worker, daemon=True)
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

    def _run_async_worker(self):
        """✅ CORRECTION 2: Worker qui lance correctement process_queue de manière asynchrone"""
        asyncio.run(self.process_queue())

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
            request_data = self.request_queue.get()
            if request_data is None:
                break
            await self.perform_request(request_data)
            # ✅ CORRECTION 3: Marquer la tâche comme terminée
            self.request_queue.task_done()

    async def perform_request(self, request_data):
        request_id = request_data['request_id']
        url = request_data['url']
        payload = request_data.get('payload', None)
        method = request_data.get('method', 'POST').upper()
        cache_duration = request_data.get('cache_duration', 0)
        request_kwargs = request_data.get('request_kwargs', {})
        client_id = request_data.get('client_id')
        headers = request_data.get('headers', {})

        print(f"🔄 Processing request {request_id[:8]}... - {method} {url}")

        # Construct a cache key based on URL, payload, and request kwargs
        cache_key = (url, frozenset(payload.items()) if payload else None,
                     frozenset(request_kwargs.items()) if request_kwargs else None)
        cache_path = self.get_cache_path(cache_key)

        # ✅ Check cache first
        if cache_duration > 0 and os.path.exists(cache_path):
            with open(cache_path, 'r') as cache_file:
                cached_data = json.load(cache_file)
                if time.time() - cached_data['timestamp'] < cache_duration:
                    print(f"📦 Cache hit for {request_id[:8]}...")
                    with self.lock:
                        self.response_store[request_id] = cached_data['response']
                        # ✅ CORRECTION 4: Nettoyer request_dict après traitement
                        self.request_dict.pop(request_id, None)

                    # Notifier le client si connecté
                    if client_id in connected_clients:
                        await self._notify_client(client_id, request_id, cached_data['response'])
                    return

        # Effectue l'appel HTTP de manière asynchrone
        try:
            await asyncio.sleep(self.CALL_INTERVAL)

            # ✅ CORRECTION 5: Corriger l'utilisation d'aiohttp
            async with ClientSession() as session:
                if method == "POST":
                    # Pour POST, utiliser json= pour le payload
                    async with session.post(url, json=payload, headers=headers, **request_kwargs) as rep:
                        response = await rep.json()
                elif method == "GET":
                    # Pour GET, utiliser params= pour le payload
                    async with session.get(url, params=payload, headers=headers, **request_kwargs) as rep:
                        response = await rep.json()
                elif method == "PUT":
                    async with session.put(url, json=payload, headers=headers, **request_kwargs) as rep:
                        response = await rep.json()
                elif method == "DELETE":
                    async with session.delete(url, headers=headers, **request_kwargs) as rep:
                        response = await rep.json()
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

            api_response = response
            print(f"✅ Request {request_id[:8]}... completed successfully")

            # Cache the response if caching is enabled
            if cache_duration > 0:
                with open(cache_path, 'w') as cache_file:
                    json.dump({'response': api_response, 'timestamp': time.time()}, cache_file)

            # Store the response
            with self.lock:
                self.response_store[request_id] = api_response
                # ✅ CORRECTION 4: Nettoyer request_dict après traitement
                self.request_dict.pop(request_id, None)

            # Notifier le client si connecté
            if client_id in connected_clients:
                await self._notify_client(client_id, request_id, api_response)

        except Exception as e:
            print(f"❌ Error in request {request_id[:8]}...: {str(e)}")
            with self.lock:
                self.response_store[request_id] = {"error": str(e)}
                # ✅ CORRECTION 4: Nettoyer request_dict même en cas d'erreur
                self.request_dict.pop(request_id, None)

            # Notifier le client en cas d'erreur
            if client_id in connected_clients:
                await self._notify_client(client_id, request_id, {"error": str(e)})

    async def _notify_client(self, client_id, request_id, response_data):
        """Helper method to notify client"""
        try:
            resurl = f"http://{API_IP_ADDRESS}:{API_PORT}/send_message"
            data = {
                "client_id": f"{client_id}", 
                "message": {
                    "request_id": request_id,
                    "response": response_data,
                    "message": "voir response"
                }
            }
            # Use aiohttp for async HTTP call
            async with ClientSession() as session:
                async with session.post(resurl, json=data) as resp:
                    result = await resp.json()
                    print(f"Client notification result: {result}")
        except Exception as e:
            print(f"Error notifying client {client_id}: {e}")

    def start_worker(self):
        # ✅ CORRECTION 6: Cette méthode ne devrait plus être utilisée
        # Le worker est maintenant démarré correctement dans __init__
        pass

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
        
        print(f"➕ Adding request {request_id[:8]}... to queue - {method} {url}")
        self.request_queue.put(request_data)
        
        with self.lock:
            self.request_dict[request_id] = request_data

        estimated_delay = self.request_queue.qsize() * self.CALL_INTERVAL
        return request_id, estimated_delay

    def get_response(self, request_id):
        """✅ CORRECTION 7: Améliorer la récupération des réponses"""
        with self.lock:
            response = self.response_store.pop(request_id, None)
            if response is not None:
                print(f"📤 Response retrieved for {request_id[:8]}...")
            return response

    def has_request(self, request_id):
        """✅ CORRECTION 8: Vérifier à la fois request_dict ET response_store"""
        with self.lock:
            in_queue = request_id in self.request_dict
            has_response = request_id in self.response_store
            result = in_queue or has_response
            print(f"🔍 Request {request_id[:8]}... - in_queue: {in_queue}, has_response: {has_response}, result: {result}")
            return result


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

@socketio.on('custom_event')  # pour test avec trialSOcketIOInClass
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


# Managing separate API request schedulers for different sets of URLs
schedulers = {}
scheduler_ids = {}


@app.route("/api/initialize", methods=["GET", "POST"])
@authenticate
def initialize_scheduler():
    if request.method == "GET":
        api_urls = request.args.getlist("api_urls")
    else:
        data = request.json
        api_urls = data.get("api_urls")

    if not api_urls:
        return jsonify({"error": "api_urls are required"}), 400

    scheduler_id = str(uuid.uuid4())
    scheduler = APIRequestScheduler(api_urls)
    schedulers[scheduler_id] = scheduler
    scheduler_ids[tuple(sorted(api_urls))] = scheduler_id

    # ✅ CORRECTION 9: Ne plus démarrer un thread supplémentaire ici
    # Le worker est déjà démarré dans __init__
    print(f"🚀 Scheduler {scheduler_id[:8]}... initialized for URLs: {api_urls}")

    return jsonify({"message": "Manager initialized for the given API URLs.", "scheduler_id": scheduler_id})


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
    if not param and request.json and paramName in request.json:
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
        headers = request.args.get("headers", None) if request.args.get("headers", None) else (request.json.get("headers", None) if request.json else {})
        cache_duration = request.args.get("cache_duration", type=int, default=0) or (request.json.get("cache_duration", 0) if request.json else 0)
        api_method = request.args.get("method", "GET") or (request.json.get("method", "GET") if request.json else "GET")
        api_method = api_method.upper()
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
def api_openstatus():
    try:
        stat = {"status": "request ids", "schedulerids": str(len(schedulers)), "requestIds": []}
        for scheduler_id, scheduler in schedulers.items():
            with scheduler.lock:
                reqids = list(scheduler.request_dict.keys())
                responseids = list(scheduler.response_store.keys())
            stat["requestIds"].append({
                "scheduler_id": scheduler_id[:8] + "...",
                "pending_requests": reqids,
                "ready_responses": responseids
            })
        return jsonify(stat)
    except Exception as e:
        print(f"Erreur dans l'interrogation du status:\n {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/status/<request_id>", methods=["GET"])
@authenticate
def api_status(request_id):
    print(f"🔍 Checking status for request {request_id[:8]}...")
    found_request = False
    try:
        for scheduler_id, scheduler in schedulers.items():
            if scheduler.has_request(request_id):
                found_request = True
                print(f"📍 Request {request_id[:8]}... found in scheduler {scheduler_id[:8]}...")
                
                response = scheduler.get_response(request_id)
                if response:
                    print(f"✅ Response ready for {request_id[:8]}...")
                    return jsonify({"status": "complete", "response": response})
                else:
                    print(f"⏳ Request {request_id[:8]}... still pending...")
                    return jsonify({"status": "pending", "message": "Your request is still being processed."})

        if not found_request:
            print(f"❌ Request {request_id[:8]}... not found in any scheduler")
            return jsonify({"error": f"Request ID not found: {request_id}"}), 404

    except Exception as e:
        print(f"Erreur dans l'interrogation du status:\n {e}")
        return jsonify({"error": str(e)}), 500

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
    socketio.run(app, host=API_IP_ADDRESS, port=API_PORT, debug=False)