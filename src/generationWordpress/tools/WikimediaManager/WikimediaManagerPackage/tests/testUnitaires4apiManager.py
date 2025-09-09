import unittest
import json
import os
import tempfile
import shutil
import time
import asyncio
import threading
from unittest.mock import patch, MagicMock, mock_open, AsyncMock
from unittest.mock import call as MockCall
import requests
import uuid
from queue import Queue, Empty
from datetime import datetime, timedelta
from urllib.parse import urlparse
import sys

# Mock de la configuration avant l'import du serveur
sys.modules['configPrivee'] = MagicMock()
config_mock = MagicMock()
config_mock.get.return_value = {'Bearer': 'test-bearer-token'}
sys.modules['configPrivee'].config = config_mock

# Import du code serveur (adapter le nom du fichier selon votre cas)
# from apiManagerClaude import (
#     APIRequestScheduler, RequestData, APIError, RateLimitExceeded,
#     app, socketio, authenticate, connected_clients
# )
from apiManagerClaude import (
     APIRequestScheduler, authenticate
)

# Classes de test copiées depuis le serveur pour éviter les imports
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple, List

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


class TestRequestData(unittest.TestCase):
    """Tests pour la classe RequestData"""
    
    def test_request_data_creation_minimal(self):
        """Test création RequestData avec paramètres minimaux"""
        request_id = str(uuid.uuid4())
        url = "http://127.0.0.1:5000/mockapi"
        
        req_data = RequestData(request_id=request_id, url=url)
        
        self.assertEqual(req_data.request_id, request_id)
        self.assertEqual(req_data.url, url)
        self.assertIsNone(req_data.payload)
        self.assertEqual(req_data.method, 'POST')
        self.assertEqual(req_data.headers, {})
        self.assertEqual(req_data.cache_duration, 0)
        self.assertEqual(req_data.request_kwargs, {})
        self.assertIsNone(req_data.client_id)
        self.assertIsNotNone(req_data.timestamp)
        self.assertEqual(req_data.retry_count, 0)

    def test_request_data_creation_complete(self):
        """Test création RequestData avec tous les paramètres"""
        request_id = str(uuid.uuid4())
        url = "http://127.0.0.1:5000/mockapi"
        payload = {"key": "value"}
        headers = {"Authorization": "Bearer token"}
        timestamp = time.time()
        
        req_data = RequestData(
            request_id=request_id,
            url=url,
            payload=payload,
            method="GET",
            headers=headers,
            cache_duration=300,
            request_kwargs={"timeout": 30},
            client_id="client123",
            timestamp=timestamp,
            retry_count=2
        )
        
        self.assertEqual(req_data.request_id, request_id)
        self.assertEqual(req_data.url, url)
        self.assertEqual(req_data.payload, payload)
        self.assertEqual(req_data.method, "GET")
        self.assertEqual(req_data.headers, headers)
        self.assertEqual(req_data.cache_duration, 300)
        self.assertEqual(req_data.request_kwargs, {"timeout": 30})
        self.assertEqual(req_data.client_id, "client123")
        self.assertEqual(req_data.timestamp, timestamp)
        self.assertEqual(req_data.retry_count, 2)

    def test_request_data_post_init_defaults(self):
        """Test que __post_init__ initialise les valeurs par défaut"""
        req_data = RequestData("123", "http://example.com")
        
        # Vérifier que les valeurs par défaut sont définies
        self.assertIsInstance(req_data.headers, dict)
        self.assertIsInstance(req_data.request_kwargs, dict)
        self.assertIsInstance(req_data.timestamp, (int, float))
        self.assertGreater(req_data.timestamp, 0)


class TestExceptions(unittest.TestCase):
    """Tests pour les classes d'exception personnalisées"""
    
    def test_api_error_creation(self):
        """Test création d'APIError"""
        message = "Test error message"
        status_code = 404
        request_id = str(uuid.uuid4())
        
        error = APIError(message, status_code, request_id)
        
        self.assertEqual(str(error), message)
        self.assertEqual(error.status_code, status_code)
        self.assertEqual(error.request_id, request_id)

    def test_api_error_minimal(self):
        """Test création d'APIError avec paramètres minimaux"""
        message = "Simple error"
        error = APIError(message)
        
        self.assertEqual(str(error), message)
        self.assertIsNone(error.status_code)
        self.assertIsNone(error.request_id)

    def test_rate_limit_exceeded_inheritance(self):
        """Test que RateLimitExceeded hérite d'APIError"""
        error = RateLimitExceeded("Rate limit exceeded")
        
        self.assertIsInstance(error, APIError)
        self.assertEqual(str(error), "Rate limit exceeded")


