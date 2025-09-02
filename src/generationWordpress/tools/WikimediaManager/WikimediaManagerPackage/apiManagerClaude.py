import re
import threading
import sys
import asyncio
import json
import os
import time
import uuid
from functools import wraps
from queue import Queue, Empty
from urllib.parse import urlparse
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional, Tuple, List
import requests
from aiohttp import ClientSession, ClientTimeout, ClientError
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import signal
import atexit
from datetime import datetime, timedelta

from configPrivee import config

# Configuration
API_IP_ADDRESS = "127.0.0.1"
API_PORT = 6000
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
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
    _instances: Dict[Tuple, 'APIRequestScheduler'] = {}
    _lock = threading.Lock()

    def __new__(cls, api_patterns: List[str], *args, **kwargs):
        key = tuple(sorted(api_patterns))
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = super(APIRequestScheduler, cls).__new__(cls)
        return cls._instances[key]

    def __init__(self, api_patterns: List[str]):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.api_patterns = api_patterns
        self.scheduler_id = str(uuid.uuid4())
        self.CALLS_PER_SECOND = 1
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND
        
        # Queues et stockage
        self.request_queue = Queue(maxsize=MAX_QUEUE_SIZE)
        self.response_store: Dict[str, Any] = {}
        self.request_dict: Dict[str, RequestData] = {}
        
        # Configuration du cache
        self.cache_dir = os.path.join(os.getcwd(), 'cache')
        self._ensure_cache_directory()
        
        # Threading et async
        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()
        
        # Initialisation des threads
        self._start_worker_threads()
        self._start_cache_cleanup_thread()
        
        # Enregistrement des handlers de fermeture
        atexit.register(self.cleanup)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self._initialized = True
        logger.info(f"APIRequestScheduler initialisé pour {len(api_patterns)} URLs - ID: {self.scheduler_id}")

    def _ensure_cache_directory(self):
        """Crée le répertoire de cache s'il n'existe pas"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Erreur lors de la création du répertoire cache: {e}")
            raise APIError(f"Impossible de créer le répertoire cache: {e}")

    def _start_worker_threads(self):
        """Démarre les threads de traitement"""
        try:
            # Thread principal de traitement
            self.worker_thread = threading.Thread(
                target=self._worker_wrapper,
                name=f"APIWorker-{self.scheduler_id[:8]}",
                daemon=True
            )
            self.worker_thread.start()
            
            # Event loop asyncio
            self.loop = asyncio.new_event_loop()
            self.loop_thread = threading.Thread(
                target=self._start_event_loop,
                name=f"EventLoop-{self.scheduler_id[:8]}",
                daemon=True
            )
            self.loop_thread.start()
            
            logger.info("Threads de traitement démarrés avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage des threads: {e}")
            raise APIError(f"Impossible de démarrer les threads: {e}")

    def _start_cache_cleanup_thread(self):
        """Démarre le thread de nettoyage du cache"""
        def cleanup_cache():
            while not self.shutdown_event.is_set():
                try:
                    self._cleanup_expired_cache()
                    self.shutdown_event.wait(CACHE_CLEANUP_INTERVAL)
                except Exception as e:
                    logger.error(f"Erreur lors du nettoyage du cache: {e}")
        
        cleanup_thread = threading.Thread(
            target=cleanup_cache,
            name=f"CacheCleanup-{self.scheduler_id[:8]}",
            daemon=True
        )
        cleanup_thread.start()

    def _signal_handler(self, signum, frame):
        """Gestionnaire de signaux pour un arrêt propre"""
        logger.info(f"Signal {signum} reçu, arrêt en cours...")
        self.cleanup()

    def _worker_wrapper(self):
        """Wrapper pour le worker asyncio"""
        try:
            asyncio.run(self._process_queue())
        except Exception as e:
            logger.error(f"Erreur critique dans le worker: {e}")

    def _start_event_loop(self):
        """Démarre la boucle d'événements asyncio"""
        try:
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"Erreur dans la boucle d'événements: {e}")

    def set_rate_limit(self, calls_per_second: float):
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

    async def _process_queue(self):
        """Traite les requêtes de la queue de manière asynchrone"""
        logger.info("Démarrage du processus de traitement de la queue")
        
        while not self.shutdown_event.is_set():
            try:
                # Récupère une requête avec timeout
                try:
                    request_data = self.request_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                if request_data is None:
                    break
                
                await self._perform_request(request_data)
                self.request_queue.task_done()
                
            except Exception as e:
                logger.error(f"Erreur dans le traitement de la queue: {e}")

    async def _perform_request(self, request_data: RequestData):
        """Effectue une requête HTTP avec gestion d'erreurs et retry"""
        request_id = request_data.request_id
        logger.info(f"Traitement de la requête {request_id[:8]}... - URL: {request_data.url}")
        
        try:
            # Vérification du cache
            if request_data.cache_duration > 0:
                cached_response = await self._check_cache(request_data)
                if cached_response:
                    await self._store_response(request_id, cached_response, request_data.client_id)
                    return

            # Respect de la limite de taux
            await asyncio.sleep(self.CALL_INTERVAL)
            
            # Effectuer la requête HTTP
            response = await self._make_http_request(request_data)
            
            # Cache et stockage de la réponse
            if request_data.cache_duration > 0:
                await self._cache_response(request_data, response)
            
            await self._store_response(request_id, response, request_data.client_id)
            logger.info(f"Requête {request_id[:8]}... traitée avec succès")
            
        except Exception as e:
            await self._handle_request_error(request_data, e)
        finally:
            # Nettoyer la requête du dictionnaire
            with self.lock:
                self.request_dict.pop(request_id, None)

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

    async def _make_http_request(self, request_data: RequestData) -> Any:
        """Effectue la requête HTTP avec retry automatique"""
        timeout = ClientTimeout(total=REQUEST_TIMEOUT)
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                async with ClientSession(timeout=timeout) as session:
                    method = request_data.method.upper()
                    
                    # Préparation des paramètres de requête
                    request_params = {
                        'headers': request_data.headers,
                        **request_data.request_kwargs
                    }
                    
                    if method in ['POST', 'PUT', 'PATCH']:
                        request_params['json'] = request_data.payload
                    elif method == 'GET':
                        request_params['params'] = request_data.payload
                    
                    # Effectuer la requête
                    async with session.request(method, request_data.url, **request_params) as response:
                        response.raise_for_status()
                        
                        # Tentative de parsing JSON
                        try:
                            return await response.json()
                        except:
                            return await response.text()
                            
            except asyncio.TimeoutError:
                error_msg = f"Timeout lors de la requête (tentative {attempt + 1}/{MAX_RETRIES + 1})"
                logger.warning(f"{error_msg} - {request_data.request_id[:8]}...")
                
                if attempt == MAX_RETRIES:
                    raise APIError(f"Timeout après {MAX_RETRIES + 1} tentatives", 
                                 request_id=request_data.request_id)
                    
            except ClientError as e:
                error_msg = f"Erreur client HTTP: {str(e)} (tentative {attempt + 1}/{MAX_RETRIES + 1})"
                logger.warning(f"{error_msg} - {request_data.request_id[:8]}...")
                
                # Ne pas retry sur certaines erreurs client (4xx)
                if hasattr(e, 'status') and 400 <= e.status < 500:
                    raise APIError(f"Erreur client HTTP {e.status}: {str(e)}", 
                                 status_code=e.status, request_id=request_data.request_id)
                
                if attempt == MAX_RETRIES:
                    raise APIError(f"Erreur HTTP après {MAX_RETRIES + 1} tentatives: {str(e)}", 
                                 request_id=request_data.request_id)
            
            except Exception as e:
                error_msg = f"Erreur inattendue: {str(e)} (tentative {attempt + 1}/{MAX_RETRIES + 1})"
                logger.error(f"{error_msg} - {request_data.request_id[:8]}...")
                
                if attempt == MAX_RETRIES:
                    raise APIError(f"Erreur après {MAX_RETRIES + 1} tentatives: {str(e)}", 
                                 request_id=request_data.request_id)
            
            # Attente avant retry avec backoff exponentiel
            if attempt < MAX_RETRIES:
                wait_time = RETRY_BACKOFF_FACTOR ** attempt
                logger.info(f"Attente de {wait_time}s avant retry - {request_data.request_id[:8]}...")
                await asyncio.sleep(wait_time)

    async def _cache_response(self, request_data: RequestData, response: Any):
        """Met en cache la réponse"""
        try:
            cache_key = self._generate_cache_key(request_data)
            cache_path = self.get_cache_path(cache_key)
            
            cache_data = {
                'response': response,
                'timestamp': time.time(),
                'request_id': request_data.request_id
            }
            
            with open(cache_path, 'w') as cache_file:
                json.dump(cache_data, cache_file, default=str)
                
            logger.debug(f"Réponse mise en cache: {request_data.request_id[:8]}...")
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache: {e}")

    async def _store_response(self, request_id: str, response: Any, client_id: Optional[str]):
        """Stocke la réponse et notifie le client si nécessaire"""
        with self.lock:
            self.response_store[request_id] = response

        # Notification du client WebSocket
        if client_id and client_id in connected_clients:
            await self._notify_client(client_id, {
                "request_id": request_id,
                "response": response,
                "message": "Requête terminée avec succès"
            })

    async def _handle_request_error(self, request_data: RequestData, error: Exception):
        """Gère les erreurs de requête"""
        request_id = request_data.request_id
        error_response = {
            "error": str(error),
            "request_id": request_id,
            "timestamp": time.time(),
            "url": request_data.url
        }
        
        # Ajout d'informations spécifiques selon le type d'erreur
        if isinstance(error, APIError):
            error_response["status_code"] = error.status_code
            
        logger.error(f"Erreur lors du traitement de la requête {request_id[:8]}...: {str(error)}")
        
        # Stockage de l'erreur
        with self.lock:
            self.response_store[request_id] = error_response

        # Notification du client
        if request_data.client_id and request_data.client_id in connected_clients:
            await self._notify_client(request_data.client_id, {
                "request_id": request_id,
                "error": str(error),
                "message": "Erreur lors du traitement de la requête"
            })

    async def _notify_client(self, client_id: str, message: Dict):
        """Notifie un client via WebSocket"""
        try:
            notify_url = f"http://{API_IP_ADDRESS}:{API_PORT}/send_message"
            data = {"client_id": client_id, "message": message}
            
            # Utiliser asyncio pour l'appel HTTP
            timeout = ClientTimeout(total=5)
            async with ClientSession(timeout=timeout) as session:
                async with session.post(notify_url, json=data) as response:
                    if response.status == 200:
                        logger.debug(f"Client {client_id} notifié avec succès")
                    else:
                        logger.warning(f"Échec de notification du client {client_id}: {response.status}")
                        
        except Exception as e:
            logger.error(f"Erreur lors de la notification du client {client_id}: {e}")

    def validate_url(self, base_url):
        for pattern in self.api_patterns:
            if not any(char in pattern.pattern for char in r'.*+?^${}[]|()\\'):
                # URL exacte
                if base_url == pattern:
                    return True
            else:
                # Pattern regex
                if re.match(pattern, base_url):
                    return True
        return False

    def add_request(self, url: str, payload: Optional[Dict] = None, 
                   cache_duration: int = 0, method: str = "POST", 
                   client_id: Optional[str] = None, headers: Optional[Dict] = None,
                   **request_kwargs) -> Tuple[str, float]:
        """Ajoute une requête à la queue"""
        try:
            # Validation de l'URL
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
            
            if not self.validate_url(base_url):
                raise ValueError(f"URL non gérée par cette instance: {base_url}")

            # Vérification de la capacité de la queue
            if self.request_queue.qsize() >= MAX_QUEUE_SIZE:
                raise RateLimitExceeded("Queue pleine, requête rejetée")

            # Création de la requête
            request_id = str(uuid.uuid4())
            request_data = RequestData(
                request_id=request_id,
                url=url,
                payload=payload,
                method=method.upper(),
                headers=headers or {},
                cache_duration=cache_duration,
                request_kwargs=request_kwargs,
                client_id=client_id
            )

            # Ajout à la queue et au dictionnaire de suivi
            self.request_queue.put(request_data)
            
            with self.lock:
                self.request_dict[request_id] = request_data

            estimated_delay = self.request_queue.qsize() * self.CALL_INTERVAL
            
            logger.info(f"Requête {request_id[:8]}... ajoutée à la queue - Délai estimé: {estimated_delay:.1f}s")
            return request_id, estimated_delay
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la requête: {e}")
            raise

    def get_response(self, request_id: str) -> Optional[Any]:
        """Récupère la réponse d'une requête"""
        with self.lock:
            response = self.response_store.pop(request_id, None)
            if response:
                logger.debug(f"Réponse récupérée pour {request_id[:8]}...")
            return response

    def has_request(self, request_id: str) -> bool:
        """Vérifie si une requête existe (en cours OU terminée mais non récupérée)"""
        with self.lock:
            # Vérifier à la fois dans request_dict ET response_store
            in_pending = request_id in self.request_dict
            in_responses = request_id in self.response_store

            # Log de debug (à supprimer en production)
            if not (in_pending or in_responses):
                logger.debug(
                    f"Request {request_id[:8]}... not found - pending: {in_pending}, responses: {in_responses}")

            return in_pending or in_responses

    def get_stats(self) -> Dict:
        """Retourne les statistiques du scheduler"""
        with self.lock:
            return {
                "scheduler_id": self.scheduler_id,
                "queue_size": self.request_queue.qsize(),
                "pending_requests": len(self.request_dict),
                "pending_responses": len(self.response_store),
                "calls_per_second": self.CALLS_PER_SECOND,
                "managed_urls": len(self.api_patterns)
            }

    def cleanup(self):
        """Nettoie les ressources"""
        logger.info(f"Nettoyage du scheduler {self.scheduler_id[:8]}...")
        
        self.shutdown_event.set()
        
        # Arrêt de la boucle d'événements
        if hasattr(self, 'loop') and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        # Attendre que les threads se terminent
        if hasattr(self, 'worker_thread') and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        
        if hasattr(self, 'loop_thread') and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=5)
        
        logger.info("Nettoyage terminé")


