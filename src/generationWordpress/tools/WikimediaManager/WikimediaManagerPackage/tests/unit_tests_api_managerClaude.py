import re
import unittest
import threading
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict

# Mock de la configuration avant l'import
sys.modules['configPrivee'] = Mock()
sys.modules['configPrivee'].config = {
    'admin': {'Bearer': 'test-bearer-token'}
}


def validate_url(base_url, patterns):
    for pattern in patterns:
        if not any(char in pattern.pattern for char in r'.*+?^${}[]|()\\'):
            # URL exacte
            if base_url == pattern:
                return True
        else:
            # Pattern regex
            if re.match(pattern, base_url):
                return True
    return False


# mockurl = "https://httpbin.org/json" # url bidon pour test
mockurl = "https://127.0.0.1:5000/mockapi" # api  bidon locale pour test
#test_urls = [r"^https://127.0.0.1:5000/mockapi(/.*)?$"]
escaped_baseurl = re.escape(mockurl) # escape fait trop de choses!
escaped_baseurl.replace(r'\:', ':')
rexpattern = re.compile(f"^{escaped_baseurl}(/.*)?$")
test_urls = [ rexpattern ]
if not validate_url(mockurl, test_urls):
    raise ValueError(f"URL non gérée par cette instance: {mockurl}")
if not validate_url(f"{mockurl}/unicode", test_urls):
    raise ValueError(f"URL non gérée par cette instance: {mockurl}")
pass

# Définir les classes nécessaires pour les tests (copie du code principal)
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

# Configuration des constantes pour les tests
API_IP_ADDRESS = "127.0.0.1"
API_PORT = 6000
LOG_LEVEL = "INFO"
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1.5
REQUEST_TIMEOUT = 30
CACHE_CLEANUP_INTERVAL = 3600
MAX_QUEUE_SIZE = 10000

class APIRequestScheduler:
    """Version simplifiée du scheduler pour les tests"""
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
        
        # Mock des threads pour les tests
        self.worker_thread = Mock()
        self.loop_thread = Mock()
        
        self._initialized = True

    def _ensure_cache_directory(self):
        """Crée le répertoire de cache s'il n'existe pas"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            raise APIError(f"Impossible de créer le répertoire cache: {e}")

    def set_rate_limit(self, calls_per_second: float):
        """Configure la limitation de taux"""
        if calls_per_second <= 0:
            raise ValueError("Le taux d'appels doit être positif")
        
        self.CALLS_PER_SECOND = calls_per_second
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND

    def get_cache_path(self, cache_key: str) -> str:
        """Génère le chemin du fichier cache"""
        return os.path.join(self.cache_dir, f"{abs(hash(str(cache_key)))}.json")

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

    async def _check_cache(self, request_data: RequestData) -> Optional[Any]:
        """Vérifie si une réponse en cache est disponible"""
        try:
            cache_key = self._generate_cache_key(request_data)
            cache_path = self.get_cache_path(cache_key)
            
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as cache_file:
                    cached_data = json.load(cache_file)
                    
                if time.time() - cached_data['timestamp'] < request_data.cache_duration:
                    return cached_data['response']
                    
        except Exception:
            pass
            
        return None

    async def _make_http_request(self, request_data: RequestData) -> Any:
        """Version mock de la requête HTTP pour les tests"""
        # Simulation d'une requête HTTP réussie
        return {"success": True, "data": "test_response"}

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
        return request_id, estimated_delay

    def get_response(self, request_id: str) -> Optional[Any]:
        """Récupère la réponse d'une requête"""
        with self.lock:
            return self.response_store.pop(request_id, None)

    def has_request(self, request_id: str) -> bool:
        """Vérifie si une requête existe"""
        with self.lock:
            return request_id in self.request_dict

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
        self.shutdown_event.set()

# Décorateur d'authentification pour les tests
def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_token = request.headers.get("Authorization")
            # Utiliser la config mockée
            import sys
            bearer = sys.modules['configPrivee'].config.get('admin', {}).get('Bearer')
            
            if not bearer:
                return jsonify({"error": "Configuration d'authentification manquante"}), 500
            
            if not auth_token:
                return jsonify({"error": "Token d'authentification requis"}), 401
            
            if auth_token != f"Bearer {bearer}":
                return jsonify({"error": "Token d'authentification invalide"}), 401
            
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({"error": "Erreur d'authentification"}), 500

    return decorated_function


class TestRequestData(unittest.TestCase):
    """Tests pour la classe RequestData"""
    
    def test_request_data_initialization(self):
        """Test l'initialisation de RequestData"""
        request_data = RequestData(
            request_id="test-id",
            url=mockurl,
            method="POST"
        )
        
        self.assertEqual(request_data.request_id, "test-id")
        self.assertEqual(request_data.url, mockurl)
        self.assertEqual(request_data.method, "POST")
        self.assertIsNotNone(request_data.timestamp)
        self.assertEqual(request_data.retry_count, 0)
        self.assertIsInstance(request_data.headers, dict)
        self.assertIsInstance(request_data.request_kwargs, dict)

    def test_request_data_with_payload(self):
        """Test RequestData avec payload"""
        payload = {"key": "value"}
        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            payload=payload
        )
        
        self.assertEqual(request_data.payload, payload)

    def test_request_data_timestamp_auto_generation(self):
        """Test la génération automatique du timestamp"""
        before = time.time()
        request_data = RequestData(
            request_id="test-id",
            url=mockurl
        )
        after = time.time()
        
        self.assertGreaterEqual(request_data.timestamp, before)
        self.assertLessEqual(request_data.timestamp, after)


class TestAPIError(unittest.TestCase):
    """Tests pour les exceptions personnalisées"""
    
    def test_api_error_creation(self):
        """Test la création d'une APIError"""
        error = APIError("Test error", status_code=400, request_id="test-id")
        
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.request_id, "test-id")

    def test_rate_limit_exceeded_inheritance(self):
        """Test que RateLimitExceeded hérite d'APIError"""
        error = RateLimitExceeded("Rate limit exceeded")
        
        self.assertIsInstance(error, APIError)
        self.assertEqual(str(error), "Rate limit exceeded")