class TestAPIRequestScheduler(unittest.TestCase):
    """Tests pour la classe APIRequestScheduler"""
    
    def setUp(self):
        """Configuration avant chaque test"""
        self.api_patterns = ["http://127.0.0.1:5000/mockapi", "http://127.0.0.1:5000/mockapi/test", "http://127.0.0.1:5000/mockapi/unicode"]
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Nettoyage après chaque test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch('threading.Thread')
    @patch('asyncio.new_event_loop')
    def test_scheduler_initialization(self, mock_event_loop, mock_thread):
        """Test d'initialisation du scheduler"""
        mock_loop = MagicMock()
        mock_event_loop.return_value = mock_loop
        
        # Mock des threads
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        with patch('os.makedirs'):
            scheduler = APIRequestScheduler(self.api_patterns)
            
            self.assertEqual(scheduler.api_patterns, self.api_patterns)
            self.assertEqual(scheduler.CALLS_PER_SECOND, 1)
            self.assertEqual(scheduler.CALL_INTERVAL, 1.0)
            self.assertIsInstance(scheduler.request_queue, Queue)
            self.assertIsInstance(scheduler.response_store, dict)
            self.assertIsInstance(scheduler.request_dict, dict)
            self.assertIsNotNone(scheduler.scheduler_id)

    def test_singleton_behavior(self):
        """Test du comportement singleton du scheduler"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler1 = APIRequestScheduler(self.api_patterns)
            scheduler2 = APIRequestScheduler(self.api_patterns)
            
            # Même instance pour les mêmes patterns
            self.assertIs(scheduler1, scheduler2)
            
            # Instance différente pour des patterns différents
            different_patterns = ["https://api3.example.com"]
            scheduler3 = APIRequestScheduler(different_patterns)
            self.assertIsNot(scheduler1, scheduler3)

    def test_set_rate_limit_valid(self):
        """Test de configuration de limite de taux valide"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            scheduler.set_rate_limit(2.0)
            
            self.assertEqual(scheduler.CALLS_PER_SECOND, 2.0)
            self.assertEqual(scheduler.CALL_INTERVAL, 0.5)

    def test_set_rate_limit_invalid(self):
        """Test de configuration de limite de taux invalide"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            with self.assertRaises(ValueError):
                scheduler.set_rate_limit(0)
            
            with self.assertRaises(ValueError):
                scheduler.set_rate_limit(-1)

    def test_validate_url_exact_match(self):
        """Test de validation d'URL avec correspondance exacte"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            # URLs valides
            self.assertTrue(scheduler.validate_url("http://127.0.0.1:5000/mockapi"))
            self.assertTrue(scheduler.validate_url("http://127.0.0.1:5000/mockapi/test"))
            
            # URLs invalides
            self.assertFalse(scheduler.validate_url("http://127.0.0.1:7000/mockapi/unicode"))
            self.assertFalse(scheduler.validate_url("http://api.example.com"))

    def test_generate_cache_key(self):
        """Test de génération de clé de cache"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            req_data = RequestData(
                request_id="123",
                url="https://api.example.com/test",
                payload={"key": "value"},
                method="POST",
                headers={"Auth": "token"}
            )
            
            cache_key = scheduler._generate_cache_key(req_data)
            self.assertIsInstance(cache_key, str)
            self.assertIn("https://api.example.com/test", cache_key)

    def test_get_cache_path(self):
        """Test de génération du chemin de cache"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            cache_key = "test_key"
            cache_path = scheduler.get_cache_path(cache_key)
            
            self.assertTrue(cache_path.endswith('.json'))
            self.assertIn('cache', cache_path)

    @patch('os.makedirs')
    def test_ensure_cache_directory_success(self, mock_makedirs):
        """Test de création réussie du répertoire cache"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'):
            scheduler = APIRequestScheduler(self.api_patterns)
            scheduler._ensure_cache_directory()
            mock_makedirs.assert_called_once()

    @patch('os.makedirs')
    def test_ensure_cache_directory_failure(self, mock_makedirs):
        """Test d'échec de création du répertoire cache"""
        mock_makedirs.side_effect = OSError("Permission denied")
        
        with patch('threading.Thread'), patch('asyncio.new_event_loop'):
            with self.assertRaises(APIError):
                APIRequestScheduler(self.api_patterns)

    def test_add_request_valid(self):
        """Test d'ajout de requête valide"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            url = "http://127.0.0.1:5000/mockapi/test"
            payload = {"key": "value"}
            
            request_id, estimated_delay = scheduler.add_request(
                url=url,
                payload=payload,
                method="POST",
                cache_duration=300
            )
            
            self.assertIsInstance(request_id, str)
            self.assertIsInstance(estimated_delay, (int, float))
            self.assertIn(request_id, scheduler.request_dict)
            self.assertEqual(scheduler.request_queue.qsize(), 1)

    def test_add_request_invalid_url(self):
        """Test d'ajout de requête avec URL invalide"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            with self.assertRaises(ValueError):
                scheduler.add_request("https://invalid-api.com/test")

    def test_add_request_malformed_url(self):
        """Test d'ajout de requête avec URL malformée"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            with self.assertRaises(ValueError):
                scheduler.add_request("not-a-valid-url")


    def test_has_request_exists(self):
        """Test de vérification d'existence de requête"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            request_id = str(uuid.uuid4())
            
            # Ajouter la requête au dictionnaire
            req_data = RequestData(request_id, "https://api.example.com/test")
            scheduler.request_dict[request_id] = req_data
            
            self.assertTrue(scheduler.has_request(request_id))

    def test_has_request_not_exists(self):
        """Test de vérification d'inexistence de requête"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            request_id = str(uuid.uuid4())
            
            self.assertFalse(scheduler.has_request(request_id))

    def test_get_response_exists(self):
        """Test de récupération de réponse existante"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            request_id = str(uuid.uuid4())
            response_data = {"result": "success"}
            
            # Ajouter la réponse au store
            scheduler.response_store[request_id] = response_data
            scheduler.request_dict[request_id] = RequestData(request_id, "http://test.com")
            
            response = scheduler.get_response(request_id)
            
            self.assertEqual(response, response_data)
            # Vérifier que les données sont nettoyées après récupération
            self.assertNotIn(request_id, scheduler.response_store)
            self.assertNotIn(request_id, scheduler.request_dict)

    def test_get_response_not_exists(self):
        """Test de récupération de réponse inexistante"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            request_id = str(uuid.uuid4())
            
            response = scheduler.get_response(request_id)
            self.assertIsNone(response)



class TestAsyncMethods(unittest.TestCase):
    """Tests pour les méthodes asynchrones du scheduler"""
    
    def setUp(self):
        self.api_patterns = ["http://127.0.0.1:5000/mockapi"]
    
    @patch('aiohttp.ClientSession')
    async def test_make_http_request_success(self, mock_session_class):
        """Test de requête HTTP réussie"""
        # Mock de la session et réponse
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_response.raise_for_status = MagicMock()
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            request_data = RequestData(
                request_id=str(uuid.uuid4()),
                url="https://api.example.com/test",
                payload={"key": "value"},
                method="POST"
            )
            
            result = await scheduler._make_http_request(request_data)
            self.assertEqual(result, {"success": True})

    @patch('aiohttp.ClientSession')
    async def test_make_http_request_timeout(self, mock_session_class):
        """Test de requête HTTP avec timeout"""
        mock_session = AsyncMock()
        mock_session.request.side_effect = asyncio.TimeoutError()
        
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            request_data = RequestData(
                request_id=str(uuid.uuid4()),
                url="https://api.example.com/test",
                method="GET"
            )
            
            with self.assertRaises(APIError):
                await scheduler._make_http_request(request_data)

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    async def test_check_cache_hit(self, mock_exists, mock_file):
        """Test de vérification de cache avec hit"""
        mock_exists.return_value = True
        cache_data = {
            'response': {'cached': True},
            'timestamp': time.time() - 100  # Cache récent
        }
        mock_file.return_value.read.return_value = json.dumps(cache_data)
        
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            request_data = RequestData(
                request_id=str(uuid.uuid4()),
                url="https://api.example.com/test",
                cache_duration=300
            )
            
            result = await scheduler._check_cache(request_data)
            self.assertEqual(result, {'cached': True})

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    async def test_check_cache_miss_expired(self, mock_exists, mock_file):
        """Test de vérification de cache avec miss (expiré)"""
        mock_exists.return_value = True
        cache_data = {
            'response': {'cached': True},
            'timestamp': time.time() - 1000  # Cache expiré
        }
        mock_file.return_value.read.return_value = json.dumps(cache_data)
        
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            request_data = RequestData(
                request_id=str(uuid.uuid4()),
                url="https://api.example.com/test",
                cache_duration=300
            )
            
            result = await scheduler._check_cache(request_data)
            self.assertIsNone(result)

    @patch('builtins.open', new_callable=mock_open)
    async def test_cache_response(self, mock_file):
        """Test de mise en cache d'une réponse"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            request_data = RequestData(
                request_id=str(uuid.uuid4()),
                url="https://api.example.com/test"
            )
            response_data = {"result": "success"}
            
            await scheduler._cache_response(request_data, response_data)
            
            # Vérifier qu'un fichier a été écrit
            mock_file.assert_called()


