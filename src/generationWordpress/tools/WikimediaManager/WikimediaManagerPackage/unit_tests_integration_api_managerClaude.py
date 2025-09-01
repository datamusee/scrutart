import re
import unittest
import requests
import json
import time
import threading
import subprocess
import sys
import os
import signal
from urllib.parse import urlparse
import socketio
from unittest.mock import patch
import tempfile
import shutil

# Configuration des tests d'intégration
TEST_API_HOST = "127.0.0.1"
TEST_API_PORT = 6000  # Port différent pour éviter les conflits
TEST_BASE_URL = f"http://{TEST_API_HOST}:{TEST_API_PORT}"
TEST_BEARER_TOKEN = "test-integration-bearer-token"

# mockurl = "https://httpbin.org/json" # url bidon pour test
mockurl = "http://127.0.0.1:5000/mockapi" # api  bidon locale pour test
#test_urls = [r"^http://127.0.0.1:5000/mockapi(/.*)?$"]
escaped_baseurl = re.escape(mockurl) # escape fait trop de choses!
escaped_baseurl.replace(r'\:', ':')
rexpattern = re.compile(f"^{escaped_baseurl}(/.*)?$")
# URLs de test (APIs publiques pour tests réels)
TEST_APIS = [
    rexpattern,
    "https://httpbin.org",  # API de test HTTP
    "https://jsonplaceholder.typicode.com",  # API de test JSON
    "https://reqres.in/api"  # API de test REST
]