# Décorateur d'authentification amélioré
def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_token = request.headers.get("Authorization")
            bearer = config.get('admin', {}).get('Bearer')
            
            if not bearer:
                logger.error("Token Bearer non configuré")
                return jsonify({"error": "Configuration d'authentification manquante"}), 500
            
            if not auth_token:
                logger.warning("Tentative d'accès sans token d'authentification")
                return jsonify({"error": "Token d'authentification requis"}), 401
            
            if auth_token != f"Bearer {bearer}":
                logger.warning(f"Tentative d'accès avec token invalide: {auth_token[:20]}...")
                return jsonify({"error": "Token d'authentification invalide"}), 401
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Erreur dans l'authentification: {e}")
            return jsonify({"error": "Erreur d'authentification"}), 500

    return decorated_function


# Configuration Flask-SocketIO avec gestion d'erreurs
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*", logger=True, engineio_logger=True)

# Stockage des clients connectés
connected_clients: Dict[str, str] = {}

# Gestionnaires WebSocket améliorés
@socketio.on('custom_event')
def handle_custom_event():
    """Gestionnaire d'événement personnalisé pour test"""
    try:
        emit('custom_event', {"message": "Custom event reçu avec succès"})
        logger.info("Événement personnalisé traité")
    except Exception as e:
        logger.error(f"Erreur dans handle_custom_event: {e}")
        emit('error', {"message": "Erreur lors du traitement de l'événement"})