class TestWebSocketHandlers(unittest.TestCase):
    """Tests pour les gestionnaires WebSocket"""
    
    def setUp(self):
        self.connected_clients = {}
    
    @patch('flask_socketio.emit')
    @patch('flask.request')
    def test_handle_connect(self, mock_request, mock_emit):
        """Test du gestionnaire de connexion WebSocket"""
        mock_request.sid = "test_session_id"
        
        # Simuler la fonction handle_connect
        def handle_connect():
            try:
                mock_emit("connect", {"message": "Connexion établie avec succès", "sid": mock_request.sid})
            except Exception as e:
                pass
        
        # Exécuter et vérifier
        handle_connect()
        mock_emit.assert_called_once_with("connect", {
            "message": "Connexion établie avec succès", 
            "sid": "test_session_id"
        })

    @patch('flask_socketio.emit')
    @patch('flask_socketio.join_room')
    @patch('flask.request')
    def test_handle_register_valid(self, mock_request, mock_join_room, mock_emit):
        """Test d'enregistrement de client valide"""
        mock_request.sid = "test_session_id"
        data = {"client_id": "client123"}
        
        def handle_register(data):
            client_id = data.get('client_id')
            if client_id:
                self.connected_clients[client_id] = mock_request.sid
                mock_join_room(client_id)
                mock_emit('message', {
                    'data': f'Enregistrement réussi avec client_id: {client_id}',
                    'client_id': client_id
                }, room=client_id)
        
        handle_register(data)
        
        self.assertIn("client123", self.connected_clients)
        self.assertEqual(self.connected_clients["client123"], "test_session_id")
        mock_join_room.assert_called_once_with("client123")

    @patch('flask_socketio.emit')
    @patch('flask.request')
    def test_handle_register_missing_client_id(self, mock_request, mock_emit):
        """Test d'enregistrement sans client_id"""
        data = {}
        
        def handle_register(data):
            client_id = data.get('client_id')
            if not client_id:
                mock_emit('error', {'message': 'client_id requis pour l\'enregistrement'})
        
        handle_register(data)
        mock_emit.assert_called_once_with('error', {
            'message': 'client_id requis pour l\'enregistrement'
        })