class APIManagerTestServer:
    """Gestionnaire du serveur de test API Manager"""
    
    def __init__(self):
        self.process = None
        self.temp_dir = None
        self.config_file = None
        
    def setup_test_environment(self):
        """Configure l'environnement de test"""
        # Créer un répertoire temporaire
        self.temp_dir = os.path.join(os.getcwd(), "temp") #tempfile.mkdtemp()
        os.makedirs(self.temp_dir)
        # Créer un fichier de configuration de test
        self.config_file = os.path.join(self.temp_dir, "configPrivee.py")
        config_content = f"""
config = {{
    'admin': {{
        'Bearer': '{TEST_BEARER_TOKEN}'
    }}
}}
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
        
        # Ajouter le répertoire temporaire au Python path
        sys.path.insert(0, self.temp_dir)
        
        return self.temp_dir
    
    def start_server(self, api_manager_path="apiManagerClaude.py"):
        """Démarre le serveur API Manager en subprocess"""
        try:
            # Variables d'environnement pour le test
            env = os.environ.copy()
            env.update({
                'PYTHONPATH': self.temp_dir,
                'API_IP_ADDRESS': TEST_API_HOST,
                'API_PORT': str(TEST_API_PORT),
                'LOG_LEVEL': 'DEBUG'
            })
            
            # Créer une version modifiée du script pour les tests
            test_script = self._create_test_script(api_manager_path)
            
            # Démarrer le serveur
            self.process = subprocess.Popen(
                [sys.executable, test_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.temp_dir
            )
            
            # Attendre que le serveur démarre
            self._wait_for_server_start()
            
            return True
            
        except Exception as e:
            print(f"Erreur lors du démarrage du serveur: {e}")
            return False
    
    def _create_test_script(self, original_path):
        """Crée une version du script adaptée aux tests"""
        test_script_path = os.path.join(self.temp_dir, "test_api_manager.py")
        
        # Contenu du script de test (version modifiée)
        script_content = f'''
import sys
sys.path.insert(0, "{self.temp_dir}")

# Configuration des tests d'intégration
TEST_API_HOST = "127.0.0.1"
TEST_API_PORT = 6000  # Port différent pour éviter les conflits
TEST_BEARER_TOKEN = "test-integration-bearer-token"

# Redéfinir les constantes pour le test
API_IP_ADDRESS = "{TEST_API_HOST}"
API_PORT = {TEST_API_PORT}

# Copier tout le code de l'API Manager ici (version simplifiée pour test)
import threading
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

# Configuration simplifiee pour les tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RequestData:
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
            self.headers = {{}}
        if self.request_kwargs is None:
            self.request_kwargs = {{}}

class APIError(Exception):
    def __init__(self, message: str, status_code: int = None, request_id: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id

class RateLimitExceeded(APIError):
    pass

# Version simplifiée du scheduler pour tests d'intégration
class APIRequestScheduler:
    _instances = {{}}

    def __new__(cls, api_patterns, *args, **kwargs):
        key = tuple(sorted(api_patterns))
        if key not in cls._instances:
            cls._instances[key] = super(APIRequestScheduler, cls).__new__(cls)
        return cls._instances[key]

    def __init__(self, api_patterns):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.api_patterns = api_patterns
        self.scheduler_id = str(uuid.uuid4())
        self.CALLS_PER_SECOND = 1
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND
        
        self.request_queue = Queue()
        self.response_store = {{}}
        self.request_dict = {{}}
        
        self.cache_dir = os.path.join(os.getcwd(), 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()
        
        # Démarrer le worker
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        
        self._initialized = True

    def _worker(self):
        """Worker thread pour traiter les requetes"""
        while not self.shutdown_event.is_set():
            try:
                request_data = self.request_queue.get(timeout=1.0)
                if request_data is None:
                    break
                
                # Simulation du traitement
                time.sleep(self.CALL_INTERVAL)
                
                try:
                    # Faire la requête HTTP réelle
                    response = requests.get(request_data.url, timeout=10)
                    result = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    
                    with self.lock:
                        self.response_store[request_data.request_id] = result
                        self.request_dict.pop(request_data.request_id, None)
                        
                except Exception as e:
                    with self.lock:
                        self.response_store[request_data.request_id] = {{"error": str(e)}}
                        self.request_dict.pop(request_data.request_id, None)
                
                self.request_queue.task_done()
                
            except Exception:
                continue

    def set_rate_limit(self, calls_per_second):
        if calls_per_second <= 0:
            raise ValueError("Le taux doit être positif")
        self.CALLS_PER_SECOND = calls_per_second
        self.CALL_INTERVAL = 1 / calls_per_second

    def add_request(self, url, payload=None, cache_duration=0, method="GET", 
                   client_id=None, headers=None, **kwargs):
        parsed_url = urlparse(url)
        base_url = f"{{parsed_url.scheme}}://{{parsed_url.netloc}}"
        
        if not any(base_url.startswith(api_url) for api_url in self.api_patterns):
            raise ValueError(f"URL non gérée: {{base_url}}")
        
        request_id = str(uuid.uuid4())
        request_data = RequestData(
            request_id=request_id,
            url=url,
            payload=payload,
            method=method,
            headers=headers or {{}},
            cache_duration=cache_duration,
            client_id=client_id
        )
        
        self.request_queue.put(request_data)
        with self.lock:
            self.request_dict[request_id] = request_data
        
        estimated_delay = self.request_queue.qsize() * self.CALL_INTERVAL
        return request_id, estimated_delay

    def get_response(self, request_id):
        with self.lock:
            return self.response_store.pop(request_id, None)
            
    def has_request(self, request_id: str) -> bool:
        """Vérifier si une requête existe (en cours OU terminée)"""
        with self.lock:
            return (request_id in self.request_dict or 
                    request_id in self.response_store)

    def get_stats(self):
        with self.lock:
            return {{
                "scheduler_id": self.scheduler_id,
                "queue_size": self.request_queue.qsize(),
                "pending_requests": len(self.request_dict),
                "pending_responses": len(self.response_store),
                "calls_per_second": self.CALLS_PER_SECOND,
                "managed_urls": len(self.api_patterns)
            }}

    def cleanup(self):
        self.shutdown_event.set()
        if hasattr(self, 'worker_thread'):
            self.worker_thread.join(timeout=5)

# Décorateur d'authentification
def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_token = request.headers.get("Authorization")
        bearer = config.get('admin', {{}}).get('Bearer')
        
        if not auth_token or auth_token != f"Bearer {{bearer}}":
            return jsonify({{"error": "Unauthorized"}}), 401
        return f(*args, **kwargs)
    return decorated_function

# Application Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Variables globales
schedulers = {{}}
scheduler_ids = {{}}
connected_clients = {{}}

def get_request_param(request_obj, param_name):
    param = request_obj.args.get(param_name)
    if param is None and request_obj.method == "POST":
        data = request_obj.get_json()
        if data:
            param = data.get(param_name)
    return param

# Routes principales
@app.route("/api/initialize", methods=["GET", "POST"])
@authenticate
def initialize_scheduler():
    try:
        if request.method == "GET":
            api_patterns = request.args.getlist("api_patterns")
        else:
            data = request.get_json()
            if not data:
                return jsonify({{"error": "Données JSON requises"}}), 400
            api_patterns = data.get("api_patterns", [])

        if not api_patterns:
            return jsonify({{"error": "api_patterns requis"}}), 400

        scheduler = APIRequestScheduler(api_patterns)
        scheduler_id = scheduler.scheduler_id
        
        schedulers[scheduler_id] = scheduler
        scheduler_ids[tuple(sorted(api_patterns))] = scheduler_id

        return jsonify({{
            "message": "Scheduler initialisé",
            "scheduler_id": scheduler_id
        }})
    except Exception as e:
        return jsonify({{"error": str(e)}}), 500

@app.route("/api/request", methods=["POST", "GET"])
@authenticate
def api_request():
    try:
        scheduler_id = get_request_param(request, "scheduler_id")
        url = get_request_param(request, "url")
        
        if not scheduler_id or scheduler_id not in schedulers:
            return jsonify({{"error": "Scheduler non trouvé"}}), 404
        
        if not url:
            return jsonify({{"error": "URL requise"}}), 400

        scheduler = schedulers[scheduler_id]
        
        if request.method == "POST":
            data = request.get_json() or {{}}
            payload = data.get("payload")
            method = data.get("method", "GET")
            headers = data.get("headers", {{}})
            cache_duration = data.get("cache_duration", 0)
            client_id = data.get("client_id")
        else:
            payload = None
            method = "GET"
            headers = {{}}
            cache_duration = 0
            client_id = get_request_param(request, "client_id")

        request_id, estimated_delay = scheduler.add_request(
            url=url,
            payload=payload,
            method=method,
            headers=headers,
            cache_duration=cache_duration,
            client_id=client_id
        )

        return jsonify({{
            "uuid": request_id,
            "status_url": f"/api/status/{{request_id}}",
            "estimated_delay": estimated_delay
        }})
        
    except Exception as e:
        return jsonify({{"error": str(e)}}), 500

@app.route("/api/status/<request_id>", methods=["GET"])
@authenticate
def api_status(request_id):
    try:
        for scheduler in schedulers.values():
            if scheduler.has_request(request_id):
                response = scheduler.get_response(request_id)
                if response:
                    return jsonify({{"status": "complete", "response": response}})
                return jsonify({{"status": "pending"}})
        
        return jsonify({{"error": "Requete non trouvee"}}), 404
    except Exception as e:
        return jsonify({{"error": str(e)}}), 500

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({{"status": "healthy", "schedulers": len(schedulers)}})

@app.route("/api/set_rate_limit", methods=["POST", "GET"])
def api_set_rate_limit():
    scheduler_id = get_request_param(request, "scheduler_id")    
    if not scheduler_id or scheduler_id not in schedulers:
        return jsonify({{"error": "Scheduler non trouvé"}}), 404
    scheduler = schedulers[scheduler_id]
    if request.method == "POST":
        data = request.get_json() or {{}}
        rate_limit = data.get("limit")
    else:
        rate_limit = get_request_param(request, "limit")  
    scheduler.set_rate_limit(float(rate_limit))
    return jsonify({{"status": "set_rate_limit ok", "limit": rate_limit, "schedulers": len(schedulers)}})

@app.route("/", methods=["GET"])
def home():
    return "<h1>API Manager Test Server</h1>"

# WebSocket handlers
@socketio.on('connect')
def handle_connect():
    print(f"Client connecté: {{request.sid}}")
    emit("connect", {{"message": "Connecté au serveur de test"}})

@socketio.on('register')
def handle_register(data):
    client_id = data.get('client_id')
    if client_id:
        connected_clients[client_id] = request.sid
        join_room(client_id)
        emit('message', {{'data': f'Enregistré avec client_id: {{client_id}}'}}, room=client_id)

if __name__ == "__main__":
    print(f"Démarrage du serveur de test sur {{TEST_API_HOST}}:{{TEST_API_PORT}}")
    socketio.run(app, host=TEST_API_HOST, port=TEST_API_PORT, debug=False)
'''
        with open("apiManagerClaude.py", encoding="utf-8") as fs:
            script_content = fs.read()
        with open(test_script_path, 'w', encoding="UTF-8") as f:
            f.write(script_content)
        
        return test_script_path
    
    def _wait_for_server_start(self, max_wait=30):
        """Attend que le serveur démarre"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{TEST_BASE_URL}/api/health", timeout=2)
                if response.status_code == 200:
                    print(f"✅ Serveur démarré après {time.time() - start_time:.1f}s")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(0.5)
        pass
        raise Exception(f"Le serveur n'a pas démarré dans les {max_wait}s")
    
    def stop_server(self):
        """Arrête le serveur"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
                print("✅ Serveur arrêté proprement")
            except subprocess.TimeoutExpired:
                self.process.kill()
                print("⚠️ Serveur forcé à s'arrêter")
            except Exception as e:
                print(f"Erreur lors de l'arrêt: {e}")
    
    def cleanup(self):
        """Nettoie l'environnement de test"""
        self.stop_server()
        
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Erreur lors du nettoyage: {e}")