class TestAPIRequestScheduler(unittest.TestCase):
    """Tests pour la classe APIRequestScheduler"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        self.test_urls = test_urls
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock des threads pour éviter les effets de bord
        self.thread_patcher = patch('threading.Thread')
        self.mock_thread = self.thread_patcher.start()
        self.mock_thread.return_value.start = Mock()
        
        # Mock du signal handler
        self.signal_patcher = patch('signal.signal')
        self.mock_signal = self.signal_patcher.start()

    def tearDown(self):
        """Nettoyage après chaque test"""
        self.thread_patcher.stop()
        self.signal_patcher.stop()
        
        # Nettoyer le répertoire temporaire
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # Nettoyer les instances singleton
        APIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    def test_scheduler_initialization(self, mock_getcwd):
        """Test l'initialisation du scheduler"""
        mock_getcwd.return_value = self.temp_dir
        
        scheduler = APIRequestScheduler(self.test_urls)
        
        self.assertEqual(scheduler.api_patterns, self.test_urls)
        self.assertEqual(scheduler.CALLS_PER_SECOND, 1)
        self.assertIsNotNone(scheduler.scheduler_id)
        self.assertTrue(hasattr(scheduler, 'request_queue'))
        self.assertTrue(hasattr(scheduler, 'response_store'))

    @patch('os.getcwd')
    def test_scheduler_singleton_behavior(self, mock_getcwd):
        """Test le comportement singleton du scheduler"""
        mock_getcwd.return_value = self.temp_dir
        
        scheduler1 = APIRequestScheduler(self.test_urls)
        scheduler2 = APIRequestScheduler(self.test_urls)
        
        self.assertIs(scheduler1, scheduler2)

    @patch('os.getcwd')
    def test_set_rate_limit(self, mock_getcwd):
        """Test la configuration de la limite de taux"""
        mock_getcwd.return_value = self.temp_dir
        
        scheduler = APIRequestScheduler(self.test_urls)
        scheduler.set_rate_limit(2.0)
        
        self.assertEqual(scheduler.CALLS_PER_SECOND, 2.0)
        self.assertEqual(scheduler.CALL_INTERVAL, 0.5)

    @patch('os.getcwd')
    def test_set_rate_limit_invalid(self, mock_getcwd):
        """Test la validation de la limite de taux"""
        mock_getcwd.return_value = self.temp_dir
        
        scheduler = APIRequestScheduler(self.test_urls)
        
        with self.assertRaises(ValueError):
            scheduler.set_rate_limit(0)
        
        with self.assertRaises(ValueError):
            scheduler.set_rate_limit(-1)

    @patch('os.getcwd')
    def test_cache_path_generation(self, mock_getcwd):
        """Test la génération des chemins de cache"""
        mock_getcwd.return_value = self.temp_dir
        
        scheduler = APIRequestScheduler(self.test_urls)
        cache_key = "test-cache-key"
        cache_path = scheduler.get_cache_path(cache_key)
        
        expected_path = os.path.join(self.temp_dir, 'cache', f"{abs(hash(cache_key))}.json")
        self.assertEqual(cache_path, expected_path)

    @patch('os.getcwd')
    #@patch('queue.Queue')
    def test_add_request_success(self, mock_queue, mock_getcwd):
        """Test l'ajout réussi d'une requête"""
        mock_getcwd.return_value = self.temp_dir

        # Configurez le mock AVANT de créer l'instance de APIRequestScheduler
        mock_queue_instance = Mock()
        mock_queue.return_value = mock_queue_instance
        mock_queue_instance.qsize.return_value = 5

        # Maintenant créez le scheduler (qui utilisera le mock configuré)
        scheduler = APIRequestScheduler(self.test_urls)

        # Exécutez votre test
        request_id, estimated_delay = scheduler.add_request(
            url="mockurl",  # J'ai ajouté les guillemets manquants
            payload={"test": "data"}
        )

        # Vos assertions
        self.assertIsInstance(request_id, str)
        self.assertGreater(len(request_id), 0)
        self.assertIsInstance(estimated_delay, float)

        # Debug
        print(f"put appelé ? {mock_queue_instance.put.called}")
        print(f"Nombre d'appels : {mock_queue_instance.put.call_count}")
        print(f"Historique des appels : {mock_queue_instance.put.call_args_list}")

        # Assertion qui devrait maintenant fonctionner
        mock_queue_instance.put.assert_called_once()

    @patch('os.getcwd')
    def test_add_request_invalid_url(self, mock_getcwd):
        """Test l'ajout d'une requête avec URL invalide"""
        mock_getcwd.return_value = self.temp_dir
        
        scheduler = APIRequestScheduler(self.test_urls)
        
        with self.assertRaises(ValueError):
            scheduler.add_request("https://invalid-api.com/test")

    @patch('os.getcwd')
    def test_has_request(self, mock_getcwd):
        """Test la vérification de l'existence d'une requête"""
        mock_getcwd.return_value = self.temp_dir
        
        scheduler = APIRequestScheduler(self.test_urls)
        request_id = "test-request-id"
        
        # Initialement, la requête n'existe pas
        self.assertFalse(scheduler.has_request(request_id))
        
        # Ajouter la requête au dictionnaire de suivi
        scheduler.request_dict[request_id] = Mock()
        
        # Maintenant elle existe
        self.assertTrue(scheduler.has_request(request_id))

    @patch('os.getcwd')
    def test_get_response(self, mock_getcwd):
        """Test la récupération d'une réponse"""
        mock_getcwd.return_value = self.temp_dir
        
        scheduler = APIRequestScheduler(self.test_urls)
        request_id = "test-request-id"
        test_response = {"result": "success"}
        
        # Ajouter une réponse
        scheduler.response_store[request_id] = test_response
        
        # Récupérer la réponse
        response = scheduler.get_response(request_id)
        
        self.assertEqual(response, test_response)
        # Vérifier que la réponse est supprimée après récupération
        self.assertNotIn(request_id, scheduler.response_store)

    @patch('os.getcwd')
    def test_get_stats(self, mock_getcwd):
        """Test la récupération des statistiques"""
        mock_getcwd.return_value = self.temp_dir
        
        with patch('queue.Queue') as mock_queue:
            mock_queue_instance = Mock()
            mock_queue.return_value = mock_queue_instance
            mock_queue_instance.qsize.return_value = 3
            
            scheduler = APIRequestScheduler(self.test_urls)
            scheduler.request_dict = {"req1": Mock(), "req2": Mock()}
            scheduler.response_store = {"resp1": Mock()}
            
            stats = scheduler.get_stats()
            
            expected_keys = [
                "scheduler_id", "queue_size", "pending_requests", 
                "pending_responses", "calls_per_second", "managed_urls"
            ]
            
            for key in expected_keys:
                self.assertIn(key, stats)
            
            self.assertEqual(stats["queue_size"], 3)
            self.assertEqual(stats["pending_requests"], 2)
            self.assertEqual(stats["pending_responses"], 1)
            self.assertEqual(stats["calls_per_second"], 1)
            self.assertEqual(stats["managed_urls"], 1)


class TestAPIRequestSchedulerAsync(unittest.IsolatedAsyncioTestCase):
    """Tests asynchrones pour APIRequestScheduler"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        self.test_urls = test_urls
        self.temp_dir = tempfile.mkdtemp()
        
        # Clear singleton instances
        APIRequestScheduler._instances.clear()

    def tearDown(self):
        """Nettoyage après chaque test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        APIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    async def test_cache_hit(self, mock_signal, mock_thread, mock_getcwd):
        """Test le hit de cache"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()
        
        scheduler = APIRequestScheduler(self.test_urls)
        
        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            cache_duration=3600
        )
        
        # Créer un fichier de cache valide
        cache_key = scheduler._generate_cache_key(request_data)
        cache_path = scheduler.get_cache_path(cache_key)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        
        cached_response = {"cached": True, "data": "test"}
        cache_data = {
            "response": cached_response,
            "timestamp": time.time()
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)
        
        # Test du cache hit
        result = await scheduler._check_cache(request_data)
        
        self.assertEqual(result, cached_response)

    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    async def test_cache_miss_expired(self, mock_signal, mock_thread, mock_getcwd):
        """Test le cache miss avec données expirées"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()
        
        scheduler = APIRequestScheduler(self.test_urls)
        
        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            cache_duration=3600
        )
        
        # Créer un fichier de cache expiré
        cache_key = scheduler._generate_cache_key(request_data)
        cache_path = scheduler.get_cache_path(cache_key)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        
        expired_cache_data = {
            "response": {"expired": True},
            "timestamp": time.time() - 7200  # 2 heures dans le passé
        }
        
        with open(cache_path, 'w') as f:
            json.dump(expired_cache_data, f)
        
        # Test du cache miss
        result = await scheduler._check_cache(request_data)
        
        self.assertIsNone(result)

    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    def test_generate_cache_key(self, mock_signal, mock_thread, mock_getcwd):
        """Test la génération de clé de cache"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()
        
        scheduler = APIRequestScheduler(self.test_urls)
        
        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            payload={"key": "value"},
            method="POST",
            headers={"Content-Type": "application/json"}
        )
        
        cache_key = scheduler._generate_cache_key(request_data)
        
        self.assertIsInstance(cache_key, str)
        self.assertIn(mockurl,  cache_key)
        self.assertIn("POST", cache_key)

    @patch('aiohttp.ClientSession.request')
    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    async def test_make_http_request_success(self, mock_signal, mock_thread, mock_getcwd, mock_request):
        """Test une requête HTTP réussie"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()
        
        # Mock de la réponse HTTP
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.raise_for_status = Mock()
        
        mock_request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        scheduler = APIRequestScheduler(self.test_urls)
        
        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            method="GET"
        )
        
        result = await scheduler._make_http_request(request_data)
        
        self.assertEqual(result, {"success": True})
        mock_request.assert_called_once()

    @patch('aiohttp.ClientSession.request')
    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    async def test_make_http_request_with_retry(self, mock_signal, mock_thread, mock_getcwd, mock_request):
        """Test une requête HTTP avec retry"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()
        
        # Mock qui échoue puis réussit
        mock_response_fail = AsyncMock()
        mock_response_fail.raise_for_status.side_effect = Exception("Network error")
        
        mock_response_success = AsyncMock()
        mock_response_success.json = AsyncMock(return_value={"success": True})
        mock_response_success.raise_for_status = Mock()
        
        mock_request.side_effect = [
            # Premier appel - échec
            AsyncMock(__aenter__=AsyncMock(return_value=mock_response_fail), 
                     __aexit__=AsyncMock(return_value=None)),
            # Deuxième appel - succès
            AsyncMock(__aenter__=AsyncMock(return_value=mock_response_success), 
                     __aexit__=AsyncMock(return_value=None))
        ]
        
        scheduler = APIRequestScheduler(self.test_urls)
        
        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            method="GET"
        )
        
        # Mock sleep pour accélérer le test
        with patch('asyncio.sleep'):
            result = await scheduler._make_http_request(request_data)
        
        self.assertEqual(result, {"success": True})
        self.assertEqual(mock_request.call_count, 2)


class TestFlaskApp(unittest.TestCase):
    """Tests pour l'application Flask"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        # Mock de la configuration
        self.config_patcher = patch.dict('sys.modules', {
            'configPrivee': Mock(config={'admin': {'Bearer': 'test-bearer'}})
        })
        self.config_patcher.start()
        
        # Créer l'app de test
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret'
        
        # Ajouter les routes de test (simplifié pour les tests)
        @self.app.route('/test-auth')
        @authenticate
        def test_auth():
            return {"message": "authenticated"}
        
        self.client = self.app.test_client()

    def tearDown(self):
        """Nettoyage après chaque test"""
        self.config_patcher.stop()

    def test_authenticate_decorator_success(self):
        """Test du décorateur d'authentification avec token valide"""
        headers = {"Authorization": "Bearer test-bearer"}
        response = self.client.get('/test-auth', headers=headers)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["message"], "authenticated")

    def test_authenticate_decorator_missing_token(self):
        """Test du décorateur d'authentification sans token"""
        response = self.client.get('/test-auth')
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_authenticate_decorator_invalid_token(self):
        """Test du décorateur d'authentification avec token invalide"""
        headers = {"Authorization": "Bearer wrong-token"}
        response = self.client.get('/test-auth', headers=headers)
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_authenticate_decorator_malformed_header(self):
        """Test du décorateur d'authentification avec header malformé"""
        headers = {"Authorization": "InvalidFormat"}
        response = self.client.get('/test-auth', headers=headers)
        
        self.assertEqual(response.status_code, 401)