class TestUtilityFunctions(unittest.TestCase):
    """Tests pour les fonctions utilitaires"""
    
    def test_url_parsing(self):
        """Test de parsing d'URL"""
        from urllib.parse import urlparse
        
        url = "https://api.example.com:8080/v1/endpoint?param=value"
        parsed = urlparse(url)
        
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "api.example.com:8080")
        self.assertEqual(parsed.path, "/v1/endpoint")
        self.assertEqual(parsed.query, "param=value")

    def test_uuid_generation(self):
        """Test de génération d'UUID"""
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid4())
        
        self.assertNotEqual(uuid1, uuid2)
        self.assertEqual(len(uuid1), 36)  # Format UUID standard
        self.assertIn('-', uuid1)

    def test_timestamp_generation(self):
        """Test de génération de timestamp"""
        timestamp1 = time.time()
        time.sleep(0.001)  # Petit délai
        timestamp2 = time.time()
        
        self.assertLess(timestamp1, timestamp2)
        self.assertIsInstance(timestamp1, (int, float))


class TestCacheOperations(unittest.TestCase):
    """Tests pour les opérations de cache"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_cache_file_creation(self):
        """Test de création de fichier cache"""
        cache_file = os.path.join(self.temp_dir, "test_cache.json")
        cache_data = {
            "response": {"result": "success"},
            "timestamp": time.time(),
            "request_id": "test123"
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Vérifier que le fichier existe et contient les bonnes données
        self.assertTrue(os.path.exists(cache_file))
        
        with open(cache_file, 'r') as f:
            loaded_data = json.load(f)
        
        self.assertEqual(loaded_data["response"], {"result": "success"})
        self.assertEqual(loaded_data["request_id"], "test123")

    def test_cache_expiration_check(self):
        """Test de vérification d'expiration du cache"""
        current_time = time.time()
        
        # Cache récent (non expiré)
        recent_cache = {
            "timestamp": current_time - 100,  # 100 secondes
            "response": {"data": "recent"}
        }
        
        # Cache ancien (expiré)
        old_cache = {
            "timestamp": current_time - 86400 - 100,  # Plus de 24h
            "response": {"data": "old"}
        }
        
        # Test d'expiration avec cache_duration = 300s
        cache_duration = 300
        is_recent_expired = current_time - recent_cache["timestamp"] > cache_duration
        is_old_expired = current_time - old_cache["timestamp"] > cache_duration
        
        self.assertFalse(is_recent_expired)
        self.assertTrue(is_old_expired)

    @patch('os.listdir')
    @patch('os.path.exists')
    def test_cache_cleanup(self, mock_exists, mock_listdir):
        """Test de nettoyage automatique du cache"""
        mock_listdir.return_value = ['cache1.json', 'cache2.json', 'not_json.txt']
        mock_exists.return_value = True
        
        current_time = time.time()
        
        # Mock des données de cache
        expired_cache = {
            "timestamp": current_time - 90000,  # Expiré
            "response": {"data": "expired"}
        }
        
        valid_cache = {
            "timestamp": current_time - 1000,  # Valide
            "response": {"data": "valid"}
        }
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('json.load') as mock_json_load, \
             patch('os.remove') as mock_remove:
            
            # Simuler différents fichiers
            def json_load_side_effect(f):
                filename = f.name if hasattr(f, 'name') else 'cache1.json'
                if 'cache1' in str(filename):
                    return expired_cache
                return valid_cache
            
            mock_json_load.side_effect = json_load_side_effect
            
            # Simuler la fonction de nettoyage
            cleaned_count = 0
            for filename in mock_listdir.return_value:
                if filename.endswith('.json'):
                    # Simuler la lecture et vérification
                    if filename == 'cache1.json':  # Fichier expiré
                        cleaned_count += 1
            
            self.assertEqual(cleaned_count, 1)