@socketio.on('connect')
def handle_connect():
    """Gestionnaire de connexion WebSocket"""
    try:
        logger.info(f"Nouveau client connecté: {request.sid}")
        emit("connect", {"message": "Connexion établie avec succès", "sid": request.sid})
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {e}")

@socketio.on('register')
def handle_register(data):
    """Enregistre un client avec un client_id"""
    try:
        client_id = data.get('client_id')
        
        if not client_id:
            emit('error', {'message': 'client_id requis pour l\'enregistrement'})
            return
        
        # Vérifier si le client_id est déjà utilisé
        if client_id in connected_clients:
            logger.warning(f"Tentative d'enregistrement avec un client_id existant: {client_id}")
        
        connected_clients[client_id] = request.sid
        join_room(client_id)
        
        logger.info(f"Client enregistré - client_id: {client_id}, sid: {request.sid}")
        emit('message', {
            'data': f'Enregistrement réussi avec client_id: {client_id}',
            'client_id': client_id
        }, room=client_id)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du client: {e}")
        emit('error', {'message': 'Erreur lors de l\'enregistrement'})

@socketio.on('disconnect')
def handle_disconnect():
    """Gestionnaire de déconnexion WebSocket"""
    try:
        disconnected_client = None
        
        # Trouver et supprimer le client déconnecté
        for client_id, sid in list(connected_clients.items()):
            if sid == request.sid:
                disconnected_client = client_id
                del connected_clients[client_id]
                leave_room(client_id)
                break
        
        if disconnected_client:
            logger.info(f"Client déconnecté: {disconnected_client}")
        else:
            logger.info(f"Client déconnecté (non enregistré): {request.sid}")
            
    except Exception as e:
        logger.error(f"Erreur lors de la déconnexion: {e}")