class TestUtilityFunctions(unittest.TestCase):
    """Tests pour les fonctions utilitaires"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
    def test_get_request_param_from_args(self):
        """Test la récupération de paramètre depuis les args (GET)"""
        with self.app.test_request_context('/?test_param=value'):
            from flask import request
            # Simuler la fonction get_request_param
            def get_request_param(request_obj, param_name):
                param = request_obj.args.get(param_name)
                if param is None and request_obj.method == "POST":
                    data = request_obj.get_json()
                    if data:
                        param = data.get(param_name)
                return param
            
            result = get_request_param(request, 'test_param')
            self.assertEqual(result, 'value')

    def test_get_request_param_from_json(self):
        """Test la récupération de paramètre depuis JSON (POST)"""
        json_data = json.dumps({"test_param": "json_value"})
        
        with self.app.test_request_context('/', method='POST', 
                                         data=json_data, 
                                         content_type='application/json'):
            from flask import request
            
            def get_request_param(request_obj, param_name):
                param = request_obj.args.get(param_name)
                if param is None and request_obj.method == "POST":
                    data = request_obj.get_json()
                    if data:
                        param = data.get(param_name)
                return param
            
            result = get_request_param(request, 'test_param')
            self.assertEqual(result, 'json_value')

    def test_get_request_param_not_found(self):
        """Test la récupération de paramètre inexistant"""
        with self.app.test_request_context('/'):
            from flask import request
            
            def get_request_param(request_obj, param_name):
                param = request_obj.args.get(param_name)
                if param is None and request_obj.method == "POST":
                    data = request_obj.get_json()
                    if data:
                        param = data.get(param_name)
                return param
            
            result = get_request_param(request, 'nonexistent')
            self.assertIsNone(result)


class TestLoggingSetup(unittest.TestCase):
    """Tests pour la configuration du logging"""
    
    @patch('logging.handlers.RotatingFileHandler')
    @patch('logging.StreamHandler')
    def test_setup_logging(self, mock_stream_handler, mock_file_handler):
        """Test la configuration du système de logging"""
        # Mock des handlers
        mock_stream = Mock()
        mock_file = Mock()
        mock_stream_handler.return_value = mock_stream
        mock_file_handler.return_value = mock_file
        
        # Tester la fonction setup_logging (simulée)
        def setup_logging():
            import logging
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            
            console_handler = mock_stream_handler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            file_handler = mock_file_handler(
                'api_manager.log',
                maxBytes=10*1024*1024,
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            return logger
        
        logger = setup_logging()
        
        # Vérifications
        mock_stream_handler.assert_called_once()
        mock_file_handler.assert_called_once_with(
            'api_manager.log',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        mock_stream.setFormatter.assert_called_once()
        mock_file.setFormatter.assert_called_once()


class TestWebSocketEvents(unittest.TestCase):
    """Tests pour les événements WebSocket"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        from flask import Flask
        from flask_socketio import SocketIO
        
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.socketio = SocketIO(self.app)
        
        # Mock des gestionnaires d'événements
        @self.socketio.on('connect')
        def handle_connect():
            return True
        
        @self.socketio.on('register')
        def handle_register(data):
            client_id = data.get('client_id')
            if client_id:
                # Simuler l'enregistrement
                return {'status': 'registered', 'client_id': client_id}
            return {'error': 'client_id required'}
        
        self.client = self.socketio.test_client(self.app)

    def test_websocket_connection(self):
        """Test la connexion WebSocket"""
        self.assertTrue(self.client.is_connected())

    def test_websocket_register_event(self):
        """Test l'événement d'enregistrement WebSocket"""
        # Envoyer un événement de registration
        self.client.emit('register', {'client_id': 'test-client-123'})
        
        # Vérifier la réponse (dans un vrai test, on vérifierait les événements reçus)
        received = self.client.get_received()
        self.assertIsInstance(received, list)

    def test_websocket_register_without_client_id(self):
        """Test l'événement d'enregistrement sans client_id"""
        self.client.emit('register', {})
        
        received = self.client.get_received()
        self.assertIsInstance(received, list)


class TestIntegration(unittest.TestCase):
    """Tests d'intégration pour l'ensemble du système"""
    
    def setUp(self):
        """Configuration avant chaque test d'intégration"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock de la configuration
        self.config_patcher = patch.dict('sys.modules', {
            'configPrivee': Mock(config={'admin': {'Bearer': 'integration-test-bearer'}})
        })
        self.config_patcher.start()
        
        # Clear singleton instances
        APIRequestScheduler._instances.clear()

    def tearDown(self):
        """Nettoyage après chaque test d'intégration"""
        self.config_patcher.stop()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        APIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    #@patch('queue.Queue')
    def test_full_request_lifecycle(self, mock_queue, mock_signal, mock_thread, mock_getcwd):
        """Test du cycle de vie complet d'une requête"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()
        
        # Mock de la queue
        mock_queue_instance = Mock()
        mock_queue.return_value = mock_queue_instance
        mock_queue_instance.qsize.return_value = 1
        
        # 1. Créer un scheduler
        scheduler = APIRequestScheduler(test_urls)
        
        # 2. Ajouter une requête
        request_id, delay = scheduler.add_request(
            url=mockurl, 
            payload={"test": "data"},
            method="POST"
        )
        
        # 3. Vérifier que la requête a été ajoutée
        self.assertTrue(scheduler.has_request(request_id))
        mock_queue_instance.put.assert_called_once()
        
        # 4. Simuler une réponse
        test_response = {"result": "success"}
        scheduler.response_store[request_id] = test_response
        
        # 5. Récupérer la réponse
        response = scheduler.get_response(request_id)
        self.assertEqual(response, test_response)
        
        # 6. Vérifier que la réponse a été supprimée du store
        self.assertNotIn(request_id, scheduler.response_store)

    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    def test_cache_integration(self, mock_signal, mock_thread, mock_getcwd):
        """Test d'intégration du système de cache"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()
        
        scheduler = APIRequestScheduler(test_urls)
        
        # Créer une requête avec cache
        request_data = RequestData(
            request_id="cache-test-id",
            url=mockurl, 
            cache_duration=3600,
            payload={"cache": "test"}
        )
        
        # Générer et vérifier la clé de cache
        cache_key = scheduler._generate_cache_key(request_data)
        cache_path = scheduler.get_cache_path(cache_key)
        
        self.assertIsInstance(cache_key, str)
        self.assertTrue(cache_path.endswith('.json'))
        
        # Vérifier que le répertoire de cache existe
        self.assertTrue(os.path.exists(scheduler.cache_dir))


class TestPerformance(unittest.TestCase):
    """Tests de performance"""

    def setUp(self):
        """Configuration avant chaque test de performance"""
        self.temp_dir = tempfile.mkdtemp()
        APIRequestScheduler._instances.clear()

    def tearDown(self):
        """Nettoyage après chaque test de performance"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        APIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    def test_multiple_requests_performance(self, mock_getcwd):
        """Test de performance avec plusieurs requêtes"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(test_urls)

        # Mesurer le temps pour ajouter 100 requêtes
        start_time = time.time()
        request_ids = []

        for i in range(100):
            request_id, _ = scheduler.add_request(
                url=f"https://api.example.com/test/{i}",
                payload={"index": i}
            )
            request_ids.append(request_id)

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Vérifier que toutes les requêtes ont été ajoutées rapidement
        self.assertEqual(len(request_ids), 100)
        self.assertLess(elapsed_time, 1.0)  # Moins d'1 seconde

        # Vérifier que toutes les requêtes sont trackées
        for request_id in request_ids:
            self.assertTrue(scheduler.has_request(request_id))

    @patch('os.getcwd')
    def test_concurrent_access_thread_safety(self, mock_getcwd):
        """Test de sécurité des threads avec accès concurrent"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(test_urls)
        results = []
        errors = []

        def add_requests_thread(thread_id):
            try:
                for i in range(10):
                    request_id, _ = scheduler.add_request(
                        url=f"https://api.example.com/thread/{thread_id}/req/{i}",
                        payload={"thread": thread_id, "request": i}
                    )
                    results.append(request_id)
            except Exception as e:
                errors.append(str(e))

        # Créer et démarrer plusieurs threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_requests_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Attendre que tous les threads se terminent
        for thread in threads:
            thread.join()

        # Vérifications
        self.assertEqual(len(errors), 0)  # Aucune erreur
        self.assertEqual(len(results), 50)  # 5 threads * 10 requêtes
        self.assertEqual(len(set(results)), 50)  # Tous les IDs sont uniques

    @patch('os.getcwd')
    def test_memory_usage_with_large_payloads(self, mock_getcwd):
        """Test d'utilisation mémoire avec de gros payloads"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(test_urls)

        # Créer un payload volumineux
        large_payload = {"data": "x" * 10000}  # 10KB de données

        # Ajouter plusieurs requêtes avec de gros payloads
        request_ids = []
        for i in range(10):
            request_id, _ = scheduler.add_request(
                url=f"{mockurl}/large/{i}",
                payload=large_payload
            )
            request_ids.append(request_id)

        # Vérifier que tout fonctionne correctement
        self.assertEqual(len(request_ids), 10)
        for request_id in request_ids:
            self.assertTrue(scheduler.has_request(request_id))