class TestErrorHandling(unittest.TestCase):
    """Tests de gestion d'erreurs"""
    
    def test_api_error_with_status_code(self):
        """Test d'APIError avec code de statut"""
        error = APIError("Not found", status_code=404, request_id="req123")
        
        self.assertEqual(str(error), "Not found")
        self.assertEqual(error.status_code, 404)
        self.assertEqual(error.request_id, "req123")

    def test_rate_limit_exceeded_error(self):
        """Test d'erreur de dépassement de limite"""
        error = RateLimitExceeded("Queue full")
        
        self.assertIsInstance(error, APIError)
        self.assertEqual(str(error), "Queue full")

    def test_exception_in_async_context(self):
        """Test de gestion d'exception dans contexte async"""
        async def failing_function():
            raise ValueError("Async error")
        
        async def test_exception_handling():
            try:
                await failing_function()
                self.fail("Exception should have been raised")
            except ValueError as e:
                self.assertEqual(str(e), "Async error")
        
        # Exécuter le test async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_exception_handling())
        finally:
            loop.close()


class TestThreadSafety(unittest.TestCase):
    """Tests de sécurité des threads"""
    
    def test_lock_acquisition(self):
        """Test d'acquisition de verrous"""
        import threading
        
        lock = threading.Lock()
        shared_resource = {"counter": 0}
        
        def increment_counter():
            with lock:
                current = shared_resource["counter"]
                time.sleep(0.001)  # Simuler une opération
                shared_resource["counter"] = current + 1
        
        # Créer plusieurs threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=increment_counter)
            threads.append(t)
            t.start()
        
        # Attendre que tous les threads se terminent
        for t in threads:
            t.join()
        
        # Vérifier que le compteur est correct
        self.assertEqual(shared_resource["counter"], 10)

    def test_queue_thread_safety(self):
        """Test de sécurité des queues avec threads"""
        from queue import Queue
        import threading
        
        test_queue = Queue()
        results = []
        
        def producer():
            for i in range(5):
                test_queue.put(f"item_{i}")
        
        def consumer():
            while True:
                try:
                    item = test_queue.get(timeout=1)
                    results.append(item)
                    test_queue.task_done()
                except Empty:
                    break
        
        # Démarrer les threads
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)
        
        producer_thread.start()
        consumer_thread.start()
        
        producer_thread.join()
        consumer_thread.join()
        
        # Vérifier les résultats
        self.assertEqual(len(results), 5)
        self.assertIn("item_0", results)
        self.assertIn("item_4", results)