# Routes API améliorées
@app.route('/send_message', methods=['POST'])
def send_message():
    """Envoie un message à un client spécifique via WebSocket"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Données JSON requises"}), 400
        
        client_id = data.get('client_id')
        message = data.get('message')
        
        if not client_id or not message:
            return jsonify({"error": "client_id et message requis"}), 400

        if client_id in connected_clients:
            socketio.emit('message', {'data': message}, room=client_id, namespace='/')
            logger.debug(f"Message envoyé au client {client_id}")
            return jsonify({"status": "Message envoyé", "client_id": client_id}), 200
        else:
            logger.warning(f"Tentative d'envoi de message à un client non trouvé: {client_id}")
            return jsonify({"error": "Client non trouvé"}), 404
            
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de message: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

# Gestionnaires de schedulers globaux
schedulers: Dict[str, APIRequestScheduler] = {}
scheduler_ids: Dict[Tuple, str] = {}

@app.route("/api/initialize", methods=["GET", "POST"])
@authenticate
def initialize_scheduler():
    """Initialise un nouveau scheduler d'API"""
    try:
        if request.method == "GET":
            api_patterns = request.args.getlist("api_patterns")
        else:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Données JSON requises"}), 400
            api_patterns = data.get("api_patterns", [])

        if not api_patterns or not isinstance(api_patterns, list):
            return jsonify({"error": "api_patterns requis (liste d'URLs)"}), 400

        # Validation des URLs
        for url in api_patterns:
            try:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    return jsonify({"error": f"URL invalide: {url}"}), 400
            except Exception:
                return jsonify({"error": f"URL invalide: {url}"}), 400

        # Vérifier si un scheduler existe déjà pour ces URLs
        key = tuple(sorted(api_patterns))
        if key in scheduler_ids:
            existing_id = scheduler_ids[key]
            logger.info(f"Scheduler existant trouvé pour ces URLs: {existing_id}")
            return jsonify({
                "message": "Scheduler existant trouvé",
                "scheduler_id": existing_id,
                "is_new": False
            })

        # Créer un nouveau scheduler
        scheduler = APIRequestScheduler(api_patterns)
        scheduler_id = scheduler.scheduler_id
        
        schedulers[scheduler_id] = scheduler
        scheduler_ids[key] = scheduler_id

        logger.info(f"Nouveau scheduler créé: {scheduler_id} pour {len(api_patterns)} URLs")
        
        return jsonify({
            "message": "Scheduler initialisé avec succès",
            "scheduler_id": scheduler_id,
            "managed_urls": len(api_patterns),
            "is_new": True
        })

    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du scheduler: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