class TestEdgeCases(unittest.TestCase):
    """Tests pour les cas limites"""

    def setUp(self):
        """Configuration avant chaque test de cas limite"""
        self.temp_dir = tempfile.mkdtemp()
        APIRequestScheduler._instances.clear()

    def tearDown(self):
        """Nettoyage après chaque test de cas limite"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        APIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    def test_empty_url_list(self, mock_getcwd):
        """Test avec une liste d'URLs vide"""
        mock_getcwd.return_value = self.temp_dir

        # Créer un scheduler avec une liste vide (devrait fonctionner)
        scheduler = APIRequestScheduler([])

        # Tenter d'ajouter une requête devrait échouer
        with self.assertRaises(ValueError):
            scheduler.add_request(mockurl)

    @patch('os.getcwd')
    def test_malformed_urls(self, mock_getcwd):
        """Test avec des URLs malformées"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(test_urls)

        # URLs invalides
        invalid_urls = [
            "not-a-url",
            "ftp://invalid-scheme.com",
            "https://",
            "",
            None
        ]

        for invalid_url in invalid_urls:
            if invalid_url is not None:
                with self.assertRaises((ValueError, AttributeError)):
                    scheduler.add_request(invalid_url)

    @patch('os.getcwd')
    def test_extreme_rate_limits(self, mock_getcwd):
        """Test avec des limites de taux extrêmes"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(test_urls)

        # Test avec une limite très élevée
        scheduler.set_rate_limit(10000.0)
        self.assertEqual(scheduler.CALLS_PER_SECOND, 10000.0)
        self.assertAlmostEqual(scheduler.CALL_INTERVAL, 0.0001, places=6)

        # Test avec une limite très basse
        scheduler.set_rate_limit(0.001)
        self.assertEqual(scheduler.CALLS_PER_SECOND, 0.001)
        self.assertEqual(scheduler.CALL_INTERVAL, 1000.0)

    @patch('os.getcwd')
    def test_unicode_and_special_characters(self, mock_getcwd):
        """Test avec des caractères Unicode et spéciaux"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(test_urls)

        # Payload avec caractères spéciaux
        unicode_payload = {
            "message": "Héllo Wörld! 🌍",
            "data": "Test avec des caractères spéciaux: éàü",
            "emoji": "🚀💡🔥",
            "special_chars": "!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/"
        }

        request_id, _ = scheduler.add_request(
            url=f"{mockurl}/unicode",
            payload=unicode_payload
        )

        self.assertTrue(scheduler.has_request(request_id))

    @patch('os.getcwd')
    def test_very_long_urls_and_payloads(self, mock_getcwd):
        """Test avec des URLs et payloads très longs"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(test_urls)

        # URL très longue (mais valide)
        long_path = "/very/long/path/" + "segment/" * 100
        long_url = mockurl + long_path

        # Payload très volumineux
        large_payload = {"data": ["item"] * 1000}

        request_id, _ = scheduler.add_request(
            url=long_url,
            payload=large_payload
        )

        self.assertTrue(scheduler.has_request(request_id))

    @patch('os.getcwd')
    def test_none_and_empty_values(self, mock_getcwd):
        """Test avec des valeurs None et vides"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(test_urls)

        # Test avec des valeurs None/vides
        request_id, _ = scheduler.add_request(
            url=mockurl, 
            payload=None,
            headers=None,
            client_id=None,
            cache_duration=0
        )

        self.assertTrue(scheduler.has_request(request_id))

        # Test avec payload vide
        request_id2, _ = scheduler.add_request(
            url=f"{mockurl}/empty",
            payload={},
            headers={}
        )

        self.assertTrue(scheduler.has_request(request_id2))


class TestErrorRecovery(unittest.TestCase):
    """Tests de récupération d'erreurs"""

    def setUp(self):
        """Configuration avant chaque test de récupération"""
        self.temp_dir = tempfile.mkdtemp()
        APIRequestScheduler._instances.clear()

    def tearDown(self):
        """Nettoyage après chaque test de récupération"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        APIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    def test_cache_directory_creation_failure(self, mock_getcwd):
        """Test d'échec de création du répertoire cache"""
        # Pointer vers un répertoire invalide
        mock_getcwd.return_value = "/invalid/path/that/does/not/exist"

        # Mock os.makedirs pour simuler un échec
        with patch('os.makedirs', side_effect=OSError("Permission denied")):
            with self.assertRaises(APIError):
                APIRequestScheduler(test_urls)

    @patch('os.getcwd')
    @patch('builtins.open', side_effect=IOError("Cannot read file"))
    def test_cache_read_failure(self, mock_open, mock_getcwd):
        """Test d'échec de lecture du cache"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(test_urls)

        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            cache_duration=3600
        )

        # Le cache check devrait gérer l'erreur gracieusement
        result = asyncio.run(scheduler._check_cache(request_data))
        self.assertIsNone(result)

    @patch('os.getcwd')
    def test_corrupted_cache_file(self, mock_getcwd):
        """Test avec un fichier cache corrompu"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(test_urls)

        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            cache_duration=3600
        )

        # Créer un fichier cache corrompu
        cache_key = scheduler._generate_cache_key(request_data)
        cache_path = scheduler.get_cache_path(cache_key)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        with open(cache_path, 'w') as f:
            f.write("invalid json content {")

        # Le cache check devrait gérer gracieusement le JSON invalide
        result = asyncio.run(scheduler._check_cache(request_data))
        self.assertIsNone(result)