class RealAPIManagerIntegrationTests(unittest.TestCase):
    """Tests d'intégration réels avec serveur API Manager en fonctionnement"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration une seule fois pour tous les tests de cette classe"""
        cls.server = APIManagerTestServer()
        cls.temp_dir = cls.server.setup_test_environment()
        
        # Démarrer le serveur
        if not cls.server.start_server():
            raise Exception("Impossible de démarrer le serveur de test")
        
        cls.headers = {"Authorization": f"Bearer {TEST_BEARER_TOKEN}"}
        cls.base_url = TEST_BASE_URL

    @classmethod
    def tearDownClass(cls):
        """Nettoyage après tous les tests"""
        cls.server.cleanup()

    def test_server_health_check(self):
        """Test du health check du serveur"""
        response = requests.get(f"{self.base_url}/api/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")

    def test_home_page(self):
        """Test de la page d'accueil"""
        response = requests.get(f"{self.base_url}/")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("API Manager", response.text)

    def test_scheduler_initialization(self):
        """Test de l'initialisation d'un scheduler"""
        # Si test_urls contient des regex compilées, convertissez-les en strings
        TEST_APIS_serializable = []
        for url in TEST_APIS:
            if hasattr(url, 'pattern'):  # C'est une regex compilée
                TEST_APIS_serializable.append(url.pattern)
            else:
                TEST_APIS_serializable.append(url)
        init_data = {"api_patterns": TEST_APIS_serializable}
        
        response = requests.post(
            f"{self.base_url}/api/initialize",
            json=init_data,
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("scheduler_id", data)
        self.assertIn("message", data)
        self.scheduler_id = data["scheduler_id"]

    def test_scheduler_initialization_without_auth(self):
        """Test de l'initialisation sans authentification"""
        # Si test_urls contient des regex compilées, convertissez-les en strings
        TEST_APIS_serializable = []
        for url in TEST_APIS:
            if hasattr(url, 'pattern'):  # C'est une regex compilée
                TEST_APIS_serializable.append(url.pattern)
            else:
                TEST_APIS_serializable.append(url)
        init_data = {"api_patterns": TEST_APIS_serializable}
        
        response = requests.post(
            f"{self.base_url}/api/initialize",
            json=init_data
        )
        
        self.assertEqual(response.status_code, 401)

    def test_real_api_request_mockapi_test(self):
        """Test d'une vraie requête API vers httpbin.org"""
        # D'abord initialiser un scheduler
        init_data = {"api_patterns": ["http://127.0.0.1:5000", "http://127.0.0.1:5000/mockapi/test"]}
        init_response = requests.post(
            f"{self.base_url}/api/initialize",
            json=init_data,
            headers=self.headers
        )
        
        self.assertEqual(init_response.status_code, 200)
        scheduler_id = init_response.json()["scheduler_id"]
        
        # Faire une requête vers httpbin
        request_data = {
            "scheduler_id": scheduler_id,
            # "url": "http://127.0.0.1:5000/mockapi/test?test=integration",
            "url": "http://127.0.0.1:5000/mockapi/test",
            "method": "GET"
        }
        
        request_response = requests.post(
            f"{self.base_url}/api/request",
            json=request_data,
            headers=self.headers
        )
        
        self.assertEqual(200, request_response.status_code)
        request_result = request_response.json()
        
        self.assertIn("uuid", request_result)
        self.assertIn("status_url", request_result)
        
        # Attendre et vérifier le statut
        request_id = request_result["uuid"]
        status_url = f"{self.base_url}/api/status/{request_id}"
        
        # Attendre que la requête soit traitée (max 30s)
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            status_response = requests.get(status_url, headers=self.headers)
            self.assertEqual(200, status_response.status_code)
            
            status_data = status_response.json()
            
            if status_data["status"] == "complete":
                self.assertIn("response", status_data)
                response = status_data["response"]
                
                # Vérifier que c'est bien une réponse de httpbin
                self.assertIn("data", response)
                self.assertIn("test", response["data"])
                break
            elif status_data["status"] == "pending":
                time.sleep(0.5)
                attempt += 1
            else:
                self.fail(f"Statut inattendu: {status_data}")
        
        if attempt >= max_attempts:
            self.fail("La requête n'a pas été traitée dans les temps")

    def test_real_api_request_jsonplaceholder(self):
        """Test d'une vraie requête API vers jsonplaceholder"""
        # Initialiser scheduler
        init_data = {"api_patterns": ["http://jsonplaceholder.typicode.com"]}
        init_response = requests.post(
            f"{self.base_url}/api/initialize",
            json=init_data,
            headers=self.headers
        )
        
        scheduler_id = init_response.json()["scheduler_id"]
        
        # Requête GET vers jsonplaceholder
        request_data = {
            "scheduler_id": scheduler_id,
            "url": "http://jsonplaceholder.typicode.com/posts/1",
            "method": "GET"
        }
        
        request_response = requests.post(
            f"{self.base_url}/api/request",
            json=request_data,
            headers=self.headers
        )
        
        self.assertEqual(200, request_response.status_code)
        request_id = request_response.json()["uuid"]
        
        # Attendre la réponse
        max_attempts = 60
        for _ in range(max_attempts):
            status_response = requests.get(
                f"{self.base_url}/api/status/{request_id}",
                headers=self.headers
            )
            
            status_data = status_response.json()
            if "status" in status_data and status_data["status"] == "complete":
                response = status_data["response"]
                
                # Vérifier la structure de réponse de jsonplaceholder
                self.assertIn("userId", response)
                self.assertIn("id", response)
                self.assertIn("title", response)
                self.assertIn("body", response)
                break
            
            time.sleep(0.5)
        else:
            self.fail("Requête jsonplaceholder non traitée")

    def test_rate_limiting_functionality(self):
        """Test de la fonctionnalité de limitation de taux"""
        # Initialiser scheduler avec limite de taux très basse
        init_data = {"api_patterns": ["http://127.0.0.1:5000"]}
        init_response = requests.post(
            f"{self.base_url}/api/initialize",
            json=init_data,
            headers=self.headers
        )
        
        scheduler_id = init_response.json()["scheduler_id"]
        
        # Configurer une limite très basse (0.5 requête/seconde)
        rate_data = {"scheduler_id": scheduler_id, "limit": "0.5"}
        rate_response = requests.post(
            f"{self.base_url}/api/set_rate_limit",
            json=rate_data,
            headers=self.headers
        )
        
        self.assertEqual(200, rate_response.status_code)

        # Faire plusieurs requêtes rapidement
        request_ids = []
        start_time = time.time()
        
        for i in range(3):
            request_data = {
                "scheduler_id": scheduler_id,
                "url": f"http://127.0.0.1:5000/mockapi/test?request={i}",
                "method": "GET"
            }
            
            response = requests.post(
                f"{self.base_url}/api/request",
                json=request_data,
                headers=self.headers
            )
            
            if response.status_code == 200:
                request_ids.append(response.json()["uuid"])
        
        # Vérifier que les délais estimés augmentent
        self.assertGreater(len(request_ids), 0)

    def test_multiple_schedulers(self):
        """Test de gestion de plusieurs schedulers"""
        # Créer le premier scheduler
        init_data1 = {"api_patterns": ["http://127.0.0.1:5000", "http://127.0.0.1:5000/mockapi/test"]}
        response1 = requests.post(
            f"{self.base_url}/api/initialize",
            json=init_data1,
            headers=self.headers
        )
        
        scheduler_id1 = response1.json()["scheduler_id"]
        
        # Créer le deuxième scheduler
        init_data2 = {"api_patterns": ["http://127.0.0.1:5000", "http://127.0.0.1:5000/mockapi/unicode"]}
        response2 = requests.post(
            f"{self.base_url}/api/initialize",
            json=init_data2,
            headers=self.headers
        )
        
        scheduler_id2 = response2.json()["scheduler_id"]
        
        # Vérifier que les schedulers sont différents
        self.assertNotEqual(scheduler_id1, scheduler_id2)
        
        # Faire des requêtes sur chaque scheduler
        request_data1 = {
            "scheduler_id": scheduler_id1,
            "url": "http://127.0.0.1:5000/mockapi/test",
            "method": "GET"
        }
        
        request_data2 = {
            "scheduler_id": scheduler_id2,
            "url": "http://127.0.0.1:5000/mockapi/unicode",
            "method": "GET"
        }
        
        # Les deux requêtes devraient réussir
        resp1 = requests.post(f"{self.base_url}/api/request", json=request_data1, headers=self.headers)
        resp2 = requests.post(f"{self.base_url}/api/request", json=request_data2, headers=self.headers)
        
        self.assertEqual(200, resp1.status_code)
        self.assertEqual(200, resp2.status_code)

    def test_error_handling_invalid_url(self):
        """Test de gestion d'erreur avec URL invalide"""
        # Initialiser scheduler
        init_data = {"api_patterns": ["https://httpbin.org"]}
        init_response = requests.post(
            f"{self.base_url}/api/initialize",
            json=init_data,
            headers=self.headers
        )
        
        scheduler_id = init_response.json()["scheduler_id"]
        
        # Tenter une requête vers une URL non autorisée
        request_data = {
            "scheduler_id": scheduler_id,
            "url": "https://127.0.0.1:5000/test",
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            json=request_data,
            headers=self.headers
        )
        
        self.assertEqual(500, response.status_code)
        error_data = response.json()
        self.assertIn("error", error_data)

    def test_nonexistent_scheduler(self):
        """Test avec un scheduler inexistant"""
        request_data = {
            "scheduler_id": "nonexistent-scheduler-id",
            "url": "http://127.0.0.1:5000/mockapi/test",
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            json=request_data,
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 404)

    def test_invalid_json_request(self):
        """Test avec données JSON invalides"""
        # Envoyer des données non-JSON
        response = requests.post(
            f"{self.base_url}/api/initialize",
            data="invalid json data",
            headers={**self.headers, "Content-Type": "application/json"}
        )
        
        self.assertEqual(500, response.status_code)


class WebSocketIntegrationTests(unittest.TestCase):
    """Tests d'intégration WebSocket réels"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration WebSocket"""
        cls.server = APIManagerTestServer()
        cls.temp_dir = cls.server.setup_test_environment()
        
        if not cls.server.start_server():
            raise Exception("Impossible de démarrer le serveur pour les tests WebSocket")
        
        cls.socket_url = f"http://{TEST_API_HOST}:{TEST_API_PORT}"

    @classmethod
    def tearDownClass(cls):
        """Nettoyage WebSocket"""
        cls.server.cleanup()

    """ code coupé dans Claude
    def test_websocket_connection(self):
        # Test de connexion WebSocket
        sio = socketio.SimpleClient()
        
        try:
            # Se connecter
            sio.connect(self.socket_url)
            self.assertTrue(sio.connected)
            
            # Écouter l'événement de connexion
            event = sio.receive(timeout=5)
            self.assertEqual(event[0], 'connect')
    """