@app.route("/api/set_rate_limit", methods=["POST"])
@authenticate
def set_rate_limit():
    """Configure la limite de taux pour un scheduler"""
    try:
        # Récupération des paramètres
        scheduler_id = request.args.get("scheduler_id")
        if not scheduler_id:
            data = request.get_json()
            if not data:
                return jsonify({"error": "scheduler_id requis"}), 400
            scheduler_id = data.get("scheduler_id")

        limit = request.args.get("limit", type=float)
        if limit is None:
            data = request.get_json()
            if data:
                limit = data.get("limit")

        # Validation
        if not scheduler_id:
            return jsonify({"error": "scheduler_id requis"}), 400
        
        if scheduler_id not in schedulers:
            return jsonify({"error": "Scheduler non trouvé"}), 404

        if not limit or limit <= 0:
            return jsonify({"error": "Limite valide requise (> 0)"}), 400

        # Mise à jour de la limite
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

    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de la limite: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


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

        scheduler = schedulers[scheduler_id]

        # Paramètres spécifiques selon la méthode HTTP
        if request.method == "POST":
            data = request.get_json() or {}
            headers = data.get("headers", {})
            payload = data.get("payload")
            cache_duration = data.get("cache_duration", 0)
            api_method = data.get("method", "POST").upper()
            request_kwargs = data.get("request_kwargs", {})
            
        else:  # GET
            try:
                headers_param = get_request_param(request, "headers")
                headers = json.loads(headers_param) if headers_param else {}
            except json.JSONDecodeError:
                headers = {}
                
            cache_duration = int(get_request_param(request, "cache_duration") or 0)
            api_method = (get_request_param(request, "method") or "GET").upper()
            request_kwargs = {}
            payload = None

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
            "status_url": f"/api/status/{request_id}",
            "estimated_delay": round(estimated_delay, 2),
            "queue_position": scheduler.request_queue.qsize(),
            "message": "Requête ajoutée à la queue avec succès"
        }

        logger.info(f"Requête {request_id[:8]}... ajoutée - Délai: {estimated_delay:.1f}s")
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
def api_status(request_id: str):
    """Vérifie le statut d'une requête"""
    try:
        if not request_id:
            return jsonify({"error": "request_id requis"}), 400

        # Rechercher la requête dans tous les schedulers
        found_scheduler = None
        for scheduler in schedulers.values():
            if scheduler.has_request(request_id):
                found_scheduler = scheduler
                break

        if not found_scheduler:
            # Vérifier si une réponse existe
            for scheduler in schedulers.values():
                response = scheduler.get_response(request_id)
                if response is not None:
                    logger.info(f"Réponse trouvée pour {request_id[:8]}...")
                    return jsonify({
                        "status": "complete",
                        "response": response,
                        "request_id": request_id
                    })
            
            return jsonify({"error": f"Requête non trouvée: {request_id}"}), 404

        # Vérifier si la réponse est prête
        response = found_scheduler.get_response(request_id)
        if response is not None:
            logger.info(f"Réponse récupérée pour {request_id[:8]}...")
            return jsonify({
                "status": "complete",
                "response": response,
                "request_id": request_id
            })

        # Requête encore en traitement
        stats = found_scheduler.get_stats()
        return jsonify({
            "status": "pending",
            "message": "Requête en cours de traitement",
            "request_id": request_id,
            "queue_size": stats["queue_size"],
            "estimated_delay": stats["queue_size"] * (1 / stats["calls_per_second"])
        })

    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut: {e}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