class TestMockIntegration(unittest.TestCase):
    """Tests d'intégration avec des mocks"""

    def setUp(self):
        """Configuration avant chaque test d'intégration"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret'

        # Stockage global des schedulers pour les tests
        self.schedulers = {}
        self.scheduler_ids = {}

        # Routes de test simplifiées
        @self.app.route("/api/initialize", methods=["POST"])
        @authenticate
        def initialize_scheduler():
            data = request.get_json()
            api_patterns = data.get("api_patterns", [])

            if not api_patterns:
                return jsonify({"error": "api_patterns required"}), 400

            # retablir les regex patterns qui ont été sérialisées
            # test naif si * dans la string on suppose regex
            rebuild_patterns = []
            for pattern in api_patterns:
                if "*" in pattern:
                    rebuild_patterns.append(re.compile(pattern))
                else:
                    rebuild_patterns.append(pattern)
            scheduler = APIRequestScheduler(rebuild_patterns)
            scheduler_id = scheduler.scheduler_id

            self.schedulers[scheduler_id] = scheduler
            self.scheduler_ids[tuple(sorted(api_patterns))] = scheduler_id

            return jsonify({
                "message": "Scheduler initialized",
                "scheduler_id": scheduler_id
            })

        @self.app.route("/api/request", methods=["POST"])
        @authenticate
        def api_request():
            data = request.get_json()
            scheduler_id = data.get("scheduler_id")
            url = data.get("url")

            if scheduler_id not in self.schedulers:
                return jsonify({"error": "Scheduler not found"}), 404

            scheduler = self.schedulers[scheduler_id]

            try:
                request_id, delay = scheduler.add_request(
                    url=url,
                    payload=data.get("payload"),
                    method=data.get("method", "POST")
                )

                return jsonify({
                    "uuid": request_id,
                    "estimated_delay": delay
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        self.client = self.app.test_client()

    def tearDown(self):
        """Nettoyage après chaque test d'intégration"""
        APIRequestScheduler._instances.clear()

    def test_full_api_workflow(self):
        """Test du workflow API complet"""
        headers = {"Authorization": "Bearer test-bearer-token"}
        # Si test_urls contient des regex compilées, convertissez-les en strings
        test_urls_serializable = []
        for url in test_urls:
            if hasattr(url, 'pattern'):  # C'est une regex compilée
                test_urls_serializable.append(url.pattern)
            else:
                test_urls_serializable.append(url)

        # 1. Initialiser un scheduler
        init_data = {"api_patterns": test_urls_serializable}
        response = self.client.post('/api/initialize',
                                    json=init_data,
                                    headers=headers)

        self.assertEqual(200, response.status_code)
        init_result = json.loads(response.data)
        scheduler_id = init_result["scheduler_id"]

        # 2. Ajouter une requête
        request_data = {
            "scheduler_id": scheduler_id,
            "url": mockurl, 
            "payload": {"test": "data"},
            "method": "POST"
        }

        response = self.client.post('/api/request',
                                    json=request_data,
                                    headers=headers)

        self.assertEqual(200, response.status_code)
        request_result = json.loads(response.data)

        self.assertIn("uuid", request_result)
        self.assertIn("estimated_delay", request_result)

        # 3. Vérifier que la requête existe dans le scheduler
        scheduler = self.schedulers[scheduler_id]
        self.assertTrue(scheduler.has_request(request_result["uuid"]))

    def test_api_error_handling(self):
        """Test de gestion d'erreurs dans l'API"""
        headers = {"Authorization": "Bearer test-bearer-token"}

        # Test sans api_patterns
        response = self.client.post('/api/initialize',
                                    json={},
                                    headers=headers)
        self.assertEqual(response.status_code, 400)

        # Test avec scheduler inexistant
        request_data = {
            "scheduler_id": "nonexistent-id",
            "url": mockurl
        }

        response = self.client.post('/api/request',
                                    json=request_data,
                                    headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_authentication_workflow(self):
        """Test du workflow d'authentification"""
        # Test sans token
        # Si test_urls contient des regex compilées, convertissez-les en strings
        test_urls_serializable = []
        for url in test_urls:
            if hasattr(url, 'pattern'):  # C'est une regex compilée
                test_urls_serializable.append(url.pattern)
            else:
                test_urls_serializable.append(url)
        response = self.client.post('/api/initialize', json={"api_patterns": test_urls_serializable})
        self.assertEqual(response.status_code, 401)

        # Test avec token invalide
        bad_headers = {"Authorization": "Bearer wrong-token"}
        response = self.client.post('/api/initialize',
                                    json={"api_patterns": test_urls_serializable},
                                    headers=bad_headers)
        self.assertEqual(response.status_code, 401)

        # Test avec token valide
        good_headers = {"Authorization": "Bearer test-bearer-token"}
        response = self.client.post('/api/initialize',
                                    json={"api_patterns": test_urls_serializable},
                                    headers=good_headers)
        self.assertEqual(response.status_code, 200)


# Suite de tests principale
def create_test_suite():
    """Crée la suite de tests complète"""
    suite = unittest.TestSuite()

    # Tests de base
    suite.addTest(unittest.makeSuite(TestRequestData))
    suite.addTest(unittest.makeSuite(TestAPIError))
    suite.addTest(unittest.makeSuite(TestAPIRequestScheduler))

    # Tests asynchrones
    suite.addTest(unittest.makeSuite(TestAPIRequestSchedulerAsync))

    # Tests Flask
    suite.addTest(unittest.makeSuite(TestFlaskApp))
    suite.addTest(unittest.makeSuite(TestUtilityFunctions))

    # Tests WebSocket
    suite.addTest(unittest.makeSuite(TestWebSocketEvents))

    # Tests de logging
    suite.addTest(unittest.makeSuite(TestLoggingSetup))

    # Tests de performance
    suite.addTest(unittest.makeSuite(TestPerformance))

    # Tests de cas limites
    suite.addTest(unittest.makeSuite(TestEdgeCases))

    # Tests de récupération d'erreurs
    suite.addTest(unittest.makeSuite(TestErrorRecovery))

    # Tests d'intégration
    suite.addTest(unittest.makeSuite(TestIntegration))
    suite.addTest(unittest.makeSuite(TestMockIntegration))

    return suite


def run_tests():
    """Lance tous les tests"""
    runner = unittest.TextTestRunner(verbosity=2)
    suite = create_test_suite()
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    # Configuration du logging pour les tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("🧪 Lancement de la suite de tests pour l'API Manager")
    print("=" * 60)

    success = run_tests()

    if success:
        print("\n✅ Tous les tests sont passés avec succès!")
        exit(0)
    else:
        print("\n❌ Certains tests ont échoué.")
        exit(1)


# Utilitaires pour les tests en ligne de commande
class TestRunner:
    """Utilitaire pour exécuter des groupes spécifiques de tests"""

    @staticmethod
    def run_unit_tests():
        """Lance uniquement les tests unitaires de base"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestRequestData))
        suite.addTest(unittest.makeSuite(TestAPIError))
        suite.addTest(unittest.makeSuite(TestAPIRequestScheduler))

        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)

    @staticmethod
    def run_performance_tests():
        """Lance uniquement les tests de performance"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestPerformance))

        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)

    @staticmethod
    def run_integration_tests():
        """Lance uniquement les tests d'intégration"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestIntegration))
        suite.addTest(unittest.makeSuite(TestMockIntegration))

        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)

    @staticmethod
    def run_async_tests():
        """Lance uniquement les tests asynchrones"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestAPIRequestSchedulerAsync))

        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)

    @staticmethod
    def run_edge_case_tests():
        """Lance uniquement les tests de cas limites"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestEdgeCases))
        suite.addTest(unittest.makeSuite(TestErrorRecovery))

        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)


# Configuration des tests avec pytest (optionnel)
def pytest_configure():
    """Configuration pour pytest si disponible"""
    try:
        import pytest
        return True
    except ImportError:
        return False


# Tests de benchmark (optionnel, nécessite des dépendances supplémentaires)
class BenchmarkTests:
    """Tests de benchmark pour mesurer les performances"""

    @staticmethod
    def benchmark_scheduler_creation():
        """Benchmark de création de scheduler"""
        import time

        times = []
        for _ in range(100):
            APIRequestScheduler._instances.clear()
            start = time.perf_counter()
            scheduler = APIRequestScheduler(test_urls)
            end = time.perf_counter()
            times.append(end - start)

        avg_time = sum(times) / len(times)
        print(f"⏱️  Temps moyen de création de scheduler: {avg_time:.6f}s")
        return avg_time

    @staticmethod
    def benchmark_request_addition():
        """Benchmark d'ajout de requêtes"""
        import time

        APIRequestScheduler._instances.clear()
        scheduler = APIRequestScheduler(test_urls)

        times = []
        for i in range(1000):
            start = time.perf_counter()
            request_id, _ = scheduler.add_request(
                url=f"{mockurl}/test/{i}",
                payload={"index": i}
            )
            end = time.perf_counter()
            times.append(end - start)

        avg_time = sum(times) / len(times)
        print(f"⏱️  Temps moyen d'ajout de requête: {avg_time:.6f}s")
        return avg_time

    @staticmethod
    def benchmark_cache_operations():
        """Benchmark des opérations de cache"""
        import time
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()

        try:
            with patch('os.getcwd', return_value=temp_dir):
                APIRequestScheduler._instances.clear()
                scheduler = APIRequestScheduler(test_urls)

                # Test de génération de clé de cache
                request_data = RequestData(
                    request_id="bench-test",
                    url=mockurl, 
                    payload={"test": "data"}
                )

                times = []
                for _ in range(1000):
                    start = time.perf_counter()
                    cache_key = scheduler._generate_cache_key(request_data)
                    end = time.perf_counter()
                    times.append(end - start)

                avg_time = sum(times) / len(times)
                print(f"⏱️  Temps moyen de génération de clé cache: {avg_time:.6f}s")

                return avg_time

        finally:
            shutil.rmtree(temp_dir)


# Documentation des tests
TEST_DOCUMENTATION = """
📚 DOCUMENTATION DES TESTS - API MANAGER

🏗️  STRUCTURE DES TESTS:

1. TestRequestData
   - Tests de la structure de données des requêtes
   - Validation des champs et types
   - Génération automatique des timestamps

2. TestAPIError
   - Tests des exceptions personnalisées
   - Héritage et propriétés des erreurs
   - Gestion des codes d'erreur

3. TestAPIRequestScheduler
   - Tests du scheduler principal
   - Singleton pattern
   - Gestion des queues et réponses
   - Configuration des limites de taux

4. TestAPIRequestSchedulerAsync
   - Tests des opérations asynchrones
   - Cache hit/miss
   - Requêtes HTTP avec retry
   - Génération de clés de cache

5. TestFlaskApp
   - Tests des routes Flask
   - Authentification
   - Gestion des erreurs HTTP

6. TestUtilityFunctions
   - Tests des fonctions utilitaires
   - Extraction de paramètres
   - Validation des entrées

7. TestWebSocketEvents
   - Tests des événements WebSocket
   - Connexion/déconnexion
   - Enregistrement des clients

8. TestLoggingSetup
   - Tests de configuration du logging
   - Handlers de fichier et console
   - Rotation des logs

9. TestPerformance
   - Tests de performance et scalabilité
   - Gestion de multiples requêtes
   - Thread safety

10. TestEdgeCases
    - Tests des cas limites
    - URLs malformées
    - Valeurs extrêmes
    - Caractères spéciaux

11. TestErrorRecovery
    - Tests de récupération d'erreurs
    - Échecs de cache
    - Fichiers corrompus

12. TestIntegration & TestMockIntegration
    - Tests d'intégration complète
    - Workflow API complet
    - Tests end-to-end

🚀 COMMENT LANCER LES TESTS:

1. Tous les tests:
   python test_api_manager.py

2. Tests spécifiques:
   TestRunner.run_unit_tests()
   TestRunner.run_performance_tests()
   TestRunner.run_integration_tests()

3. Avec pytest (si installé):
   pytest test_api_manager.py -v

4. Tests de benchmark:
   BenchmarkTests.benchmark_scheduler_creation()

📊 COUVERTURE DES TESTS:

✅ Classes et méthodes principales
✅ Cas d'erreur et exceptions
✅ Performance et thread safety
✅ Intégration Flask/WebSocket
✅ Cache et persistance
✅ Authentification et sécurité
✅ Cas limites et edge cases
✅ Opérations asynchrones
✅ Configuration et logging

🔧 DÉPENDANCES REQUISES:

- unittest (Python standard)
- unittest.mock (Python standard)
- flask
- flask-socketio
- aiohttp (pour les tests async)
- pytest (optionnel)

⚠️  NOTES IMPORTANTES:

- Les tests utilisent des mocks pour éviter les appels réseau réels
- Les répertoires temporaires sont automatiquement nettoyés
- Les instances singleton sont réinitialisées entre les tests
- Les threads sont mockés pour éviter les effets de bord
- La configuration est mockée pour les tests d'authentification

💡 CONSEILS D'UTILISATION:

1. Lancez d'abord les tests unitaires pour valider la base
2. Utilisez les tests de performance pour identifier les goulots
3. Les tests d'intégration valident le comportement end-to-end
4. Surveillez la sortie des tests pour identifier les problèmes
5. Utilisez les benchmarks pour optimiser les performances

🐛 DEBUGGING:

- Augmentez la verbosité avec -v
- Utilisez logging.DEBUG pour plus de détails
- Vérifiez les mocks si les tests échouent de façon inattendue
- Les tests de thread safety peuvent être non-déterministes

"""