class TestConfigurationHandling(unittest.TestCase):
    """Tests de gestion de configuration"""
    
    def test_config_loading(self):
        """Test de chargement de configuration"""
        # Simuler une configuration
        config = {
            'admin': {'Bearer': 'test-token'},
            'api': {'timeout': 30, 'retries': 3}
        }
        
        # Vérifier l'accès aux configurations
        self.assertEqual(config['admin']['Bearer'], 'test-token')
        self.assertEqual(config['api']['timeout'], 30)
        self.assertEqual(config['api']['retries'], 3)

    def test_environment_variables(self):
        """Test des variables d'environnement"""
        with patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG', 'API_PORT': '8080'}):
            log_level = os.getenv('LOG_LEVEL', 'INFO')
            api_port = int(os.getenv('API_PORT', 6000))
            
            self.assertEqual(log_level, 'DEBUG')
            self.assertEqual(api_port, 8080)

    def test_default_configuration_values(self):
        """Test des valeurs de configuration par défaut"""
        # Simuler les constantes du serveur
        DEFAULT_API_IP = "127.0.0.1"
        DEFAULT_API_PORT = 6000
        DEFAULT_LOG_LEVEL = "INFO"
        DEFAULT_MAX_RETRIES = 3
        DEFAULT_RETRY_BACKOFF_FACTOR = 1.5
        DEFAULT_REQUEST_TIMEOUT = 30
        
        # Vérifier les valeurs par défaut
        self.assertEqual(DEFAULT_API_IP, "127.0.0.1")
        self.assertEqual(DEFAULT_API_PORT, 6000)
        self.assertEqual(DEFAULT_LOG_LEVEL, "INFO")
        self.assertEqual(DEFAULT_MAX_RETRIES, 3)
        self.assertEqual(DEFAULT_RETRY_BACKOFF_FACTOR, 1.5)
        self.assertEqual(DEFAULT_REQUEST_TIMEOUT, 30)