@app.route("/api/openstatus", methods=["GET"])
def api_openstatus():
    """Statut ouvert pour debug - liste des requêtes en cours"""
    try:
        status_data = {
            "status": "API Manager Status",
            "timestamp": datetime.now().isoformat(),
            "schedulers_count": len(schedulers),
            "connected_clients": len(connected_clients),
            "schedulers": []
        }

        for scheduler_id, scheduler in schedulers.items():
            stats = scheduler.get_stats()
            scheduler_info = {
                "scheduler_id": scheduler_id,
                "stats": stats,
                "pending_requests": list(scheduler.request_dict.keys())[:10]  # Limite pour éviter les réponses trop grandes
            }
            status_data["schedulers"].append(scheduler_info)

        return jsonify(status_data)
    
    except Exception as e:
        logger.error(f"Erreur dans l'interrogation du statut: {e}")
        return jsonify({"error": "Erreur lors de la récupération du statut"}), 500


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
        return jsonify({"error": "Erreur interne du serveur"}), 500


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

        scheduler = schedulers[scheduler_id]
        
        # Nettoyage du scheduler
        scheduler.cleanup()
        
        # Suppression des références
        del schedulers[scheduler_id]
        
        # Supprimer de scheduler_ids
        for key, value in list(scheduler_ids.items()):
            if value == scheduler_id:
                del scheduler_ids[key]
                break

        logger.info(f"Scheduler {scheduler_id[:8]}... supprimé avec succès")
        
        return jsonify({
            "message": f"Scheduler supprimé avec succès",
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
    
    for scheduler_id, scheduler in schedulers.items():
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
        
        # Démarrage du serveur
        socketio.run(
            app, 
            host=API_IP_ADDRESS, 
            port=API_PORT, 
            debug=False,
            use_reloader=False  # Évite les problèmes avec les threads
        )
        
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale lors du démarrage: {e}")
        raise
    finally:
        cleanup_on_shutdown()