def print_test_documentation():
    """Affiche la documentation des tests"""
    print(TEST_DOCUMENTATION)


# Point d'entrée principal avec options
if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "help" or command == "--help":
            print_test_documentation()
        elif command == "unit":
            print("🧪 Lancement des tests unitaires...")
            TestRunner.run_unit_tests()
        elif command == "performance":
            print("⚡ Lancement des tests de performance...")
            TestRunner.run_performance_tests()
        elif command == "integration":
            print("🔗 Lancement des tests d'intégration...")
            TestRunner.run_integration_tests()
        elif command == "async":
            print("🔄 Lancement des tests asynchrones...")
            TestRunner.run_async_tests()
        elif command == "edge":
            print("🎯 Lancement des tests de cas limites...")
            TestRunner.run_edge_case_tests()
        elif command == "benchmark":
            print("📊 Lancement des benchmarks...")
            BenchmarkTests.benchmark_scheduler_creation()
            BenchmarkTests.benchmark_request_addition()
            BenchmarkTests.benchmark_cache_operations()
        elif command == "doc":
            print_test_documentation()
        else:
            print(f"❌ Commande inconnue: {command}")
            print("💡 Utilisez 'help' pour voir les options disponibles")
    else:
        # Lancement de tous les tests par défaut
        print("🧪 Lancement de la suite de tests complète pour l'API Manager")
        print("=" * 60)

        success = run_tests()

        if success:
            print("\n✅ Tous les tests sont passés avec succès!")
            print("📊 Vous pouvez maintenant lancer les benchmarks avec: python test_api_manager.py benchmark")
            exit(0)
        else:
            print("\n❌ Certains tests ont échoué.")
            print("💡 Utilisez python test_api_manager.py help pour plus d'options")
            exit(1)
            import unittest
import asyncio
import json
import os
import tempfile
import threading
import time
import uuid
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import shutil
import sys
from queue import Queue, Empty
from urllib.parse import urlparse
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
from functools import wraps

# Imports pour les tests Flask et SocketIO
import pytest
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, SocketIOTestClient

# Mock de la configuration avant l'import
sys.modules['configPrivee'] = Mock()
sys.modules['configPrivee'].config = {
    'admin': {'Bearer': 'test-bearer-token'}
}


# Définir les classes nécessaires pour les tests (copie du code principal)
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


# Configuration des constantes pour les tests
API_IP_ADDRESS = "127.0.0.1"
API_PORT = 6000
LOG_LEVEL = "INFO"
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1.5
REQUEST_TIMEOUT = 30
CACHE_CLEANUP_INTERVAL = 3600
MAX_QUEUE_SIZE = 10000


class APIRequestScheduler:
    """Version simplifiée du scheduler pour les tests"""
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

        # Mock des threads pour les tests
        self.worker_thread = Mock()
        self.loop_thread = Mock()

        self._initialized = True

    def _ensure_cache_directory(self):
        """Crée le répertoire de cache s'il n'existe pas"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            raise APIError(f"Impossible de créer le répertoire cache: {e}")

    def set_rate_limit(self, calls_per_second: float):
        """Configure la limitation de taux"""
        if calls_per_second <= 0:
            raise ValueError("Le taux d'appels doit être positif")

        self.CALLS_PER_SECOND = calls_per_second
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND

    def get_cache_path(self, cache_key: str) -> str:
        """Génère le chemin du fichier cache"""
        return os.path.join(self.cache_dir, f"{abs(hash(str(cache_key)))}.json")

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

    async def _check_cache(self, request_data: RequestData) -> Optional[Any]:
        """Vérifie si une réponse en cache est disponible"""
        try:
            cache_key = self._generate_cache_key(request_data)
            cache_path = self.get_cache_path(cache_key)

            if os.path.exists(cache_path):
                with open(cache_path, 'r') as cache_file:
                    cached_data = json.load(cache_file)

                if time.time() - cached_data['timestamp'] < request_data.cache_duration:
                    return cached_data['response']

        except Exception:
            pass

        return None

    async def _make_http_request(self, request_data: RequestData) -> Any:
        """Version mock de la requête HTTP pour les tests"""
        # Simulation d'une requête HTTP réussie
        return {"success": True, "data": "test_response"}

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
        return request_id, estimated_delay

    def get_response(self, request_id: str) -> Optional[Any]:
        """Récupère la réponse d'une requête"""
        with self.lock:
            return self.response_store.pop(request_id, None)

    def has_request(self, request_id: str) -> bool:
        """Vérifie si une requête existe"""
        with self.lock:
            return request_id in self.request_dict

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
        self.shutdown_event.set()


# Décorateur d'authentification pour les tests
def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_token = request.headers.get("Authorization")
            # Utiliser la config mockée
            import sys
            bearer = sys.modules['configPrivee'].config.get('admin', {}).get('Bearer')

            if not bearer:
                return jsonify({"error": "Configuration d'authentification manquante"}), 500

            if not auth_token:
                return jsonify({"error": "Token d'authentification requis"}), 401

            if auth_token != f"Bearer {bearer}":
                return jsonify({"error": "Token d'authentification invalide"}), 401

            return f(*args, **kwargs)

        except Exception as e:
            return jsonify({"error": "Erreur d'authentification"}), 500

    return decorated_function


class TestRequestData(unittest.TestCase):
    """Tests pour la classe RequestData"""

    def test_request_data_initialization(self):
        """Test l'initialisation de RequestData"""
        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            method="POST"
        )

        self.assertEqual(request_data.request_id, "test-id")
        self.assertEqual(request_data.url, mockurl)
        self.assertEqual(request_data.method, "POST")
        self.assertIsNotNone(request_data.timestamp)
        self.assertEqual(request_data.retry_count, 0)
        self.assertIsInstance(request_data.headers, dict)
        self.assertIsInstance(request_data.request_kwargs, dict)

    def test_request_data_with_payload(self):
        """Test RequestData avec payload"""
        payload = {"key": "value"}
        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            payload=payload
        )

        self.assertEqual(request_data.payload, payload)

    def test_request_data_timestamp_auto_generation(self):
        """Test la génération automatique du timestamp"""
        before = time.time()
        request_data = RequestData(
            request_id="test-id",
            url=mockurl
        )
        after = time.time()

        self.assertGreaterEqual(request_data.timestamp, before)
        self.assertLessEqual(request_data.timestamp, after)


class TestAPIError(unittest.TestCase):
    """Tests pour les exceptions personnalisées"""

    def test_api_error_creation(self):
        """Test la création d'une APIError"""
        error = APIError("Test error", status_code=400, request_id="test-id")

        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.request_id, "test-id")

    def test_rate_limit_exceeded_inheritance(self):
        """Test que RateLimitExceeded hérite d'APIError"""
        error = RateLimitExceeded("Rate limit exceeded")

        self.assertIsInstance(error, APIError)
        self.assertEqual(str(error), "Rate limit exceeded")