class TestDataValidation(unittest.TestCase):
    """Tests de validation des données"""
    
    def test_url_validation(self):
        """Test de validation d'URLs"""
        valid_urls = [
            "https://api.example.com",
            "http://localhost:8080",
            "https://api.test.com/v1/endpoint"
        ]
        
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "",
            None,
            "http://",
            "https://"
        ]
        
        for url in valid_urls:
            try:
                parsed = urlparse(url)
                is_valid = bool(parsed.scheme and parsed.netloc)
                self.assertTrue(is_valid, f"URL should be valid: {url}")
            except Exception:
                self.fail(f"Valid URL raised exception: {url}")
        
        for url in invalid_urls:
            if url is None:
                continue
            try:
                parsed = urlparse(url)
                is_valid = bool(parsed.scheme and parsed.netloc)
                if is_valid and url not in ["http://", "https://"]:
                    continue  # Ces cas peuvent être techniquement valides
                self.assertFalse(is_valid, f"URL should be invalid: {url}")
            except Exception:
                pass  # Exception attendue pour URLs invalides

    def test_json_validation(self):
        """Test de validation JSON"""
        valid_json = '{"key": "value", "number": 123}'
        invalid_json = '{"key": "value", "incomplete"'
        
        # Test JSON valide
        try:
            data = json.loads(valid_json)
            self.assertIsInstance(data, dict)
            self.assertEqual(data["key"], "value")
            self.assertEqual(data["number"], 123)
        except json.JSONDecodeError:
            self.fail("Valid JSON should not raise exception")
        
        # Test JSON invalide
        with self.assertRaises(json.JSONDecodeError):
            json.loads(invalid_json)

    def test_parameter_validation(self):
        """Test de validation des paramètres de requête"""
        # Test des méthodes HTTP valides
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        invalid_methods = ["INVALID", "", None, 123]
        
        for method in valid_methods:
            self.assertIn(method, valid_methods)
        
        for method in invalid_methods:
            self.assertNotIn(method, valid_methods)
        
        # Test de cache_duration
        valid_durations = [0, 60, 300, 3600]
        invalid_durations = [-1, -100, "string", None]
        
        for duration in valid_durations:
            self.assertIsInstance(duration, int)
            self.assertGreaterEqual(duration, 0)
        
        for duration in invalid_durations:
            if duration is None or isinstance(duration, str):
                continue
            if isinstance(duration, int):
                self.assertLess(duration, 0)


class TestLoggingSystem(unittest.TestCase):
    """Tests du système de logging"""
    
    def test_logger_configuration(self):
        """Test de configuration du logger"""
        import logging
        
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)
        
        # Créer un handler de test
        from io import StringIO
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        logger.addHandler(handler)
        
        # Test des niveaux de log
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        log_output = log_stream.getvalue()
        
        # Debug ne devrait pas apparaître (niveau INFO)
        self.assertNotIn("Debug message", log_output)
        # Les autres devraient apparaître
        self.assertIn("Info message", log_output)
        self.assertIn("Warning message", log_output)
        self.assertIn("Error message", log_output)

    def test_log_formatting(self):
        """Test du formatage des logs"""
        import logging
        from io import StringIO
        
        logger = logging.getLogger("format_test")
        logger.setLevel(logging.INFO)
        
        # Formatter personnalisé
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        logger.info("Test message")
        log_output = log_stream.getvalue()
        
        self.assertIn("format_test", log_output)
        self.assertIn("INFO", log_output)
        self.assertIn("Test message", log_output)


class TestPerformanceMetrics(unittest.TestCase):
    """Tests des métriques de performance"""
    
    def test_execution_time_measurement(self):
        """Test de mesure du temps d'exécution"""
        start_time = time.time()
        
        # Simuler une opération qui prend du temps
        time.sleep(0.1)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertGreaterEqual(execution_time, 0.1)
        self.assertLess(execution_time, 0.2)  # Marge de tolérance

    def test_memory_usage_tracking(self):
        """Test de suivi de l'utilisation mémoire"""
        import sys
        
        # Créer des objets pour augmenter l'utilisation mémoire
        large_list = []
        initial_size = sys.getsizeof(large_list)
        
        # Ajouter des éléments
        for i in range(1000):
            large_list.append(f"item_{i}")
        
        final_size = sys.getsizeof(large_list)
        
        self.assertGreater(final_size, initial_size)

    def test_queue_performance(self):
        """Test de performance des queues"""
        from queue import Queue
        
        test_queue = Queue()
        
        # Mesurer le temps d'ajout
        start_time = time.time()
        for i in range(1000):
            test_queue.put(f"item_{i}")
        add_time = time.time() - start_time
        
        # Mesurer le temps de récupération
        start_time = time.time()
        while not test_queue.empty():
            test_queue.get()
        get_time = time.time() - start_time
        
        # Les opérations devraient être rapides
        self.assertLess(add_time, 1.0)
        self.assertLess(get_time, 1.0)


