import re
import threading
import sys
import asyncio
import json
import psutil
import os
import time
import uuid
from functools import wraps
from queue import Queue, Empty
from urllib.parse import urlparse
import requests
from aiohttp import ClientSession
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional, Tuple, List
from aiohttp import ClientSession, ClientTimeout, ClientError
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import signal
import atexit
from datetime import datetime, timedelta
import aiohttp

from configPrivee import config

# Configuration
API_IP_ADDRESS = "127.0.0.1"
API_PORT = 6000
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1.5
REQUEST_TIMEOUT = 30
CACHE_CLEANUP_INTERVAL = 3600  # 1 hour
MAX_QUEUE_SIZE = 10000

# Configuration du logging
def setup_logging():
    """Configure le système de logging avec rotation des fichiers"""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))

    # Formatteur
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )

    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler fichier avec rotation
    file_handler = RotatingFileHandler(
        'api_manager.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logging()

@dataclass
class RequestData:
    """Structure de données pour les requêtes API"""
    request_id: str
    url: str
    payload: Optional[Dict] = None
    method: str = 'POST'
    headers: Optional[Dict] = None
    cache_duration: int = 0
    request_kwargs: Optional[Dict] = None
    client_id: Optional[str] = None
    timestamp: float = None
    retry_count: int = 0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.headers is None:
            self.headers = {}
        if self.request_kwargs is None:
            self.request_kwargs = {}

class APIError(Exception):
    """Exception personnalisée pour les erreurs d'API"""
    def __init__(self, message: str, status_code: int = None, request_id: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id

class RateLimitExceeded(APIError):
    """Exception pour les dépassements de limite de taux"""
    pass

class APIRequestScheduler:
    """
    Gestionnaire de requêtes API avec limitation de taux, cache et gestion d'erreurs robuste
    """
    _instances = {}

    def __new__(cls, api_patterns, *args, **kwargs):
        patterns_hash = cls._hash_patterns(api_patterns)
        if patterns_hash not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[patterns_hash] = instance
        return cls._instances[patterns_hash]

    @staticmethod
    def _hash_patterns(patterns):
        return hash(tuple(sorted(patterns)))

    def __init__(self, api_patterns):
        if hasattr(self, '_initialized'):
            return

        patterns_hash = self._hash_patterns(api_patterns)
        self.scheduler_id = patterns_hash  # Utiliser le hash comme scheduler_id

        self.api_patterns = api_patterns
        self.CALLS_PER_SECOND = 1  # Default to 1 call per second
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND
        self.request_queue = Queue()
        self.response_store = {}
        self.request_dict = {}  # ghost of the queue, for debug
        self.cache_dir = os.path.join(os.getcwd(), 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.lock = threading.Lock()
        key = tuple(sorted(api_patterns))
        self.scheduler_id = str(hash(key))
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

    def get_stats(self) -> Dict:
        """Retourne les statistiques du scheduler"""
        with self.lock:
            return {
                # "scheduler_id": self.scheduler_id,
                "queue_size": self.request_queue.qsize(),
                "pending_requests": len(self.request_dict),
                "pending_responses": len(self.response_store),
                "calls_per_second": self.CALLS_PER_SECOND,
                "managed_urls": len(self.api_patterns)
            }

    def set_rate_limit(self, calls_per_second):
        """Configure la limitation de taux"""
        if calls_per_second <= 0:
            raise ValueError("Le taux d'appels doit être positif")

        self.CALLS_PER_SECOND = calls_per_second
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND
        logger.info(f"Limite de taux mise à jour: {calls_per_second} appels/seconde")

    def get_cache_path(self, cache_key: str) -> str:
        """Génère le chemin du fichier cache"""
        return os.path.join(self.cache_dir, f"{abs(hash(str(cache_key)))}.json")

    def _cleanup_expired_cache(self):
        """Nettoie les fichiers de cache expirés"""
        try:
            current_time = time.time()
            cleaned_count = 0

            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.cache_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)

                        # Vérifier si le cache est expiré (plus de 24h)
                        if current_time - data.get('timestamp', 0) > 86400:
                            os.remove(filepath)
                            cleaned_count += 1
                    except (json.JSONDecodeError, OSError) as e:
                        logger.warning(f"Erreur lors du nettoyage de {filepath}: {e}")
                        try:
                            os.remove(filepath)
                            cleaned_count += 1
                        except OSError:
                            pass

            if cleaned_count > 0:
                logger.info(f"{cleaned_count} fichiers de cache expirés supprimés")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du cache: {e}")


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

    async def _store_response_safely(self, request_id: str, response: Any, client_id: Optional[str]):
        """Stocke la réponse de manière thread-safe - NOUVELLE MÉTHODE"""
        try:
            # Stockage thread-safe
            async with asyncio.Lock():  # Lock asyncio pour éviter les race conditions
                with self.lock:  # Lock threading pour compatibilité
                    self.response_store[request_id] = response

            # Notification du client si connecté
            if client_id and client_id in connected_clients:
                await self._notify_client_safely(client_id, {
                    "request_id": request_id,
                    "response": response,
                    "message": "Requête terminée avec succès"
                })

        except Exception as e:
            logger.error(f"Erreur lors du stockage de la réponse {request_id[:8]}...: {e}")

    async def _notify_client_safely(self, client_id: str, message: Dict):
        """Notifie un client de manière sécurisée - NOUVELLE MÉTHODE"""
        try:
            # Timeout très court pour éviter les blocages
            timeout = ClientTimeout(total=2)

            notify_url = f"http://{API_IP_ADDRESS}:{API_PORT}/send_message"
            data = {"client_id": client_id, "message": message}

            async with ClientSession(timeout=timeout) as session:
                try:
                    async with session.post(notify_url, json=data) as response:
                        if response.status == 200:
                            logger.debug(f"Client {client_id} notifié avec succès")
                        else:
                            logger.warning(f"Échec de notification du client {client_id}: {response.status}")
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout lors de la notification du client {client_id}")
                except Exception as e:
                    logger.warning(f"Erreur de notification du client {client_id}: {e}")

        except Exception as e:
            logger.error(f"Erreur critique lors de la notification du client {client_id}: {e}")

    async def _check_cache(self, request_data: RequestData) -> Optional[Any]:
        """Vérifie si une réponse en cache est disponible"""
        try:
            cache_key = self._generate_cache_key(request_data)
            cache_path = self.get_cache_path(cache_key)

            if os.path.exists(cache_path):
                with open(cache_path, 'r') as cache_file:
                    cached_data = json.load(cache_file)

                if time.time() - cached_data['timestamp'] < request_data.cache_duration:
                    logger.info(f"Cache hit pour la requête {request_data.request_id[:8]}...")
                    return cached_data['response']

        except Exception as e:
            logger.warning(f"Erreur lors de la vérification du cache: {e}")

        return None

    def _generate_cache_key(self, request_data: RequestData) -> str:
        """Génère une clé de cache unique"""
        key_components = [
            request_data.url,
            str(request_data.payload) if request_data.payload else '',
            str(request_data.method),
            str(request_data.headers),
            str(request_data.request_kwargs)
        ]
        return '|'.join(key_components)

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
            print(
                f"🔍 Request {request_id[:8]}... - in_queue: {in_queue}, has_response: {has_response}, result: {result}")
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
        api_patterns = request.args.getlist("api_patterns")
    else:
        data = request.json
        api_patterns = data.get("api_patterns")

    if not api_patterns:
        return jsonify({"error": "api_patterns are required"}), 400

    # Validation des URLs
    for url in api_patterns:
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return jsonify({"error": f"URL invalide: {url}"}), 400
        except Exception:
            return jsonify({"error": f"URL invalide: {url}"}), 400

    # scheduler_id = str(uuid.uuid4())
    scheduler = APIRequestScheduler(api_patterns)
    scheduler_id = scheduler.scheduler_id
    schedulers[scheduler_id] = scheduler
    scheduler_ids[tuple(sorted(api_patterns))] = scheduler_id

    # ✅ CORRECTION 9: Ne plus démarrer un thread supplémentaire ici
    # Le worker est déjà démarré dans __init__
    print(f"🚀 Scheduler {scheduler_id[:8]}... initialized for URLs: {api_patterns}")

    return jsonify({"message": "Manager initialized for the given API URLs.", "scheduler_id": scheduler_id})



@app.route("/api/scheduler/<scheduler_id>/stats", methods=["GET"])
@authenticate
def get_scheduler_stats_bis(scheduler_id: str):
    """Récupère les statistiques détaillées d'un scheduler"""
    try:
        if scheduler_id not in schedulers:
            return jsonify({"error": "Scheduler non trouvé"}), 404

        scheduler = schedulers[scheduler_id]
        stats = scheduler.get_stats()

        # Ajouter des informations supplémentaires
        stats.update({
            "api_patterns": scheduler.api_patterns,
            "cache_directory": scheduler.cache_dir,
            "thread_alive": scheduler.worker_thread.is_alive() if hasattr(scheduler, 'worker_thread') else False
        })

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stats: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


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
    old_limit = scheduler.CALLS_PER_SECOND
    scheduler.set_rate_limit(limit)

    logger.info(f"Limite de taux mise à jour pour {scheduler_id[:8]}...: {old_limit} -> {limit}")

    return jsonify({
        "message": "Limite de taux mise à jour",
        "scheduler_id": scheduler_id,
        "old_limit": old_limit,
        "new_limit": limit
    })


def get_request_param(request_obj, param_name: str):
    """Utilitaire pour récupérer un paramètre depuis GET ou POST"""
    try:
        # Essayer depuis les args (GET)
        param = request_obj.args.get(param_name)

        # Si pas trouvé et méthode POST, essayer depuis JSON
        if param is None and request_obj.method == "POST":
            data = request_obj.get_json()
            if data:
                param = data.get(param_name)

        return param
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du paramètre {param_name}: {e}")
        return None


@app.route("/api/request", methods=["POST", "GET"])
@authenticate
def api_request():
    """Ajoute une requête à la queue d'un scheduler"""
    try:
        # Récupération des paramètres de base
        scheduler_id = get_request_param(request, "scheduler_id")
        client_id = get_request_param(request, "client_id")
        url = get_request_param(request, "url")

        if not scheduler_id:
            return jsonify({"error": "scheduler_id requis"}), 400

        if scheduler_id not in schedulers:
            return jsonify({"error": "Scheduler non trouvé"}), 404

        if not url:
            return jsonify({"error": "URL requise"}), 400

        if not scheduler_id or scheduler_id not in schedulers:
            return jsonify({"error": "Scheduler not found for the given ID."}), 404

        scheduler = schedulers[scheduler_id]
        client_id = get_request_param(request, "client_id")
        url = get_request_param(request, "url")

        # Paramètres spécifiques selon la méthode HTTP
        if request.method == "POST":
            data = request.get_json() or {}
            headers = data.get("headers", {})
            payload = data.get("payload", None)
            cache_duration = data.get("cache_duration", 0)
            api_method = data.get("method", "POST").upper()  # Default to POST for Web API
            request_kwargs = data.get("request_kwargs", {})
        elif request.method == "GET":
            try:
                headers = request.args.get("headers", None) if request.args.get("headers", None) else (request.json.get("headers", None) if request.json else {})
                cache_duration = int(request.args.get("cache_duration", type=int, default=0) or (request.json.get("cache_duration", 0) if request.json else 0))
                api_method = request.args.get("method", "GET") or (request.json.get("method", "GET") if request.json else "GET")
                # api_method = api_method.upper()
                request_kwargs = {}  # Assume no additional kwargs for GET requests
                payload = None  # GET requests usually don't have a payload
            except json.JSONDecodeError:
                headers = {}

        if not url:
            return jsonify({"error": "URL is required."}), 400
        # Validation du cache_duration
        if cache_duration < 0:
            cache_duration = 0

        # Validation de la méthode HTTP
        if api_method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
            return jsonify({"error": f"Méthode HTTP non supportée: {api_method}"}), 400

        # Ajout de la requête
        request_id, estimated_delay = scheduler.add_request(
            url=url,
            payload=payload,
            cache_duration=cache_duration,
            method=api_method,
            client_id=client_id,
            headers=headers,
            **request_kwargs
        )

        response_data = {
            "uuid": request_id,
            "request_id": request_id,
            "status_url": f"/api/status/{request_id}",
            "estimated_delay": estimated_delay,
            "message": "Your request is in the queue. Use the provided URL to check the status."
        }

        logger.info(f"Requête {request_id[:8]}... ajoutée - Délai: {estimated_delay:.1f}s")
        logger.debug(f"URL soumise {url}")
        return jsonify(response_data)

    except RateLimitExceeded as e:
        logger.warning(f"Limite de taux dépassée: {e}")
        return jsonify({"error": "Queue pleine, réessayez plus tard"}), 429

    except ValueError as e:
        logger.warning(f"Erreur de validation: {e}")
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        logger.error(f"Erreur lors de l'ajout de la requête: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

@app.route("/api/status/<request_id>", methods=["GET"])
@authenticate
def api_status(request_id):
    """Vérifie le statut d'une requête avec logging amélioré"""
    found_request = False
    try:
        if not request_id:
            return jsonify({"error": "request_id requis"}), 400

        # ✅ AMÉLIORATION - Logging de debug
        logger.debug(f"Vérification statut pour {request_id}...")
        # Rechercher la requête dans tous les schedulers
        found_scheduler = None
        for scheduler_id, scheduler in schedulers.items():
            if scheduler.has_request(request_id):
                found_scheduler = scheduler
                found_request = True
                logger.debug(f"Requête {request_id}... trouvée dans scheduler {found_scheduler}")
                break

        if not found_scheduler:
            logger.warning(f"Requête {request_id}... non trouvée, dans aucun scheduler")
            return jsonify({"error": f"Request ID not found: {request_id}"}), 404

        # Vérifier si la réponse est prête
        response = found_scheduler.get_response(request_id)
        if response is not None:
            logger.info(f"✅ Response ready for {request_id[:8]}...")
            return jsonify({"status": "complete",
                            "response": response,
                            "request_id": request_id
                            })
        else:
            # Requête encore en traitement
            stats = found_scheduler.get_stats()
            return jsonify({
                "status": "pending",
                "message": "Requête en cours de traitement",
                "request_id": request_id,
                "queue_size": stats["queue_size"],
                "estimated_delay": stats["queue_size"] * (1 / stats["calls_per_second"])
            })
            logger.debug(f"⏳ Request {request_id[:8]}... still pending...")
            return jsonify({"scheduler_id": scheduler_id, "request_id": request_id, "status": "pending",
                            "message": "Your request is still being processed."})

    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut de {request_id[:8]}...: {e}")
        return jsonify({"error": f"Erreur interne du serveur {str(e)}"}), 500

@app.route("/api/openstatus", methods=["GET"])
def api_openstatus():
    """Statut ouvert pour debug avec informations détaillées"""
    try:
        status_data = {
            "status": "API Manager Status, request ids",
            "timestamp": datetime.now().isoformat(),
            "schedulers_count": str(len(schedulers)),
            "connected_clients": len(connected_clients),
            "schedulers": [],
            "requestIds": []
        }

        for scheduler_id, scheduler in schedulers.items():
            stats = scheduler.get_stats()

            # ✅ AMÉLIORATION - Plus de détails de debug
            with scheduler.lock:
                pending_request_details = []
                for req_id, req_data in list(scheduler.request_dict.items())[:10]:  # Limiter à 10
                    pending_request_details.append({
                        "id": req_id, #req_id[:8] + "...",
                        "url": req_data.url,
                        "timestamp": req_data.timestamp,
                        "age_seconds": time.time() - req_data.timestamp,
                        "has_response": req_id in scheduler.response_store
                    })

                # response_ids = [resp_id[:8] + "..." for resp_id in list(scheduler.response_store.keys())[:10]]
                response_ids = [resp_id  for resp_id in list(scheduler.response_store.keys())]

            scheduler_info = {
                "scheduler_id": scheduler_id, #[:12] + "...",
                "stats": stats,
                "pending_request_details": pending_request_details,
                "ready_response_ids": response_ids,
                "worker_thread_alive": scheduler.worker_thread.is_alive() if hasattr(scheduler,
                                                                                     'worker_thread') else False
            }
            status_data["schedulers"].append(scheduler_info)
            status_data["requestIds"].append(scheduler_info)
        return jsonify(status_data)
    except Exception as e:
        logger.error(f"Erreur dans l'interrogation du statut: {e}")
        return jsonify({"error": f"Erreur lors de la récupération du statut{str(e)}"}), 500



@app.route("/api/scheduler/<scheduler_id>/stats", methods=["GET"])
@authenticate
def get_scheduler_stats(scheduler_id: str):
    """Récupère les statistiques détaillées d'un scheduler"""
    try:
        if scheduler_id not in schedulers:
            return jsonify({"error": "Scheduler non trouvé"}), 404

        scheduler = schedulers[scheduler_id]
        stats = scheduler.get_stats()

        # Ajouter des informations supplémentaires
        stats.update({
            "api_patterns": scheduler.api_patterns,
            "cache_directory": scheduler.cache_dir,
            "thread_alive": scheduler.worker_thread.is_alive() if hasattr(scheduler, 'worker_thread') else False
        })

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des stats: {e}")
        return jsonify({"error": f"Erreur interne du serveur {str(e)}"}), 500


@app.route("/api/delete_scheduler", methods=["DELETE"])
@authenticate
def delete_scheduler():
    """Supprime un scheduler"""
    try:
        scheduler_id = request.args.get("scheduler_id")

        if not scheduler_id:
            return jsonify({"error": "scheduler_id requis"}), 400

        if scheduler_id not in schedulers:
            return jsonify({"error": "Scheduler non trouvé"}), 404

        # scheduler = schedulers[scheduler_id]

        # Nettoyage du scheduler
        # TODO vérifier si il faut ça scheduler.cleanup()

        # Supprimer le scheduler de la liste
        del schedulers[scheduler_id]

        # Supprimer l'association des URL associées à cet ID
        for key, value in list(scheduler_ids.items()):
            if value == scheduler_id:
                del scheduler_ids[key]
                break
        logger.info(f"Scheduler {scheduler_id[:8]}... supprimé avec succès")

        return jsonify({
            "message": f"scheduler with ID {scheduler_id} deleted successfully",
            "scheduler_id": scheduler_id
        })

    except Exception as e:
        logger.error(f"Erreur lors de la suppression du scheduler: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Endpoint de santé pour monitoring"""
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "schedulers_active": len(schedulers),
            "connected_clients": len(connected_clients),
            "uptime_seconds": time.time() - start_time if 'start_time' in globals() else 0
        }

        return jsonify(health_data)

    except Exception as e:
        logger.error(f"Erreur dans le health check: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    """Page d'accueil avec informations sur l'API"""
    try:
        html_content = f"""
        <html>
        <head>
            <title>API Manager - Gestionnaire de requêtes</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                h1 {{ color: #333; }}
                .stats {{ background: #e8f4f8; padding: 15px; border-radius: 4px; margin: 20px 0; }}
                .endpoint {{ background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 4px; }}
                code {{ background: #e8e8e8; padding: 2px 4px; border-radius: 2px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 API Manager v2.0</h1>
                <p>Gestionnaire de requêtes API avec limitation de taux, cache et WebSocket</p>
                
                <div class="stats">
                    <h3>📊 Statistiques actuelles</h3>
                    <p><strong>Schedulers actifs:</strong> {len(schedulers)}</p>
                    <p><strong>Clients connectés:</strong> {len(connected_clients)}</p>
                    <p><strong>Uptime:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <h3>🔗 Endpoints principaux</h3>
                <div class="endpoint">
                    <strong>POST /api/initialize</strong> - Initialiser un scheduler
                </div>
                <div class="endpoint">
                    <strong>POST /api/request</strong> - Ajouter une requête
                </div>
                <div class="endpoint">
                    <strong>GET /api/status/&lt;id&gt;</strong> - Vérifier le statut
                </div>
                <div class="endpoint">
                    <strong>GET /api/health</strong> - Health check
                </div>
                
                <h3>🔧 Fonctionnalités</h3>
                <ul>
                    <li>✅ Limitation de taux configurable</li>
                    <li>✅ Cache avec TTL</li>
                    <li>✅ Retry automatique avec backoff</li>
                    <li>✅ WebSocket pour notifications temps réel</li>
                    <li>✅ Logging structuré</li>
                    <li>✅ Gestion d'erreurs robuste</li>
                    <li>✅ Monitoring et métriques</li>
                </ul>
            </div>
        </body>
        </html>
        """
        return html_content

    except Exception as e:
        logger.error(f"Erreur dans la page d'accueil: {e}")
        return "<h1>Erreur</h1><p>Erreur lors du chargement de la page d'accueil</p>", 500


# Gestionnaires d'erreurs globaux
@app.errorhandler(404)
def not_found(error):
    """Gestionnaire d'erreur 404"""
    return jsonify({"error": "Endpoint non trouvé"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Gestionnaire d'erreur 405"""
    return jsonify({"error": "Méthode HTTP non autorisée"}), 405


@app.errorhandler(500)
def internal_error(error):
    """Gestionnaire d'erreur 500"""
    logger.error(f"Erreur interne du serveur: {error}")
    return jsonify({"error": "Erreur interne du serveur"}), 500


# Nettoyage à l'arrêt

def cleanup_on_shutdown():
    """Nettoie les ressources à l'arrêt"""
    logger.info("Arrêt de l'application - nettoyage en cours...")

    # Nettoyer les schedulers
    for scheduler_id, scheduler in list(schedulers.items()):
        try:
            scheduler.cleanup()
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du scheduler {scheduler_id}: {e}")

    logger.info("Nettoyage terminé")

# Enregistrement du nettoyage
atexit.register(cleanup_on_shutdown)

# Variables globales pour le monitoring
start_time = time.time()

if __name__ == "__main__":
    try:
        logger.info(f"Démarrage de l'API Manager sur {API_IP_ADDRESS}:{API_PORT}")
        logger.info(f"Niveau de log: {LOG_LEVEL}")
        logger.info(f"Configuration: Timeout={REQUEST_TIMEOUT}s, Max retries={MAX_RETRIES}")

        # ✅ CORRECTION: Configuration plus robuste pour les tests
        socketio.run(
            app,
            host=API_IP_ADDRESS,
            port=API_PORT,
            debug=False,
            use_reloader=False,  # Évite les problèmes avec les threads
            allow_unsafe_werkzeug=True,  # Pour compatibilité tests
            log_output=True if LOG_LEVEL == 'DEBUG' else False
        )

    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale lors du démarrage: {e}")
        raise
    finally:
        cleanup_on_shutdown()