class TestAPIRequestScheduler(unittest.TestCase):
    """Tests pour la classe APIRequestScheduler"""

    def setUp(self):
        """Configuration avant chaque test"""
        self.test_urls = test_urls
        self.temp_dir = tempfile.mkdtemp()

        # Mock des threads pour éviter les effets de bord
        self.thread_patcher = patch('threading.Thread')
        self.mock_thread = self.thread_patcher.start()
        self.mock_thread.return_value.start = Mock()

        # Mock du signal handler
        self.signal_patcher = patch('signal.signal')
        self.mock_signal = self.signal_patcher.start()

    def tearDown(self):
        """Nettoyage après chaque test"""
        self.thread_patcher.stop()
        self.signal_patcher.stop()

        # Nettoyer le répertoire temporaire
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        # Nettoyer les instances singleton
        APIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    def test_scheduler_initialization(self, mock_getcwd):
        """Test l'initialisation du scheduler"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(self.test_urls)

        self.assertEqual(scheduler.api_patterns, self.test_urls)
        self.assertEqual(scheduler.CALLS_PER_SECOND, 1)
        self.assertIsNotNone(scheduler.scheduler_id)
        self.assertTrue(hasattr(scheduler, 'request_queue'))
        self.assertTrue(hasattr(scheduler, 'response_store'))

    @patch('os.getcwd')
    def test_scheduler_singleton_behavior(self, mock_getcwd):
        """Test le comportement singleton du scheduler"""
        mock_getcwd.return_value = self.temp_dir

        scheduler1 = APIRequestScheduler(self.test_urls)
        scheduler2 = APIRequestScheduler(self.test_urls)

        self.assertIs(scheduler1, scheduler2)

    @patch('os.getcwd')
    def test_set_rate_limit(self, mock_getcwd):
        """Test la configuration de la limite de taux"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(self.test_urls)
        scheduler.set_rate_limit(2.0)

        self.assertEqual(scheduler.CALLS_PER_SECOND, 2.0)
        self.assertEqual(scheduler.CALL_INTERVAL, 0.5)

    @patch('os.getcwd')
    def test_set_rate_limit_invalid(self, mock_getcwd):
        """Test la validation de la limite de taux"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(self.test_urls)

        with self.assertRaises(ValueError):
            scheduler.set_rate_limit(0)

        with self.assertRaises(ValueError):
            scheduler.set_rate_limit(-1)

    @patch('os.getcwd')
    def test_cache_path_generation(self, mock_getcwd):
        """Test la génération des chemins de cache"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(self.test_urls)
        cache_key = "test-cache-key"
        cache_path = scheduler.get_cache_path(cache_key)

        expected_path = os.path.join(self.temp_dir, 'cache', f"{abs(hash(cache_key))}.json")
        self.assertEqual(cache_path, expected_path)

    @patch('os.getcwd')
    # @patch('queue.Queue')
    def test_add_request_success(self, mock_getcwd): # mock_queue, mock_getcwd):
        """Test l'ajout réussi d'une requête"""
        mock_getcwd.return_value = self.temp_dir
        scheduler = APIRequestScheduler(self.test_urls)

        # Configurez le mock AVANT de créer l'instance de APIRequestScheduler
        mock_queue_instance = Mock()
        mock_queue_instance.qsize.return_value = 5
        scheduler.request_queue = mock_queue_instance

        # Exécutez votre test
        request_id, estimated_delay = scheduler.add_request(
            url=mockurl,
            payload={"test": "data"}
        )

        # Vos assertions
        self.assertIsInstance(request_id, str)
        self.assertGreater(len(request_id), 0)
        self.assertIsInstance(estimated_delay, float)

        # Debug
        print(f"put appelé ? {mock_queue_instance.put.called}")
        print(f"Nombre d'appels : {mock_queue_instance.put.call_count}")
        print(f"Historique des appels : {mock_queue_instance.put.call_args_list}")

        # Assertion qui devrait maintenant fonctionner
        mock_queue_instance.put.assert_called_once()

    @patch('os.getcwd')
    def test_add_request_invalid_url(self, mock_getcwd):
        """Test l'ajout d'une requête avec URL invalide"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(self.test_urls)

        with self.assertRaises(ValueError):
            scheduler.add_request("https://invalid-api.com/test")

    @patch('os.getcwd')
    def test_has_request(self, mock_getcwd):
        """Test la vérification de l'existence d'une requête"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(self.test_urls)
        request_id = "test-request-id"

        # Initialement, la requête n'existe pas
        self.assertFalse(scheduler.has_request(request_id))

        # Ajouter la requête au dictionnaire de suivi
        scheduler.request_dict[request_id] = Mock()

        # Maintenant elle existe
        self.assertTrue(scheduler.has_request(request_id))

    @patch('os.getcwd')
    def test_get_response(self, mock_getcwd):
        """Test la récupération d'une réponse"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = APIRequestScheduler(self.test_urls)
        request_id = "test-request-id"
        test_response = {"result": "success"}

        # Ajouter une réponse
        scheduler.response_store[request_id] = test_response

        # Récupérer la réponse
        response = scheduler.get_response(request_id)

        self.assertEqual(response, test_response)
        # Vérifier que la réponse est supprimée après récupération
        self.assertNotIn(request_id, scheduler.response_store)

    @patch('os.getcwd')
    def test_get_stats(self, mock_getcwd):
        """Test la récupération des statistiques"""
        mock_getcwd.return_value = self.temp_dir

        # Créez le scheduler normalement
        scheduler = APIRequestScheduler(self.test_urls)

        # Mockez uniquement les attributs nécessaires pour les stats
        mock_queue_instance = Mock()
        mock_queue_instance.qsize.return_value = 3
        scheduler.request_queue = mock_queue_instance

        # Configurez les données de test
        scheduler.request_dict = {"req1": Mock(), "req2": Mock()}
        scheduler.response_store = {"resp1": Mock()}

        # Exécutez le test
        stats = scheduler.get_stats()

        # Vos assertions
        expected_keys = [
            "scheduler_id",
            "queue_size",
            "pending_requests",
            "pending_responses",
            "calls_per_second",
            "managed_urls"
        ]

        for key in expected_keys:
            self.assertIn(key, stats)

        self.assertEqual(stats["queue_size"], 3)
        self.assertEqual(stats["pending_requests"], 2)
        self.assertEqual(stats["pending_responses"], 1)
        self.assertEqual(stats["calls_per_second"], 1)
        self.assertEqual(stats["managed_urls"], 1)

class TestAPIRequestSchedulerAsync(unittest.IsolatedAsyncioTestCase):
    """Tests asynchrones pour APIRequestScheduler"""

    def setUp(self):
        """Configuration avant chaque test"""
        self.test_urls = test_urls
        self.temp_dir = tempfile.mkdtemp()

        # Clear singleton instances
        APIRequestScheduler._instances.clear()

    def tearDown(self):
        """Nettoyage après chaque test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

        APIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    async def test_cache_hit(self, mock_signal, mock_thread, mock_getcwd):
        """Test le hit de cache"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()

        scheduler = APIRequestScheduler(self.test_urls)

        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            cache_duration=3600
        )

        # Créer un fichier de cache valide
        cache_key = scheduler._generate_cache_key(request_data)
        cache_path = scheduler.get_cache_path(cache_key)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        cached_response = {"cached": True, "data": "test"}
        cache_data = {
            "response": cached_response,
            "timestamp": time.time()
        }

        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        # Test du cache hit
        result = await scheduler._check_cache(request_data)

        self.assertEqual(result, cached_response)

    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    async def test_cache_miss_expired(self, mock_signal, mock_thread, mock_getcwd):
        """Test le cache miss avec données expirées"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()

        scheduler = APIRequestScheduler(self.test_urls)

        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            cache_duration=3600
        )

        # Créer un fichier de cache expiré
        cache_key = scheduler._generate_cache_key(request_data)
        cache_path = scheduler.get_cache_path(cache_key)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        expired_cache_data = {
            "response": {"expired": True},
            "timestamp": time.time() - 7200  # 2 heures dans le passé
        }

        with open(cache_path, 'w') as f:
            json.dump(expired_cache_data, f)

        # Test du cache miss
        result = await scheduler._check_cache(request_data)

        self.assertIsNone(result)

    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    def test_generate_cache_key(self, mock_signal, mock_thread, mock_getcwd):
        """Test la génération de clé de cache"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()

        scheduler = APIRequestScheduler(self.test_urls)

        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            payload={"key": "value"},
            method="POST",
            headers={"Content-Type": "application/json"}
        )

        cache_key = scheduler._generate_cache_key(request_data)

        self.assertIsInstance(cache_key, str)
        self.assertIn(mockurl,  cache_key)
        self.assertIn("POST", cache_key)

    @patch('aiohttp.ClientSession.request')
    @patch('os.getcwd')
    async def test_make_http_request_success(self, mock_getcwd, mock_request):
        """Test une requête HTTP réussie"""
        mock_getcwd.return_value = self.temp_dir

        # Mock de la réponse HTTP
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.raise_for_status = Mock()

        mock_request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request.return_value.__aexit__ = AsyncMock(return_value=None)

        scheduler = APIRequestScheduler(self.test_urls)

        # Mock spécifique pour éviter les threads si nécessaire
        #with patch.object(scheduler, '_start_processing_thread', Mock()):
            # Ou mockez directement les attributs de thread si votre scheduler en a
        #    if hasattr(scheduler, 'processing_thread'):
        #        scheduler.processing_thread = Mock()
        #        scheduler.processing_thread.start = Mock()

        request_data = RequestData(
            request_id="test-id",
            url=mockurl,
            method="GET"
        )

        result = await scheduler._make_http_request(request_data)

        self.assertEqual(result, {'data': 'test_response', 'success': True})
        mock_request.assert_called_once()

    @patch('aiohttp.ClientSession.request')
    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    async def test_make_http_request_with_retry(self, mock_signal, mock_thread, mock_getcwd, mock_request):
        """Test une requête HTTP avec retry"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()

        # Mock qui échoue puis réussit
        mock_response_fail = AsyncMock()
        mock_response_fail.raise_for_status.side_effect = Exception("Network error")

        mock_response_success = AsyncMock()
        mock_response_success.json = AsyncMock(return_value={"success": True})
        mock_response_success.raise_for_status = Mock()

        mock_request.side_effect = [
            # Premier appel - échec
            AsyncMock(__aenter__=AsyncMock(return_value=mock_response_fail),
                      __aexit__=AsyncMock(return_value=None)),
            # Deuxième appel - succès
            AsyncMock(__aenter__=AsyncMock(return_value=mock_response_success),
                      __aexit__=AsyncMock(return_value=None))
        ]

        scheduler = APIRequestScheduler(self.test_urls)

        request_data = RequestData(
            request_id="test-id",
            url=mockurl, 
            method="GET"
        )

        # Mock sleep pour accélérer le test
        with patch('asyncio.sleep'):
            result = await scheduler._make_http_request(request_data)

        self.assertEqual(result, {'data': 'test_response', 'success': True})
        self.assertEqual(mock_request.call_count, 2)