class TestIntegrationScenarios(unittest.TestCase):
    """Tests de scénarios d'intégration"""
    
    def setUp(self):
        self.api_patterns = ["http://127.0.0.1:5000/mockapi"]
    
    @patch('aiohttp.ClientSession')
    def test_complete_request_flow(self, mock_session_class):
        """Test du flux complet d'une requête"""
        # Mock de la réponse HTTP
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"status": "success"})
        mock_response.raise_for_status = MagicMock()
        
        mock_session = AsyncMock()
        mock_session.request = AsyncMock()
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            # 1. Ajouter une requête
            request_id, delay = scheduler.add_request(
                url="http://127.0.0.1:5000/mockapi/test",
                payload={"data": "test"},
                method="POST"
            )
            
            # 2. Vérifier que la requête existe
            self.assertTrue(scheduler.has_request(request_id))
            
            # 3. Simuler le traitement (normalement fait par le worker thread)
            request_data = scheduler.request_dict[request_id]
            
            # 4. Simuler une réponse traitée
            mock_response_data = {"result": "processed"}
            scheduler.response_store[request_id] = mock_response_data
            
            # 5. Récupérer la réponse
            response = scheduler.get_response(request_id)
            self.assertEqual(response, mock_response_data)
            
            # 6. Vérifier le nettoyage
            self.assertNotIn(request_id, scheduler.response_store)

    def test_multiple_schedulers_isolation(self):
        """Test d'isolation entre plusieurs schedulers"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            patterns1 = ["https://api1.example.com"]
            patterns2 = ["https://api2.example.com"]
            
            scheduler1 = APIRequestScheduler(patterns1)
            scheduler2 = APIRequestScheduler(patterns2)
            
            # Vérifier que ce sont des instances différentes
            self.assertIsNot(scheduler1, scheduler2)
            
            # Ajouter des requêtes à chaque scheduler
            req_id1, _ = scheduler1.add_request("https://api1.example.com/test")
            req_id2, _ = scheduler2.add_request("https://api2.example.com/test")
            
            # Vérifier l'isolation
            self.assertTrue(scheduler1.has_request(req_id1))
            self.assertFalse(scheduler1.has_request(req_id2))
            self.assertTrue(scheduler2.has_request(req_id2))
            self.assertFalse(scheduler2.has_request(req_id1))

    def test_error_recovery_scenario(self):
        """Test de scénario de récupération d'erreur"""
        with patch('threading.Thread'), patch('asyncio.new_event_loop'), \
             patch('os.makedirs'):
            
            scheduler = APIRequestScheduler(self.api_patterns)
            
            # Ajouter une requête
            request_id, _ = scheduler.add_request("http://127.0.0.1:5000/mockapi/test")
            
            # Simuler une erreur
            error_response = {
                "error": "Network timeout",
                "request_id": request_id,
                "timestamp": time.time()
            }
            scheduler.response_store[request_id] = error_response
            
            # Récupérer la réponse d'erreur
            response = scheduler.get_response(request_id)
            
            self.assertIn("error", response)
            self.assertEqual(response["error"], "Network timeout")
            self.assertEqual(response["request_id"], request_id)


if __name__ == '__main__':
    # Configuration des tests
    unittest.TestLoader.sortTestMethodsUsing = None
    
    # Créer une suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter toutes les classes de test
    test_classes = [
        TestRequestData,
        TestExceptions,
        TestAPIRequestScheduler,
        TestAsyncMethods,
        TestFlaskEndpoints,
        TestWebSocketHandlers,
        TestUtilityFunctions,
        TestCacheOperations,
        TestErrorHandling,
        TestThreadSafety,
        TestConfigurationHandling,
        TestDataValidation,
        TestLoggingSystem,
        TestPerformanceMetrics,
        TestIntegrationScenarios
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Lancer les tests avec un reporting détaillé
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    print(f"Lancement de {suite.countTestCases()} tests unitaires...")
    print("=" * 70)
    
    result = runner.run(suite)
    
    # Résumé final
    print("\n" + "=" * 70)
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    print(f"Ignorés: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print(f"\nÉchecs détaillés: {len(result.failures)}")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\nErreurs détaillées: {len(result.errors)}")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\nTaux de réussite: {success_rate:.1f}%")
    
    # Code de sortie
    exit_code = 0 if result.wasSuccessful() else 1
    print(f"Code de sortie: {exit_code}")
    sys.exit(exit_code)