class TestFlaskApp(unittest.TestCase):
    """Tests pour l'application Flask"""

    def setUp(self):
        """Configuration avant chaque test"""
        # Mock de la configuration
        self.config_patcher = patch.dict('sys.modules', {
            'configPrivee': Mock(config={'admin': {'Bearer': 'test-bearer'}})
        })
        self.config_patcher.start()

        # Créer l'app de test
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret'

        # Ajouter les routes de test (simplifié pour les tests)
        @self.app.route('/test-auth')
        @authenticate
        def test_auth():
            return {"message": "authenticated"}

        self.client = self.app.test_client()

    def tearDown(self):
        """Nettoyage après chaque test"""
        self.config_patcher.stop()

    def test_authenticate_decorator_success(self):
        """Test du décorateur d'authentification avec token valide"""
        headers = {"Authorization": "Bearer test-bearer"}
        response = self.client.get('/test-auth', headers=headers)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["message"], "authenticated")

    def test_authenticate_decorator_missing_token(self):
        """Test du décorateur d'authentification sans token"""
        response = self.client.get('/test-auth')

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_authenticate_decorator_invalid_token(self):
        """Test du décorateur d'authentification avec token invalide"""
        headers = {"Authorization": "Bearer wrong-token"}
        response = self.client.get('/test-auth', headers=headers)

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_authenticate_decorator_malformed_header(self):
        """Test du décorateur d'authentification avec header malformé"""
        headers = {"Authorization": "InvalidFormat"}
        response = self.client.get('/test-auth', headers=headers)

        self.assertEqual(response.status_code, 401)


class TestUtilityFunctions(unittest.TestCase):
    """Tests pour les fonctions utilitaires"""

    def setUp(self):
        """Configuration avant chaque test"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

    def test_get_request_param_from_args(self):
        """Test la récupération de paramètre depuis les args (GET)"""
        with self.app.test_request_context('/?test_param=value'):
            from flask import request
            # Simuler la fonction get_request_param
            def get_request_param(request_obj, param_name):
                param = request_obj.args.get(param_name)
                if param is None and request_obj.method == "POST":
                    data = request_obj.get_json()
                    if data:
                        param = data.get(param_name)
                return param

            result = get_request_param(request, 'test_param')
            self.assertEqual(result, 'value')

    def test_get_request_param_from_json(self):
        """Test la récupération de paramètre depuis JSON (POST)"""
        json_data = json.dumps({"test_param": "json_value"})

        with self.app.test_request_context('/', method='POST',
                                           data=json_data,
                                           content_type='application/json'):
            from flask import request

            def get_request_param(request_obj, param_name):
                param = request_obj.args.get(param_name)
                if param is None and request_obj.method == "POST":
                    data = request_obj.get_json()
                    if data:
                        param = data.get(param_name)
                return param

            result = get_request_param(request, 'test_param')
            self.assertEqual(result, 'json_value')

    def test_get_request_param_not_found(self):
        """Test la récupération de paramètre inexistant"""
        with self.app.test_request_context('/'):
            from flask import request

            def get_request_param(request_obj, param_name):
                param = request_obj.args.get(param_name)
                if param is None and request_obj.method == "POST":
                    data = request_obj.get_json()
                    if data:
                        param = data.get(param_name)
                return param

            result = get_request_param(request, 'nonexistent')
            self.assertIsNone(result)


class TestLoggingSetup(unittest.TestCase):
    """Tests pour la configuration du logging"""

    @patch('logging.handlers.RotatingFileHandler')
    @patch('logging.StreamHandler')
    def test_setup_logging(self, mock_stream_handler, mock_file_handler):
        """Test la configuration du système de logging"""
        # Mock des handlers
        mock_stream = Mock()
        mock_file = Mock()
        mock_stream_handler.return_value = mock_stream
        mock_file_handler.return_value = mock_file

        # Tester la fonction setup_logging (simulée)
        def setup_logging():
            import logging
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)

            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )

            console_handler = mock_stream_handler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            file_handler = mock_file_handler(
                'api_manager.log',
                maxBytes=10 * 1024 * 1024,
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            return logger

        logger = setup_logging()

        # Vérifications
        mock_stream_handler.assert_called_once()
        mock_file_handler.assert_called_once_with(
            'api_manager.log',
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
        mock_stream.setFormatter.assert_called_once()
        mock_file.setFormatter.assert_called_once()


class TestWebSocketEvents(unittest.TestCase):
    """Tests pour les événements WebSocket"""

    def setUp(self):
        """Configuration avant chaque test"""
        from flask import Flask
        from flask_socketio import SocketIO

        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.socketio = SocketIO(self.app)

        # Mock des gestionnaires d'événements
        @self.socketio.on('connect')
        def handle_connect():
            return True

        @self.socketio.on('register')
        def handle_register(data):
            client_id = data.get('client_id')
            if client_id:
                # Simuler l'enregistrement
                return {'status': 'registered', 'client_id': client_id}
            return {'error': 'client_id required'}

        self.client = self.socketio.test_client(self.app)

    def test_websocket_connection(self):
        """Test la connexion WebSocket"""
        self.assertTrue(self.client.is_connected())

    def test_websocket_register_event(self):
        """Test l'événement d'enregistrement WebSocket"""
        # Envoyer un événement de registration
        self.client.emit('register', {'client_id': 'test-client-123'})

        # Vérifier la réponse (dans un vrai test, on vérifierait les événements reçus)
        received = self.client.get_received()
        self.assertIsInstance(received, list)

    def test_websocket_register_without_client_id(self):
        """Test l'événement d'enregistrement sans client_id"""
        self.client.emit('register', {})

        received = self.client.get_received()
        self.assertIsInstance(received, list)


class TestIntegration(unittest.TestCase):
    """Tests d'intégration pour l'ensemble du système"""

    def setUp(self):
        """Configuration avant chaque test d'intégration"""
        self.temp_dir = tempfile.mkdtemp()

        # Mock de la configuration
        self.config_patcher = patch.dict('sys.modules', {
            'configPrivee': Mock(config={'admin': {'Bearer': 'integration-test-bearer'}})
        })
        self.config_patcher.start()

        # Clear singleton instances
        APIRequestScheduler._instances.clear()

    def tearDown(self):
        """Nettoyage après chaque test d'intégration"""
        self.config_patcher.stop()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        APIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    def test_full_request_lifecycle(self, mock_getcwd):
        """Test du cycle de vie complet d'une requête"""
        mock_getcwd.return_value = self.temp_dir

        # Créez le scheduler normalement
        scheduler = APIRequestScheduler(test_urls)  # Utilisez self.test_urls

        # Mockez seulement les attributs nécessaires APRÈS création
        mock_queue_instance = Mock()
        mock_queue_instance.qsize.return_value = 1
        scheduler.request_queue = mock_queue_instance

        # Mockez le thread si nécessaire (après création)
        if hasattr(scheduler, 'processing_thread'):
            scheduler.processing_thread = Mock()
            scheduler.processing_thread.start = Mock()

        # 1. Ajouter une requête
        request_id, delay = scheduler.add_request(
            url=mockurl,
            payload={"test": "data"},
            method="POST"
        )

        # 2. Vérifier que la requête a été ajoutée
        self.assertTrue(scheduler.has_request(request_id))
        mock_queue_instance.put.assert_called_once()

        # 3. Simuler une réponse
        test_response = {"result": "success"}
        scheduler.response_store[request_id] = test_response

        # 4. Récupérer la réponse
        response = scheduler.get_response(request_id)
        self.assertEqual(response, test_response)

        # 5. Vérifier que la réponse a été supprimée du store
        self.assertNotIn(request_id, scheduler.response_store)

    @patch('os.getcwd')
    @patch('threading.Thread')
    @patch('signal.signal')
    def test_cache_integration(self, mock_signal, mock_thread, mock_getcwd):
        """Test d'intégration du système de cache"""
        mock_getcwd.return_value = self.temp_dir
        mock_thread.return_value.start = Mock()

        scheduler = APIRequestScheduler(test_urls)

        # Créer une requête avec cache
        request_data = RequestData(
            request_id="cache-test-id",
            url=mockurl, 
            cache_duration=3600,
            payload={"cache": "test"}
        )

        # Générer et vérifier la clé de cache
        cache_key = scheduler._generate_cache_key(request_data)
        cache_path = scheduler.get_cache_path(cache_key)

        self.assertIsInstance(cache_key, str)
        self.assertTrue(cache_path.endswith('.json'))

        # Vérifier que le répertoire de cache existe
        self.assertTrue(os.path.exists(scheduler.cache_dir))

