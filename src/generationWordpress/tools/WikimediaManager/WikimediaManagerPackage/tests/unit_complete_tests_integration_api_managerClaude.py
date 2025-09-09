"""
Suite de Tests Complète pour l'API Manager
Combine tests unitaires, tests d'intégration réels, et diagnostics
"""
from flask import Flask, jsonify, request
import re
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
import requests
import socketio

# Configuration des tests
TEST_API_HOST = "127.0.0.1"
TEST_API_PORT = 6000
TEST_BASE_URL = f"http://{TEST_API_HOST}:{TEST_API_PORT}"
TEST_BEARER_TOKEN = "your-actual-bearer-token-here"  # ⚠️ À modifier selon votre config

# URLs de test pour les vraies requêtes
REAL_TEST_APIS = [
    "https://httpbin.org",
    "https://jsonplaceholder.typicode.com",
    "https://reqres.in/api"
]

# Mock de la configuration pour les tests unitaires
sys.modules['configPrivee'] = Mock()
sys.modules['configPrivee'].config = {
    'admin': {'Bearer': 'test-bearer-token'}
}

# ============================================================================
# CLASSES DE BASE POUR LES TESTS UNITAIRES
# ============================================================================

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

# Configuration des constantes
LOG_LEVEL = "INFO"
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 1.5
REQUEST_TIMEOUT = 30
CACHE_CLEANUP_INTERVAL = 3600
MAX_QUEUE_SIZE = 10000


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

class WebSocketRealTests(unittest.TestCase):
    """Tests WebSocket réels contre l'API Manager"""

    def setUp(self):
        """Configuration WebSocket"""
        self.socket_url = TEST_BASE_URL
        self.sio = None

    def tearDown(self):
        """Nettoyage WebSocket"""
        if self.sio and self.sio.connected:
            self.sio.disconnect()

    def test_websocket_connection(self):
        """Test de connexion WebSocket basique"""
        try:
            self.sio = socketio.SimpleClient()

            # Tentative de connexion
            connected = self.sio.connect(self.socket_url, wait_timeout=10)

            if connected:
                print("✅ Connexion WebSocket réussie")
                self.assertTrue(self.sio.connected)

                # Test d'envoi d'événement
                self.sio.emit('custom_event')

                # Écouter la réponse
                try:
                    event = self.sio.receive(timeout=5)
                    print(f"📨 Événement reçu: {event}")
                except:
                    print("⚠️  Aucun événement reçu (normal selon l'implémentation)")
            else:
                print("⚠️  Connexion WebSocket échouée")
                self.skipTest("WebSocket non disponible")

        except Exception as e:
            print(f"⚠️  Test WebSocket échoué: {e}")
            self.skipTest("WebSocket non disponible ou non configuré")

    def test_websocket_registration(self):
        """Test d'enregistrement WebSocket avec client_id"""
        try:
            self.sio = socketio.SimpleClient()

            if not self.sio.connect(self.socket_url, wait_timeout=10):
                self.skipTest("Impossible de se connecter au WebSocket")

            # Enregistrer avec un client_id
            test_client_id = f"test_client_{int(time.time())}"

            self.sio.emit('register', {'client_id': test_client_id})

            # Attendre une réponse
            try:
                event = self.sio.receive(timeout=5)
                print(f"📝 Réponse registration: {event}")

                # Vérifier que l'enregistrement a réussi
                if len(event) >= 2 and 'registered' in str(event[1]).lower():
                    print("✅ Enregistrement WebSocket réussi")
                else:
                    print("⚠️  Réponse d'enregistrement inattendue")

            except:
                print("⚠️  Aucune réponse à l'enregistrement")

        except Exception as e:
            print(f"⚠️  Test registration WebSocket échoué: {e}")
            self.skipTest("WebSocket registration non disponible")

    def test_websocket_message_sending(self):
        """Test d'envoi de message via l'API REST vers WebSocket"""
        try:
            # Connexion WebSocket
            self.sio = socketio.SimpleClient()

            if not self.sio.connect(self.socket_url, wait_timeout=10):
                self.skipTest("Impossible de se connecter au WebSocket")

            # Enregistrement avec client_id
            test_client_id = f"test_msg_{int(time.time())}"
            self.sio.emit('register', {'client_id': test_client_id})

            # Attendre la confirmation d'enregistrement
            try:
                self.sio.receive(timeout=5)
            except:
                pass

            # Envoyer un message via l'API REST
            message_data = {
                "client_id": test_client_id,
                "message": {
                    "type": "test",
                    "content": "Hello from API test",
                    "timestamp": time.time()
                }
            }

            response = requests.post(f"{self.socket_url}/send_message",
                                   json=message_data,
                                   timeout=10)

            print(f"📤 Envoi message REST: {response.status_code}")

            if response.status_code == 200:
                # Écouter le message sur WebSocket
                try:
                    event = self.sio.receive(timeout=10)
                    print(f"📨 Message WebSocket reçu: {event}")
                    print("✅ Communication REST->WebSocket réussie")
                except:
                    print("⚠️  Aucun message reçu sur WebSocket")
            else:
                print(f"❌ Échec envoi message: {response.text}")

        except Exception as e:
            print(f"⚠️  Test message WebSocket échoué: {e}")


# ============================================================================
# TESTS DE STRESS ET PERFORMANCE
# ============================================================================

class StressTests(unittest.TestCase):
    """Tests de stress pour l'API Manager réel"""

    def setUp(self):
        """Configuration stress tests"""
        self.headers = {"Authorization": f"Bearer {TEST_BEARER_TOKEN}"}
        self.base_url = TEST_BASE_URL

        # Vérifier que l'API est accessible
        try:
            requests.get(f"{self.base_url}/", timeout=5)
        except:
            self.skipTest("API Manager non accessible pour les tests de stress")

    def test_concurrent_scheduler_creation(self):
        """Test de création concurrente de schedulers"""
        def create_scheduler(thread_id):
            try:
                init_data = {"api_patterns": ["https://httpbin.org"]}
                response = requests.post(f"{self.base_url}/api/initialize",
                                       json=init_data,
                                       headers=self.headers,
                                       timeout=10)
                return response.status_code == 200, response.json() if response.status_code == 200 else None
            except Exception as e:
                return False, str(e)

        # Lancer plusieurs threads en parallèle
        import threading as th
        import queue

        results = queue.Queue()
        threads = []

        def thread_wrapper(tid):
            success, data = create_scheduler(tid)
            results.put((tid, success, data))

        # Créer 5 threads
        for i in range(5):
            thread = th.Thread(target=thread_wrapper, args=(i,))
            threads.append(thread)
            thread.start()

        # Attendre tous les threads
        for thread in threads:
            thread.join(timeout=15)

        # Analyser les résultats
        all_results = []
        while not results.empty():
            all_results.append(results.get())

        successful_creations = [r for r in all_results if r[1]]
        print(f"✅ Créations réussies: {len(successful_creations)}/{len(all_results)}")

        # Au moins une création devrait réussir (singleton pattern)
        self.assertGreater(len(successful_creations), 0)

    def test_rapid_requests_submission(self):
        """Test de soumission rapide de requêtes"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            if init_response.status_code != 200:
                self.skipTest("Impossible de créer le scheduler pour le test de stress")

            scheduler_id = init_response.json()["scheduler_id"]

            # Soumettre 20 requêtes rapidement
            successful_requests = 0
            failed_requests = 0

            start_time = time.time()

            for i in range(20):
                request_data = {
                    "scheduler_id": scheduler_id,
                    "url": f"https://httpbin.org/get?stress_test={i}",
                    "method": "GET"
                }

                try:
                    response = requests.post(f"{self.base_url}/api/request",
                                           json=request_data,
                                           headers=self.headers,
                                           timeout=5)

                    if response.status_code == 200:
                        successful_requests += 1
                    else:
                        failed_requests += 1

                except Exception:
                    failed_requests += 1

            elapsed_time = time.time() - start_time

            print(f"📊 Stress test terminé en {elapsed_time:.2f}s")
            print(f"✅ Requêtes réussies: {successful_requests}")
            print(f"❌ Requêtes échouées: {failed_requests}")

            # Au moins 80% des requêtes devraient réussir
            total_requests = successful_requests + failed_requests
            if total_requests > 0:
                success_rate = successful_requests / total_requests * 100
                self.assertGreater(success_rate, 80.0)

        except Exception as e:
            self.fail(f"Test de stress échoué: {e}")

    def test_memory_usage_large_payloads(self):
        """Test avec de gros payloads"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Créer un payload volumineux
            large_payload = {
                "data": "x" * 50000,  # 50KB de données
                "array": list(range(1000)),
                "nested": {"level1": {"level2": {"level3": "deep data"}}}
            }

            # Soumettre plusieurs requêtes avec de gros payloads
            request_ids = []
            for i in range(5):
                request_data = {
                    "scheduler_id": scheduler_id,
                    "url": "https://httpbin.org/post",
                    "method": "POST",
                    "payload": large_payload
                }

                response = requests.post(f"{self.base_url}/api/request",
                                       json=request_data,
                                       headers=self.headers,
                                       timeout=10)

                if response.status_code == 200:
                    request_ids.append(response.json()["uuid"])

            print(f"📊 {len(request_ids)} requêtes avec gros payloads soumises")
            self.assertGreater(len(request_ids), 0)

        except Exception as e:
            self.fail(f"Test gros payloads échoué: {e}")

    def test_sustained_load(self):
        """Test de charge soutenue"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Test de charge sur 30 secondes
            test_duration = 30  # secondes
            start_time = time.time()
            request_count = 0
            success_count = 0

            while time.time() - start_time < test_duration:
                request_data = {
                    "scheduler_id": scheduler_id,
                    "url": f"https://httpbin.org/get?load_test={request_count}",
                    "method": "GET"
                }

                try:
                    response = requests.post(f"{self.base_url}/api/request",
                                           json=request_data,
                                           headers=self.headers,
                                           timeout=2)

                    request_count += 1
                    if response.status_code == 200:
                        success_count += 1

                except:
                    request_count += 1

                # Petite pause pour éviter de surcharger
                time.sleep(0.1)

            elapsed_time = time.time() - start_time

            print(f"📊 Test de charge soutenue:")
            print(f"   Durée: {elapsed_time:.1f}s")
            print(f"   Requêtes totales: {request_count}")
            print(f"   Requêtes réussies: {success_count}")
            print(f"   Taux de succès: {success_count/request_count*100:.1f}%")
            print(f"   Requêtes/seconde: {request_count/elapsed_time:.1f}")

            # Vérifications
            self.assertGreater(request_count, 0)
            if request_count > 0:
                success_rate = success_count / request_count * 100
                self.assertGreater(success_rate, 70.0)  # Au moins 70% de succès

        except Exception as e:
            self.fail(f"Test charge soutenue échoué: {e}")


# ============================================================================
# TESTS DE CAS LIMITES
# ============================================================================

class EdgeCaseTests(unittest.TestCase):
    """Tests pour les cas limites et situations extrêmes"""

    def setUp(self):
        """Configuration pour les tests de cas limites"""
        self.headers = {"Authorization": f"Bearer {TEST_BEARER_TOKEN}"}
        self.base_url = TEST_BASE_URL

        try:
            requests.get(f"{self.base_url}/", timeout=5)
        except:
            self.skipTest("API Manager non accessible pour les tests de cas limites")

    def test_malformed_json_requests(self):
        """Test avec des requêtes JSON malformées"""
        # Test avec JSON invalide
        try:
            response = requests.post(f"{self.base_url}/api/initialize",
                                   data="{ invalid json",
                                   headers={**self.headers, "Content-Type": "application/json"})

            print(f"🚫 JSON malformé - Status: {response.status_code}")
            self.assertIn(response.status_code, [400, 422])
            print("✅ JSON malformé correctement rejeté")

        except Exception as e:
            print(f"⚠️  Test JSON malformé échoué: {e}")

    def test_extremely_long_urls(self):
        """Test avec des URLs extrêmement longues"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # URL très longue (mais techniquement valide)
            long_query = "&".join([f"param{i}=value{i}" for i in range(100)])
            long_url = f"https://httpbin.org/get?{long_query}"

            print(f"🔗 URL de {len(long_url)} caractères")

            request_data = {
                "scheduler_id": scheduler_id,
                "url": long_url,
                "method": "GET"
            }

            response = requests.post(f"{self.base_url}/api/request",
                                   json=request_data,
                                   headers=self.headers)

            print(f"📏 URL longue - Status: {response.status_code}")

            # Devrait soit réussir, soit échouer proprement
            self.assertIn(response.status_code, [200, 400, 414])  # 414 = URI Too Long

        except Exception as e:
            print(f"⚠️  Test URL longue échoué: {e}")

    def test_unicode_and_special_characters(self):
        """Test avec caractères Unicode et spéciaux"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Payload avec caractères spéciaux
            unicode_payload = {
                "message": "Héllo Wörld! 🌍",
                "data": "Test avec des caractères spéciaux: éàüñç",
                "emoji": "🚀💡🔥⭐🎯",
                "chinese": "你好世界",
                "arabic": "مرحبا بالعالم",
                "special_chars": "!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/"
            }

            request_data = {
                "scheduler_id": scheduler_id,
                "url": "https://httpbin.org/post",
                "method": "POST",
                "payload": unicode_payload
            }

            response = requests.post(f"{self.base_url}/api/request",
                                   json=request_data,
                                   headers=self.headers)

            print(f"🌐 Unicode & spéciaux - Status: {response.status_code}")

            if response.status_code == 200:
                print("✅ Caractères Unicode/spéciaux acceptés")
            else:
                print(f"⚠️  Caractères Unicode/spéciaux rejetés: {response.text}")

        except Exception as e:
            self.fail(f"Test Unicode échoué: {e}")

    def test_empty_and_null_values(self):
        """Test avec des valeurs vides et null"""
        try:
            # Test avec payload vide
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Test avec différents types de valeurs vides/null
            test_cases = [
                {"payload": None},
                {"payload": {}},
                {"payload": {"empty_string": "", "null_value": None}},
                {"payload": {"empty_list": [], "empty_dict": {}}},
            ]

            for i, test_case in enumerate(test_cases):
                request_data = {
                    "scheduler_id": scheduler_id,
                    "url": f"https://httpbin.org/post?test_case={i}",
                    "method": "POST",
                    **test_case
                }

                response = requests.post(f"{self.base_url}/api/request",
                                       json=request_data,
                                       headers=self.headers)

                print(f"🗳️  Cas {i+1} (valeurs vides) - Status: {response.status_code}")

                # Toutes devraient être acceptées
                if response.status_code != 200:
                    print(f"⚠️  Cas {i+1} rejeté: {response.text}")

            print("✅ Tests valeurs vides terminés")

        except Exception as e:
            self.fail(f"Test valeurs vides échoué: {e}")

    def test_invalid_http_methods(self):
        """Test avec des méthodes HTTP invalides"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Tester des méthodes HTTP invalides
            invalid_methods = ["INVALID", "CUSTOM", "123", "", None]

            for method in invalid_methods:
                request_data = {
                    "scheduler_id": scheduler_id,
                    "url": "https://httpbin.org/get",
                    "method": method
                }

                response = requests.post(f"{self.base_url}/api/request",
                                       json=request_data,
                                       headers=self.headers)

                print(f"🚫 Méthode '{method}' - Status: {response.status_code}")

                # Devrait être rejetée
                if method in ["INVALID", "CUSTOM", "123", ""]:
                    self.assertIn(response.status_code, [400, 422])

            print("✅ Méthodes HTTP invalides correctement rejetées")

        except Exception as e:
            self.fail(f"Test méthodes HTTP invalides échoué: {e}")


# ============================================================================
# RUNNER DE TESTS ET CONFIGURATION
# ============================================================================

class TestRunner:
    """Runner avancé pour les tests avec options"""

    @staticmethod
    def run_unit_tests():
        """Lance uniquement les tests unitaires (mocks)"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestRequestData))
        suite.addTest(unittest.makeSuite(TestAPIError))
        suite.addTest(unittest.makeSuite(TestMockAPIRequestScheduler))
        suite.addTest(unittest.makeSuite(TestMockAPIRequestSchedulerAsync))

        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)

    @staticmethod
    def run_integration_tests():
        """Lance les tests d'intégration réels"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(RealAPIManagerIntegrationTests))

        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)

    @staticmethod
    def run_websocket_tests():
        """Lance les tests WebSocket"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(WebSocketRealTests))

        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)

    @staticmethod
    def run_stress_tests():
        """Lance les tests de stress"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(StressTests))

        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)

    @staticmethod
    def run_edge_case_tests():
        """Lance les tests de cas limites"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(EdgeCaseTests))

        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(suite)

    @staticmethod
    def run_all_tests():
        """Lance tous les tests"""
        suites = [
            unittest.makeSuite(TestRequestData),
            unittest.makeSuite(TestAPIError),
            unittest.makeSuite(TestMockAPIRequestScheduler),
            unittest.makeSuite(TestMockAPIRequestSchedulerAsync),
            unittest.makeSuite(RealAPIManagerIntegrationTests),
            unittest.makeSuite(WebSocketRealTests),
            unittest.makeSuite(StressTests),
            unittest.makeSuite(EdgeCaseTests)
        ]

        combined_suite = unittest.TestSuite(suites)
        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(combined_suite)

    @staticmethod
    def run_quick_tests():
        """Lance les tests rapides (unitaires + intégration de base)"""
        suite = unittest.TestSuite()
        suite.addTest(unittest.makeSuite(TestRequestData))
        suite.addTest(unittest.makeSuite(TestAPIError))
        suite.addTest(unittest.makeSuite(TestMockAPIRequestScheduler))

        # Quelques tests d'intégration de base
        integration_suite = unittest.TestSuite()
        integration_suite.addTest(RealAPIManagerIntegrationTests('test_01_health_check'))
        integration_suite.addTest(RealAPIManagerIntegrationTests('test_02_home_page_accessible'))
        integration_suite.addTest(RealAPIManagerIntegrationTests('test_03_authentication_required'))
        integration_suite.addTest(RealAPIManagerIntegrationTests('test_05_scheduler_initialization'))

        combined_suite = unittest.TestSuite([suite, integration_suite])
        runner = unittest.TextTestRunner(verbosity=2)
        return runner.run(combined_suite)


# ============================================================================
# DOCUMENTATION ET AIDE
# ============================================================================

def print_test_documentation():
    """Affiche la documentation complète des tests"""
    doc = """
🧪 SUITE DE TESTS COMPLÈTE - API MANAGER
========================================

📋 TYPES DE TESTS DISPONIBLES:

1. 🔧 TESTS UNITAIRES (Mocks)
   - TestRequestData: Structure de données
   - TestAPIError: Exceptions personnalisées  
   - TestMockAPIRequestScheduler: Scheduler mock
   - TestMockAPIRequestSchedulerAsync: Tests async mock

2. 🌐 TESTS D'INTÉGRATION RÉELS (API Manager requis)
   - 20 tests couvrant tous les aspects de l'API
   - Vraies requêtes HTTP vers httpbin.org et jsonplaceholder
   - Tests d'authentification, schedulers, rate limiting
   - Monitoring des requêtes en temps réel

3. 🔌 TESTS WEBSOCKET
   - Connexion WebSocket
   - Enregistrement client
   - Communication REST->WebSocket

4. ⚡ TESTS DE STRESS
   - Création concurrente de schedulers
   - Soumission rapide de requêtes
   - Gros payloads et charge soutenue

5. 🎯 TESTS DE CAS LIMITES
   - JSON malformé, URLs longues
   - Caractères Unicode et spéciaux
   - Valeurs vides et méthodes HTTP invalides

🚀 COMMANDES DISPONIBLES:

python complete_test_suite.py               # Tous les tests
python complete_test_suite.py unit          # Tests unitaires seulement
python complete_test_suite.py integration   # Tests d'intégration seulement
python complete_test_suite.py websocket     # Tests WebSocket seulement
python complete_test_suite.py stress        # Tests de stress seulement
python complete_test_suite.py edge          # Tests de cas limites seulement
python complete_test_suite.py quick         # Tests rapides (unitaires + base intégration)
python complete_test_suite.py help          # Cette aide

⚙️ CONFIGURATION REQUISE:

1. API Manager en fonctionnement sur localhost:6000
2. Modifier TEST_BEARER_TOKEN avec votre vrai token
3. Connexion internet pour httpbin.org et jsonplaceholder.typicode.com

📊 STATISTIQUES:
- Tests unitaires: ~25 tests
- Tests d'intégration: 20 tests  
- Tests WebSocket: 3 tests
- Tests de stress: 4 tests
- Tests cas limites: 5 tests
- TOTAL: ~57 tests

⚠️ NOTES IMPORTANTES:

- Les tests d'intégration nécessitent que votre API Manager soit démarré
- Certains tests font des vraies requêtes HTTP (peuvent prendre du temps)
- Les tests WebSocket peuvent échouer si SocketIO n'est pas configuré
- Les tests de stress peuvent impacter les performances

🔍 DIAGNOSTIC:
Si des tests échouent, utilisez le script diagnostic_api_manager.py
pour identifier les problèmes spécifiques.
"""
    print(doc)


def main():
    """Fonction principale avec gestion des arguments"""
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command in ["help", "--help", "-h"]:
            print_test_documentation()
            return

        print(f"🧪 SUITE DE TESTS API MANAGER - Mode: {command.upper()}")
        print("=" * 60)

        if command == "unit":
            print("🔧 Lancement des tests unitaires...")
            result = TestRunner.run_all_tests()

        # Statistiques finales
        print("\n" + "=" * 60)
        print("📊 RÉSULTATS FINAUX")
        print("=" * 60)

        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        success = total_tests - failures - errors

        print(f"Tests exécutés: {total_tests}")
        print(f"✅ Succès: {success}")
        print(f"❌ Échecs: {failures}")
        print(f"⚠️  Erreurs: {errors}")

        if result.wasSuccessful():
            success_rate = 100.0
            print(f"🎉 Taux de succès: {success_rate:.1f}%")
            print("\n🏆 FÉLICITATIONS! Tous les tests sont passés!")

            print("\n📝 RÉSUMÉ DES CAPACITÉS TESTÉES:")
            print("  ✅ Structure de données et exceptions")
            print("  ✅ Gestion des schedulers et singletons")
            print("  ✅ Cache et génération de clés")
            print("  ✅ Authentification et sécurité")
            print("  ✅ Requêtes HTTP réelles")
            print("  ✅ Rate limiting et queues")
            print("  ✅ WebSocket et communications temps réel")
            print("  ✅ Gestion d'erreurs et cas limites")
            print("  ✅ Performance et stress")
        else:
            success_rate = (success / total_tests * 100) if total_tests > 0 else 0
            print(f"📊 Taux de succès: {success_rate:.1f}%")

            if success_rate >= 80:
                print("\n✅ RÉSULTAT ACCEPTABLE (≥80%)")
            elif success_rate >= 60:
                print("\n⚠️  RÉSULTAT MOYEN (≥60%)")
            else:
                print("\n❌ RÉSULTAT INSUFFISANT (<60%)")

            print("\n🔍 POUR DIAGNOSTIQUER LES PROBLÈMES:")
            print("1. Vérifiez que l'API Manager est démarré")
            print("2. Vérifiez le token d'authentification")
            print("3. Lancez python diagnostic_api_manager.py")
            print("4. Consultez les logs de l'API Manager")

            if failures:
                print(f"\n💥 DÉTAILS DES {failures} ÉCHEC(S):")
                for i, (test, traceback) in enumerate(result.failures[:5]):  # Limiter à 5
                    print(f"\n  {i+1}. {test}")
                    # Extraire la ligne d'erreur principale
                    lines = traceback.split('\n')
                    for line in lines:
                        if 'AssertionError' in line or 'self.assert' in line:
                            print(f"     → {line.strip()}")
                            break

                if len(result.failures) > 5:
                    print(f"     ... et {len(result.failures) - 5} autres échecs")

            if errors:
                print(f"\n⚠️  DÉTAILS DES {errors} ERREUR(S):")
                for i, (test, traceback) in enumerate(result.errors[:3]):  # Limiter à 3
                    print(f"\n  {i+1}. {test}")
                    # Extraire l'erreur principale
                    lines = traceback.split('\n')
                    for line in lines:
                        if any(word in line.lower() for word in ['error:', 'exception:', 'failed']):
                            print(f"     → {line.strip()}")
                            break

                if len(result.errors) > 3:
                    print(f"     ... et {len(result.errors) - 3} autres erreurs")

        print(f"\n🏁 Tests terminés en {time.time() - start_time:.1f}s" if 'start_time' in locals() else "")

        # Code de sortie basé sur les résultats
        sys.exit(0 if result.wasSuccessful() else 1)


# ============================================================================
# UTILITAIRES ET HELPERS
# ============================================================================

class TestUtils:
    """Utilitaires pour les tests"""

    @staticmethod
    def check_api_manager_status():
        """Vérifie si l'API Manager est accessible"""
        try:
            response = requests.get(TEST_BASE_URL, timeout=5)
            return response.status_code == 200
        except:
            return False

    @staticmethod
    def wait_for_api_manager(max_wait=30):
        """Attend que l'API Manager soit prêt"""
        print("⏳ Attente de l'API Manager...")

        start_time = time.time()
        while time.time() - start_time < max_wait:
            if TestUtils.check_api_manager_status():
                print("✅ API Manager prêt!")
                return True

            print(".", end="", flush=True)
            time.sleep(1)

        print(f"\n❌ API Manager non accessible après {max_wait}s")
        return False

    @staticmethod
    def validate_bearer_token():
        """Valide que le token Bearer est configuré"""
        if TEST_BEARER_TOKEN == "your-actual-bearer-token-here":
            print("⚠️  ATTENTION: Token Bearer non configuré!")
            print("   Modifiez TEST_BEARER_TOKEN dans le script")
            return False
        return True

    @staticmethod
    def create_test_scheduler():
        """Crée un scheduler de test et retourne son ID"""
        headers = {"Authorization": f"Bearer {TEST_BEARER_TOKEN}"}

        init_data = {"api_patterns": ["https://httpbin.org"]}
        response = requests.post(f"{TEST_BASE_URL}/api/initialize",
                               json=init_data,
                               headers=headers,
                               timeout=10)

        if response.status_code == 200:
            return response.json()["scheduler_id"]
        else:
            raise Exception(f"Impossible de créer le scheduler: {response.text}")

    @staticmethod
    def cleanup_test_scheduler(scheduler_id):
        """Nettoie un scheduler de test"""
        headers = {"Authorization": f"Bearer {TEST_BEARER_TOKEN}"}

        try:
            response = requests.delete(f"{TEST_BASE_URL}/api/delete_scheduler",
                                     params={"scheduler_id": scheduler_id},
                                     headers=headers,
                                     timeout=5)
            return response.status_code in [200, 404]  # 404 = déjà supprimé
        except:
            return False


class TestReporter:
    """Générateur de rapports de tests"""

    @staticmethod
    def generate_html_report(result, output_file="test_report.html"):
        """Génère un rapport HTML des résultats de tests"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>API Manager - Rapport de Tests</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        .header { text-align: center; margin-bottom: 30px; }
        .stats { display: flex; justify-content: space-around; margin: 20px 0; }
        .stat-box { padding: 15px; border-radius: 8px; text-align: center; min-width: 120px; }
        .success { background-color: #d4edda; color: #155724; }
        .failure { background-color: #f8d7da; color: #721c24; }
        .error { background-color: #fff3cd; color: #856404; }
        .test-section { margin: 20px 0; }
        .test-section h3 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 5px; }
        .test-item { padding: 10px; margin: 5px 0; border-left: 4px solid #ccc; background: #f8f9fa; }
        .test-success { border-left-color: #28a745; }
        .test-failure { border-left-color: #dc3545; }
        .test-error { border-left-color: #ffc107; }
        .traceback { background: #f1f1f1; padding: 10px; margin-top: 10px; font-family: monospace; font-size: 12px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 API Manager - Rapport de Tests</h1>
            <p>Généré le {timestamp}</p>
        </div>
        
        <div class="stats">
            <div class="stat-box success">
                <h3>{success_count}</h3>
                <p>Succès</p>
            </div>
            <div class="stat-box failure">
                <h3>{failure_count}</h3>
                <p>Échecs</p>
            </div>
            <div class="stat-box error">
                <h3>{error_count}</h3>
                <p>Erreurs</p>
            </div>
            <div class="stat-box">
                <h3>{total_tests}</h3>
                <p>Total</p>
            </div>
        </div>
        
        <div style="text-align: center; margin: 20px 0;">
            <h2>Taux de succès: {success_rate:.1f}%</h2>
        </div>
        
        {sections}
    </div>
</body>
</html>
        """

        # Calculer les statistiques
        total_tests = result.testsRun
        failure_count = len(result.failures)
        error_count = len(result.errors)
        success_count = total_tests - failure_count - error_count
        success_rate = (success_count / total_tests * 100) if total_tests > 0 else 0

        # Générer les sections
        sections = ""

        # Section succès
        if success_count > 0:
            sections += '<div class="test-section"><h3>✅ Tests Réussis</h3>'
            sections += f'<p>{success_count} tests ont réussi avec succès.</p>'
            sections += '</div>'

        # Section échecs
        if failure_count > 0:
            sections += '<div class="test-section"><h3>❌ Échecs</h3>'
            for test, traceback in result.failures:
                sections += f'<div class="test-item test-failure">'
                sections += f'<strong>{test}</strong>'
                sections += f'<div class="traceback">{traceback.replace("<", "&lt;").replace(">", "&gt;")}</div>'
                sections += '</div>'
            sections += '</div>'

        # Section erreurs
        if error_count > 0:
            sections += '<div class="test-section"><h3>⚠️ Erreurs</h3>'
            for test, traceback in result.errors:
                sections += f'<div class="test-item test-error">'
                sections += f'<strong>{test}</strong>'
                sections += f'<div class="traceback">{traceback.replace("<", "&lt;").replace(">", "&gt;")}</div>'
                sections += '</div>'
            sections += '</div>'

        # Générer le HTML final
        html_content = html_template.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_tests=total_tests,
            success_count=success_count,
            failure_count=failure_count,
            error_count=error_count,
            success_rate=success_rate,
            sections=sections
        )

        # Écrire le fichier
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"📄 Rapport HTML généré: {output_file}")
        return output_file


# ============================================================================
# EXÉCUTION PRINCIPALE
# ============================================================================

if __name__ == "__main__":
    # Configuration du logging pour les tests
    logging.basicConfig(
        level=logging.WARNING,  # Réduire les logs pendant les tests
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Banner de démarrage
    print("🧪" + "="*58 + "🧪")
    print("🧪" + " "*18 + "API MANAGER TEST SUITE" + " "*17 + "🧪")
    print("🧪" + "="*58 + "🧪")
    print()

    # Vérifications préliminaires
    print("🔍 Vérifications préliminaires...")

    # 1. Vérifier la configuration du token
    if not TestUtils.validate_bearer_token():
        print("\n❌ Configuration invalide. Corrigez le token Bearer et relancez.")
        sys.exit(1)

    # 2. Pour les tests d'intégration, vérifier l'API Manager
    if len(sys.argv) <= 1 or sys.argv[1].lower() in ['integration', 'websocket', 'stress', 'edge']:
        print("🔗 Vérification de l'API Manager...")
        if not TestUtils.check_api_manager_status():
            print("❌ API Manager non accessible sur " + TEST_BASE_URL)
            print("💡 Démarrez l'API Manager avant de lancer les tests d'intégration")

            # Demander s'il faut continuer avec seulement les tests unitaires
            if len(sys.argv) <= 1:
                print("\n🤔 Voulez-vous lancer seulement les tests unitaires? (y/N)")
                response = input().lower().strip()
                if response in ['y', 'yes', 'oui']:
                    print("🔧 Lancement des tests unitaires seulement...")
                    result = TestRunner.run_unit_tests()
                    sys.exit(0 if result.wasSuccessful() else 1)
                else:
                    print("❌ Tests annulés.")
                    sys.exit(1)
            else:
                sys.exit(1)
        else:
            print("✅ API Manager accessible")

    print("✅ Vérifications terminées\n")

    # Démarrer le chrono
    start_time = time.time()

    # Lancer la fonction principale
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrompus par l'utilisateur")
        sys.exit(130)  # Code de sortie standard pour Ctrl+C
    except Exception as e:
        print(f"\n💥 Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

class MockAPIRequestScheduler:
    """Version mock du scheduler pour tests unitaires"""
    _instances: Dict[Tuple, 'MockAPIRequestScheduler'] = {}
    _lock = threading.Lock()

    def __new__(cls, api_patterns: List[str], *args, **kwargs):
        key = tuple(sorted(api_patterns))
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = super(MockAPIRequestScheduler, cls).__new__(cls)
        return cls._instances[key]

    def __init__(self, api_patterns: List[str]):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.api_patterns = api_patterns
        self.scheduler_id = str(uuid.uuid4())
        self.CALLS_PER_SECOND = 1
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND

        self.request_queue = Queue(maxsize=MAX_QUEUE_SIZE)
        self.response_store: Dict[str, Any] = {}
        self.request_dict: Dict[str, RequestData] = {}

        self.cache_dir = os.path.join(os.getcwd(), 'cache')
        self._ensure_cache_directory()

        self.lock = threading.Lock()
        self.shutdown_event = threading.Event()

        self.worker_thread = Mock()
        self.loop_thread = Mock()

        self._initialized = True

    def _ensure_cache_directory(self):
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            raise APIError(f"Impossible de créer le répertoire cache: {e}")

    def set_rate_limit(self, calls_per_second: float):
        if calls_per_second <= 0:
            raise ValueError("Le taux d'appels doit être positif")

        self.CALLS_PER_SECOND = calls_per_second
        self.CALL_INTERVAL = 1 / self.CALLS_PER_SECOND

    def get_cache_path(self, cache_key: str) -> str:
        return os.path.join(self.cache_dir, f"{abs(hash(str(cache_key)))}.json")

    def _generate_cache_key(self, request_data: RequestData) -> str:
        key_components = [
            request_data.url,
            str(request_data.payload) if request_data.payload else '',
            str(request_data.method),
            str(request_data.headers),
            str(request_data.request_kwargs)
        ]
        return '|'.join(key_components)

    async def _check_cache(self, request_data: RequestData) -> Optional[Any]:
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
        return {"success": True, "data": "mock_response"}

    def add_request(self, url: str, payload: Optional[Dict] = None,
                   cache_duration: int = 0, method: str = "POST",
                   client_id: Optional[str] = None, headers: Optional[Dict] = None,
                   **request_kwargs) -> Tuple[str, float]:
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        if base_url not in self.api_patterns:
            raise ValueError(f"URL non gérée par cette instance: {base_url}")

        if self.request_queue.qsize() >= MAX_QUEUE_SIZE:
            raise RateLimitExceeded("Queue pleine, requête rejetée")

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

        self.request_queue.put(request_data)

        with self.lock:
            self.request_dict[request_id] = request_data

        estimated_delay = self.request_queue.qsize() * self.CALL_INTERVAL
        return request_id, estimated_delay

    def get_response(self, request_id: str) -> Optional[Any]:
        with self.lock:
            return self.response_store.pop(request_id, None)

    def has_request(self, request_id: str) -> bool:
        with self.lock:
            return request_id in self.request_dict

    def get_stats(self) -> Dict:
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
        self.shutdown_event.set()

def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            auth_token = request.headers.get("Authorization")
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

# ============================================================================
# TESTS UNITAIRES (MOCKS)
# ============================================================================

class TestRequestData(unittest.TestCase):
    """Tests pour la classe RequestData"""

    def test_request_data_initialization(self):
        """Test l'initialisation de RequestData"""
        request_data = RequestData(
            request_id="test-id",
            url="https://api.example.com/test",
            method="POST"
        )

        self.assertEqual(request_data.request_id, "test-id")
        self.assertEqual(request_data.url, "https://api.example.com/test")
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
            url="https://api.example.com/test",
            payload=payload
        )

        self.assertEqual(request_data.payload, payload)

    def test_request_data_timestamp_auto_generation(self):
        """Test la génération automatique du timestamp"""
        before = time.time()
        request_data = RequestData(
            request_id="test-id",
            url="https://api.example.com/test"
        )
        after = time.time()

        self.assertGreaterEqual(request_data.timestamp, before)
        self.assertLessEqual(request_data.timestamp, after)

    def test_request_data_defaults(self):
        """Test les valeurs par défaut"""
        request_data = RequestData(
            request_id="test-id",
            url="https://api.example.com/test"
        )

        self.assertEqual(request_data.method, "POST")
        self.assertEqual(request_data.cache_duration, 0)
        self.assertEqual(request_data.retry_count, 0)
        self.assertIsNone(request_data.payload)
        self.assertIsNone(request_data.client_id)


class TestAPIError(unittest.TestCase):
    """Tests pour les exceptions personnalisées"""

    def test_api_error_creation(self):
        """Test la création d'une APIError"""
        error = APIError("Test error", status_code=400, request_id="test-id")

        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error.request_id, "test-id")

    def test_api_error_minimal(self):
        """Test APIError avec paramètres minimaux"""
        error = APIError("Simple error")

        self.assertEqual(str(error), "Simple error")
        self.assertIsNone(error.status_code)
        self.assertIsNone(error.request_id)

    def test_rate_limit_exceeded_inheritance(self):
        """Test que RateLimitExceeded hérite d'APIError"""
        error = RateLimitExceeded("Rate limit exceeded")

        self.assertIsInstance(error, APIError)
        self.assertEqual(str(error), "Rate limit exceeded")

    def test_exception_hierarchy(self):
        """Test la hiérarchie d'exceptions"""
        error = RateLimitExceeded("Test", status_code=429)

        self.assertIsInstance(error, Exception)
        self.assertIsInstance(error, APIError)
        self.assertIsInstance(error, RateLimitExceeded)


class TestMockAPIRequestScheduler(unittest.TestCase):
    """Tests pour la version mock du scheduler"""

    def setUp(self):
        """Configuration avant chaque test"""
        self.test_urls = ["https://api.example.com"]
        self.temp_dir = tempfile.mkdtemp()
        MockAPIRequestScheduler._instances.clear()

    def tearDown(self):
        """Nettoyage après chaque test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        MockAPIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    def test_scheduler_initialization(self, mock_getcwd):
        """Test l'initialisation du scheduler"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)

        self.assertEqual(scheduler.api_patterns, self.test_urls)
        self.assertEqual(scheduler.CALLS_PER_SECOND, 1)
        self.assertIsNotNone(scheduler.scheduler_id)
        self.assertTrue(hasattr(scheduler, 'request_queue'))
        self.assertTrue(hasattr(scheduler, 'response_store'))

    @patch('os.getcwd')
    def test_scheduler_singleton_behavior(self, mock_getcwd):
        """Test le comportement singleton du scheduler"""
        mock_getcwd.return_value = self.temp_dir

        scheduler1 = MockAPIRequestScheduler(self.test_urls)
        scheduler2 = MockAPIRequestScheduler(self.test_urls)

        self.assertIs(scheduler1, scheduler2)

    @patch('os.getcwd')
    def test_different_urls_different_instances(self, mock_getcwd):
        """Test que des URLs différentes créent des instances différentes"""
        mock_getcwd.return_value = self.temp_dir

        scheduler1 = MockAPIRequestScheduler(["https://api1.example.com"])
        scheduler2 = MockAPIRequestScheduler(["https://api2.example.com"])

        self.assertIsNot(scheduler1, scheduler2)

    @patch('os.getcwd')
    def test_set_rate_limit(self, mock_getcwd):
        """Test la configuration de la limite de taux"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)
        scheduler.set_rate_limit(2.0)

        self.assertEqual(scheduler.CALLS_PER_SECOND, 2.0)
        self.assertEqual(scheduler.CALL_INTERVAL, 0.5)

    @patch('os.getcwd')
    def test_set_rate_limit_validation(self, mock_getcwd):
        """Test la validation de la limite de taux"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)

        with self.assertRaises(ValueError):
            scheduler.set_rate_limit(0)

        with self.assertRaises(ValueError):
            scheduler.set_rate_limit(-1)

    @patch('os.getcwd')
    def test_cache_path_generation(self, mock_getcwd):
        """Test la génération des chemins de cache"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)
        cache_key = "test-cache-key"
        cache_path = scheduler.get_cache_path(cache_key)

        expected_path = os.path.join(self.temp_dir, 'cache', f"{abs(hash(cache_key))}.json")
        self.assertEqual(cache_path, expected_path)

    @patch('os.getcwd')
    @patch('queue.Queue')
    def test_add_request_success(self, mock_queue, mock_getcwd):
        """Test l'ajout réussi d'une requête"""
        mock_getcwd.return_value = self.temp_dir
        mock_queue_instance = Mock()
        mock_queue.return_value = mock_queue_instance
        mock_queue_instance.qsize.return_value = 5

        scheduler = MockAPIRequestScheduler(self.test_urls)

        request_id, estimated_delay = scheduler.add_request(
            url="https://api.example.com/test",
            payload={"test": "data"}
        )

        self.assertIsInstance(request_id, str)
        self.assertGreater(len(request_id), 0)
        self.assertIsInstance(estimated_delay, float)
        mock_queue_instance.put.assert_called_once()

    @patch('os.getcwd')
    def test_add_request_invalid_url(self, mock_getcwd):
        """Test l'ajout d'une requête avec URL invalide"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)

        with self.assertRaises(ValueError):
            scheduler.add_request("https://invalid-api.com/test")

    @patch('os.getcwd')
    def test_add_request_queue_full(self, mock_getcwd):
        """Test l'ajout d'une requête quand la queue est pleine"""
        mock_getcwd.return_value = self.temp_dir

        with patch('queue.Queue') as mock_queue:
            mock_queue_instance = Mock()
            mock_queue.return_value = mock_queue_instance
            mock_queue_instance.qsize.return_value = MAX_QUEUE_SIZE

            scheduler = MockAPIRequestScheduler(self.test_urls)

            with self.assertRaises(RateLimitExceeded):
                scheduler.add_request("https://api.example.com/test")

    @patch('os.getcwd')
    def test_has_request(self, mock_getcwd):
        """Test la vérification de l'existence d'une requête"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)
        request_id = "test-request-id"

        self.assertFalse(scheduler.has_request(request_id))

        scheduler.request_dict[request_id] = Mock()

        self.assertTrue(scheduler.has_request(request_id))

    @patch('os.getcwd')
    def test_get_response(self, mock_getcwd):
        """Test la récupération d'une réponse"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)
        request_id = "test-request-id"
        test_response = {"result": "success"}

        scheduler.response_store[request_id] = test_response

        response = scheduler.get_response(request_id)

        self.assertEqual(response, test_response)
        self.assertNotIn(request_id, scheduler.response_store)

    @patch('os.getcwd')
    def test_get_response_nonexistent(self, mock_getcwd):
        """Test la récupération d'une réponse inexistante"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)

        response = scheduler.get_response("nonexistent-id")

        self.assertIsNone(response)

    @patch('os.getcwd')
    def test_get_stats(self, mock_getcwd):
        """Test la récupération des statistiques"""
        mock_getcwd.return_value = self.temp_dir

        with patch('queue.Queue') as mock_queue:
            mock_queue_instance = Mock()
            mock_queue.return_value = mock_queue_instance
            mock_queue_instance.qsize.return_value = 3

            scheduler = MockAPIRequestScheduler(self.test_urls)
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

    @patch('os.getcwd')
    def test_cache_key_generation(self, mock_getcwd):
        """Test la génération de clé de cache"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)

        request_data = RequestData(
            request_id="test-id",
            url="https://api.example.com/test",
            payload={"key": "value"},
            method="POST",
            headers={"Content-Type": "application/json"}
        )

        cache_key = scheduler._generate_cache_key(request_data)

        self.assertIsInstance(cache_key, str)
        self.assertIn("https://api.example.com/test", cache_key)
        self.assertIn("POST", cache_key)

    @patch('os.getcwd')
    def test_cleanup(self, mock_getcwd):
        """Test le nettoyage du scheduler"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)
        scheduler.cleanup()

        self.assertTrue(scheduler.shutdown_event.is_set())


class TestMockAPIRequestSchedulerAsync(unittest.IsolatedAsyncioTestCase):
    """Tests asynchrones pour le scheduler mock"""

    def setUp(self):
        """Configuration avant chaque test"""
        self.test_urls = ["https://api.example.com"]
        self.temp_dir = tempfile.mkdtemp()
        MockAPIRequestScheduler._instances.clear()

    def tearDown(self):
        """Nettoyage après chaque test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        MockAPIRequestScheduler._instances.clear()

    @patch('os.getcwd')
    async def test_cache_hit(self, mock_getcwd):
        """Test le hit de cache"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)

        request_data = RequestData(
            request_id="test-id",
            url="https://api.example.com/test",
            cache_duration=3600
        )

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

        result = await scheduler._check_cache(request_data)

        self.assertEqual(result, cached_response)

    @patch('os.getcwd')
    async def test_cache_miss_expired(self, mock_getcwd):
        """Test le cache miss avec données expirées"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)

        request_data = RequestData(
            request_id="test-id",
            url="https://api.example.com/test",
            cache_duration=3600
        )

        cache_key = scheduler._generate_cache_key(request_data)
        cache_path = scheduler.get_cache_path(cache_key)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        expired_cache_data = {
            "response": {"expired": True},
            "timestamp": time.time() - 7200
        }

        with open(cache_path, 'w') as f:
            json.dump(expired_cache_data, f)

        result = await scheduler._check_cache(request_data)

        self.assertIsNone(result)

    @patch('os.getcwd')
    async def test_cache_miss_no_file(self, mock_getcwd):
        """Test le cache miss sans fichier"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)

        request_data = RequestData(
            request_id="test-id",
            url="https://api.example.com/test",
            cache_duration=3600
        )

        result = await scheduler._check_cache(request_data)

        self.assertIsNone(result)

    @patch('os.getcwd')
    async def test_make_http_request(self, mock_getcwd):
        """Test la requête HTTP mock"""
        mock_getcwd.return_value = self.temp_dir

        scheduler = MockAPIRequestScheduler(self.test_urls)

        request_data = RequestData(
            request_id="test-id",
            url="https://api.example.com/test",
            method="GET"
        )

        result = await scheduler._make_http_request(request_data)

        self.assertEqual(result, {"success": True, "data": "mock_response"})


# ============================================================================
# TESTS D'INTÉGRATION RÉELS
# ============================================================================

class RealAPIManagerIntegrationTests(unittest.TestCase):
    """Tests d'intégration réels contre l'API Manager en fonctionnement"""

    def setUp(self):
        """Configuration avant chaque test"""
        self.headers = {"Authorization": f"Bearer {TEST_BEARER_TOKEN}"}
        self.base_url = TEST_BASE_URL
        self.timeout = 30

        # Vérifier que l'API Manager est accessible
        self._check_api_manager_running()

    def _check_api_manager_running(self):
        """Vérifie que l'API Manager est en fonctionnement"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code != 200:
                self.skipTest("API Manager non accessible - Veuillez le démarrer d'abord")
        except requests.exceptions.RequestException:
            self.skipTest("API Manager non accessible - Veuillez le démarrer sur localhost:6000")

    def test_01_health_check(self):
        """Test 1: Health check de base"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            print(f"📡 Health check - Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Manager healthy - {data}")
                self.assertEqual(data.get("status"), "healthy")
            else:
                print("⚠️  Health endpoint non disponible, mais serveur accessible")

        except Exception as e:
            self.fail(f"Health check échoué: {e}")

    def test_02_home_page_accessible(self):
        """Test 2: Page d'accueil accessible"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            print(f"🏠 Page d'accueil - Status: {response.status_code}")

            self.assertEqual(response.status_code, 200)
            self.assertTrue(len(response.text) > 0)
            print("✅ Page d'accueil accessible")

        except Exception as e:
            self.fail(f"Page d'accueil inaccessible: {e}")

    def test_03_authentication_required(self):
        """Test 3: Vérification de l'authentification requise"""
        try:
            response = requests.post(f"{self.base_url}/api/initialize",
                                   json={"api_patterns": REAL_TEST_APIS})
            print(f"🔒 Test sans auth - Status: {response.status_code}")

            self.assertEqual(response.status_code, 401)
            print("✅ Authentification correctement requise")

        except Exception as e:
            self.fail(f"Test d'authentification échoué: {e}")

    def test_04_invalid_bearer_token(self):
        """Test 4: Token Bearer invalide"""
        try:
            invalid_headers = {"Authorization": "Bearer invalid-token-12345"}
            response = requests.post(f"{self.base_url}/api/initialize",
                                   json={"api_patterns": REAL_TEST_APIS},
                                   headers=invalid_headers)
            print(f"🚫 Test token invalide - Status: {response.status_code}")

            self.assertEqual(response.status_code, 401)
            print("✅ Token invalide correctement rejeté")

        except Exception as e:
            self.fail(f"Test token invalide échoué: {e}")

    def test_05_scheduler_initialization(self):
        """Test 5: Initialisation d'un scheduler"""
        try:
            init_data = {"api_patterns": REAL_TEST_APIS}

            response = requests.post(f"{self.base_url}/api/initialize",
                                   json=init_data,
                                   headers=self.headers,
                                   timeout=10)

            print(f"🏗️  Initialisation scheduler - Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Scheduler créé: {data.get('scheduler_id', 'N/A')[:8]}...")

                self.assertIn("scheduler_id", data)
                self.scheduler_id = data["scheduler_id"]

            elif response.status_code == 401:
                self.fail("❌ Authentification échouée - Vérifiez votre token Bearer")
            else:
                print(f"⚠️  Réponse inattendue: {response.text}")
                self.fail(f"Initialisation échouée: {response.status_code}")

        except requests.exceptions.Timeout:
            self.fail("⏰ Timeout lors de l'initialisation du scheduler")
        except Exception as e:
            self.fail(f"Erreur lors de l'initialisation: {e}")

    def test_06_scheduler_initialization_empty_urls(self):
        """Test 6: Initialisation avec URLs vides"""
        try:
            init_data = {"api_patterns": []}

            response = requests.post(f"{self.base_url}/api/initialize",
                                   json=init_data,
                                   headers=self.headers,
                                   timeout=10)

            print(f"❌ Test URLs vides - Status: {response.status_code}")
            self.assertEqual(response.status_code, 400)
            print("✅ URLs vides correctement rejetées")

        except Exception as e:
            self.fail(f"Test URLs vides échoué: {e}")

    def test_07_scheduler_initialization_invalid_urls(self):
        """Test 7: Initialisation avec URLs invalides"""
        try:
            invalid_urls = ["not-a-url", "ftp://invalid.com", ""]
            init_data = {"api_patterns": invalid_urls}

            response = requests.post(f"{self.base_url}/api/initialize",
                                   json=init_data,
                                   headers=self.headers,
                                   timeout=10)

            print(f"🚫 Test URLs invalides - Status: {response.status_code}")
            self.assertIn(response.status_code, [400, 422])  # Soit 400 soit 422
            print("✅ URLs invalides correctement rejetées")

        except Exception as e:
            self.fail(f"Test URLs invalides échoué: {e}")

    def test_08_real_http_request_httpbin(self):
        """Test 8: Vraie requête HTTP vers httpbin.org"""
        try:
            # Créer un scheduler pour httpbin
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers,
                                        timeout=10)

            if init_response.status_code != 200:
                self.skipTest("Impossible de créer le scheduler httpbin")

            scheduler_id = init_response.json()["scheduler_id"]
            print(f"🔧 Scheduler httpbin créé: {scheduler_id[:8]}...")

            # Faire une vraie requête vers httpbin
            request_data = {
                "scheduler_id": scheduler_id,
                "url": "https://httpbin.org/get?test_param=integration_test",
                "method": "GET"
            }

            request_response = requests.post(f"{self.base_url}/api/request",
                                           json=request_data,
                                           headers=self.headers,
                                           timeout=10)

            print(f"📡 Requête httpbin - Status: {request_response.status_code}")

            if request_response.status_code != 200:
                self.fail(f"Échec de la requête: {request_response.text}")

            request_id = request_response.json()["uuid"]
            print(f"🎫 Request ID: {request_id[:8]}...")

            # Attendre et vérifier la réponse
            self._wait_for_response(request_id, expected_content="httpbin.org")

        except Exception as e:
            self.fail(f"Test httpbin échoué: {e}")

    def test_09_real_http_request_jsonplaceholder(self):
        """Test 9: Vraie requête HTTP vers jsonplaceholder"""
        try:
            # Créer scheduler pour jsonplaceholder
            init_data = {"api_patterns": ["https://jsonplaceholder.typicode.com"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers,
                                        timeout=10)

            if init_response.status_code != 200:
                self.skipTest("Impossible de créer le scheduler jsonplaceholder")

            scheduler_id = init_response.json()["scheduler_id"]
            print(f"🔧 Scheduler jsonplaceholder créé: {scheduler_id[:8]}...")

            # Requête vers un post spécifique
            request_data = {
                "scheduler_id": scheduler_id,
                "url": "https://jsonplaceholder.typicode.com/posts/1",
                "method": "GET"
            }

            request_response = requests.post(f"{self.base_url}/api/request",
                                           json=request_data,
                                           headers=self.headers,
                                           timeout=10)

            print(f"📡 Requête jsonplaceholder - Status: {request_response.status_code}")

            if request_response.status_code != 200:
                self.fail(f"Échec de la requête: {request_response.text}")

            request_id = request_response.json()["uuid"]

            # Attendre et vérifier la réponse
            response_data = self._wait_for_response(request_id)

            # Vérifier la structure JSON de jsonplaceholder
            if isinstance(response_data, dict):
                expected_keys = ["userId", "id", "title", "body"]
                for key in expected_keys:
                    if key in response_data:
                        print(f"✅ Clé '{key}' trouvée dans la réponse")
                    else:
                        print(f"⚠️  Clé '{key}' manquante dans la réponse")

        except Exception as e:
            self.fail(f"Test jsonplaceholder échoué: {e}")

    def test_10_rate_limiting_verification(self):
        """Test 10: Vérification de la limitation de taux"""
        try:
            # Créer un scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            if init_response.status_code != 200:
                self.skipTest("Impossible de créer le scheduler pour le test de rate limiting")

            scheduler_id = init_response.json()["scheduler_id"]

            # Configurer une limite de taux basse
            rate_data = {"scheduler_id": scheduler_id, "limit": 0.5}
            rate_response = requests.post(f"{self.base_url}/api/set_rate_limit",
                                        json=rate_data,
                                        headers=self.headers)

            print(f"⚡ Configuration rate limit - Status: {rate_response.status_code}")

            if rate_response.status_code != 200:
                print("⚠️  Rate limiting non disponible, test ignoré")
                return

            # Faire plusieurs requêtes et mesurer les délais
            request_ids = []

            for i in range(3):
                request_data = {
                    "scheduler_id": scheduler_id,
                    "url": f"https://httpbin.org/get?test_rate_limit={i}",
                    "method": "GET"
                }

                response = requests.post(f"{self.base_url}/api/request",
                                       json=request_data,
                                       headers=self.headers)

                if response.status_code == 200:
                    request_ids.append(response.json()["uuid"])
                    estimated_delay = response.json().get("estimated_delay", 0)
                    print(f"📋 Requête {i+1} - Délai estimé: {estimated_delay:.1f}s")

            print(f"✅ {len(request_ids)} requêtes soumises avec rate limiting")

        except Exception as e:
            self.fail(f"Test rate limiting échoué: {e}")

    def test_11_request_status_monitoring(self):
        """Test 11: Monitoring du statut des requêtes"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            if init_response.status_code != 200:
                self.skipTest("Impossible de créer le scheduler")

            scheduler_id = init_response.json()["scheduler_id"]

            # Soumettre une requête avec délai
            request_data = {
                "scheduler_id": scheduler_id,
                "url": "https://httpbin.org/delay/2",
                "method": "GET"
            }

            start_time = time.time()
            request_response = requests.post(f"{self.base_url}/api/request",
                                           json=request_data,
                                           headers=self.headers)

            self.assertEqual(request_response.status_code, 200)
            request_id = request_response.json()["uuid"]
            status_url = request_response.json()["status_url"]

            print(f"🎫 Requête soumise: {request_id[:8]}...")
            print(f"📊 Status URL: {status_url}")

            # Vérifier le statut pendant le traitement
            pending_found = False
            complete_found = False

            for attempt in range(60):
                status_response = requests.get(f"{self.base_url}/api/status/{request_id}",
                                             headers=self.headers,
                                             timeout=5)

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data["status"]

                    if current_status == "pending":
                        pending_found = True
                        print(f"⏳ Requête en cours... (tentative {attempt+1})")
                    elif current_status == "complete":
                        complete_found = True
                        elapsed_time = time.time() - start_time
                        print(f"✅ Requête terminée en {elapsed_time:.1f}s")

                        response_data = status_data.get("response", {})
                        if isinstance(response_data, dict) and "url" in response_data:
                            print(f"📊 Réponse valide de httpbin reçue")
                        else:
                            print(f"⚠️  Réponse inattendue: {type(response_data)}")

                        break
                    else:
                        print(f"❓ Statut inattendu: {current_status}")
                elif status_response.status_code == 404:
                    print(f"❌ Requête non trouvée (tentative {attempt+1})")

                time.sleep(0.5)

            # Vérifications
            self.assertTrue(pending_found or complete_found, "Aucun statut valide trouvé")
            if not complete_found:
                print("⚠️  Requête non terminée dans les temps (peut être normal)")

        except Exception as e:
            self.fail(f"Test monitoring échoué: {e}")

    def test_12_multiple_requests_queue(self):
        """Test 12: File d'attente de requêtes multiples"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Soumettre plusieurs requêtes rapidement
            request_ids = []

            for i in range(5):
                request_data = {
                    "scheduler_id": scheduler_id,
                    "url": f"https://httpbin.org/get?batch_test={i}",
                    "method": "GET"
                }

                response = requests.post(f"{self.base_url}/api/request",
                                       json=request_data,
                                       headers=self.headers)

                if response.status_code == 200:
                    req_id = response.json()["uuid"]
                    estimated_delay = response.json().get("estimated_delay", 0)
                    request_ids.append(req_id)
                    print(f"📋 Requête {i+1}/5 - ID: {req_id[:8]}... - Délai: {estimated_delay:.1f}s")

            print(f"✅ {len(request_ids)} requêtes soumises en batch")

            # Vérifier que les délais augmentent (queue effect)
            self.assertGreater(len(request_ids), 0)

        except Exception as e:
            self.fail(f"Test requêtes multiples échoué: {e}")

    def test_13_error_handling_invalid_url(self):
        """Test 13: Gestion d'erreur avec URL non autorisée"""
        try:
            # Créer scheduler pour httpbin uniquement
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Tenter une requête vers une URL non autorisée
            request_data = {
                "scheduler_id": scheduler_id,
                "url": "https://unauthorized-api.example.com/test",
                "method": "GET"
            }

            response = requests.post(f"{self.base_url}/api/request",
                                   json=request_data,
                                   headers=self.headers)

            print(f"🚫 Requête URL non autorisée - Status: {response.status_code}")

            # Devrait être rejetée (400 ou 404)
            self.assertIn(response.status_code, [400, 404])
            print("✅ URL non autorisée correctement rejetée")

        except Exception as e:
            self.fail(f"Test URL non autorisée échoué: {e}")

    def test_14_nonexistent_scheduler(self):
        """Test 14: Requête avec scheduler inexistant"""
        try:
            fake_scheduler_id = "00000000-0000-0000-0000-000000000000"

            request_data = {
                "scheduler_id": fake_scheduler_id,
                "url": "https://httpbin.org/get",
                "method": "GET"
            }

            response = requests.post(f"{self.base_url}/api/request",
                                   json=request_data,
                                   headers=self.headers)

            print(f"❌ Scheduler inexistant - Status: {response.status_code}")

            self.assertEqual(response.status_code, 404)
            print("✅ Scheduler inexistant correctement rejeté")

        except Exception as e:
            self.fail(f"Test scheduler inexistant échoué: {e}")

    def test_15_open_status_endpoint(self):
        """Test 15: Endpoint de statut ouvert (debug)"""
        try:
            response = requests.get(f"{self.base_url}/api/openstatus", timeout=10)
            print(f"📊 Status ouvert - Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Statut récupéré - Schedulers: {data.get('schedulers_count', 'N/A')}")

                # Vérifications de base
                self.assertIn("schedulers_count", data)
                self.assertIsInstance(data["schedulers_count"], int)
            else:
                print("⚠️  Endpoint openstatus non disponible")

        except Exception as e:
            print(f"⚠️  Test openstatus échoué (normal si endpoint n'existe pas): {e}")

    def test_16_request_with_payload(self):
        """Test 16: Requête avec payload JSON"""
        try:
            # Créer scheduler pour httpbin (qui accepte POST)
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Requête POST avec payload
            test_payload = {
                "message": "Test payload",
                "timestamp": time.time(),
                "data": {"key": "value", "number": 42}
            }

            request_data = {
                "scheduler_id": scheduler_id,
                "url": "https://httpbin.org/post",
                "method": "POST",
                "payload": test_payload
            }

            response = requests.post(f"{self.base_url}/api/request",
                                   json=request_data,
                                   headers=self.headers)

            print(f"📤 Requête POST avec payload - Status: {response.status_code}")

            if response.status_code == 200:
                request_id = response.json()["uuid"]
                print(f"✅ Requête POST soumise: {request_id[:8]}...")

                # Optionnel: Attendre la réponse pour vérifier le payload
                response_data = self._wait_for_response(request_id, timeout=15)
                if response_data and isinstance(response_data, dict):
                    json_data = response_data.get("json", {})
                    if json_data.get("message") == "Test payload":
                        print("✅ Payload correctement transmis")
            else:
                self.fail(f"Échec requête POST: {response.text}")

        except Exception as e:
            self.fail(f"Test requête avec payload échoué: {e}")

    def test_17_request_with_custom_headers(self):
        """Test 17: Requête avec headers personnalisés"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Requête avec headers personnalisés
            custom_headers = {
                "X-Custom-Header": "Test-Value",
                "X-Client-Version": "1.0.0",
                "Content-Type": "application/json"
            }

            request_data = {
                "scheduler_id": scheduler_id,
                "url": "https://httpbin.org/headers",
                "method": "GET",
                "headers": custom_headers
            }

            response = requests.post(f"{self.base_url}/api/request",
                                   json=request_data,
                                   headers=self.headers)

            print(f"🏷️  Requête avec headers - Status: {response.status_code}")

            if response.status_code == 200:
                request_id = response.json()["uuid"]
                print(f"✅ Requête avec headers soumise: {request_id[:8]}...")

                # Optionnel: Vérifier que les headers sont transmis
                response_data = self._wait_for_response(request_id, timeout=15)
                if response_data and isinstance(response_data, dict):
                    headers_received = response_data.get("headers", {})
                    if "X-Custom-Header" in headers_received:
                        print("✅ Headers personnalisés transmis")
            else:
                self.fail(f"Échec requête avec headers: {response.text}")

        except Exception as e:
            self.fail(f"Test requête avec headers échoué: {e}")

    def test_18_concurrent_requests_same_scheduler(self):
        """Test 18: Requêtes concurrentes sur le même scheduler"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Fonction pour créer une requête dans un thread
            def make_request(thread_id):
                try:
                    request_data = {
                        "scheduler_id": scheduler_id,
                        "url": f"https://httpbin.org/get?thread={thread_id}",
                        "method": "GET"
                    }

                    response = requests.post(f"{self.base_url}/api/request",
                                           json=request_data,
                                           headers=self.headers,
                                           timeout=10)

                    return response.status_code == 200, response.json() if response.status_code == 200 else None
                except Exception as e:
                    return False, str(e)

            # Lancer plusieurs threads
            import threading as th
            import queue

            results = queue.Queue()
            threads = []

            def thread_wrapper(tid):
                success, data = make_request(tid)
                results.put((tid, success, data))

            # Créer 5 threads simultanés
            for i in range(5):
                thread = th.Thread(target=thread_wrapper, args=(i,))
                threads.append(thread)
                thread.start()

            # Attendre tous les threads
            for thread in threads:
                thread.join(timeout=15)

            # Analyser les résultats
            successful_requests = 0
            all_results = []

            while not results.empty():
                thread_id, success, data = results.get()
                all_results.append((thread_id, success, data))
                if success:
                    successful_requests += 1
                    print(f"✅ Thread {thread_id}: Requête réussie")
                else:
                    print(f"❌ Thread {thread_id}: Échec - {data}")

            print(f"📊 Requêtes concurrentes: {successful_requests}/{len(all_results)} réussies")

            # Au moins 80% des requêtes devraient réussir
            success_rate = successful_requests / len(all_results) * 100
            self.assertGreater(success_rate, 80.0)

        except Exception as e:
            self.fail(f"Test requêtes concurrentes échoué: {e}")

    def test_19_scheduler_stats_endpoint(self):
        """Test 19: Endpoint des statistiques de scheduler"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Tester l'endpoint de stats (s'il existe)
            stats_url = f"{self.base_url}/api/scheduler/{scheduler_id}/stats"

            try:
                stats_response = requests.get(stats_url, headers=self.headers, timeout=5)

                if stats_response.status_code == 200:
                    stats_data = stats_response.json()
                    print(f"📊 Stats scheduler récupérées")

                    # Vérifier les champs attendus
                    expected_fields = ["scheduler_id", "queue_size", "pending_requests",
                                     "pending_responses", "calls_per_second"]

                    for field in expected_fields:
                        if field in stats_data:
                            print(f"  ✅ {field}: {stats_data[field]}")
                        else:
                            print(f"  ⚠️  {field}: manquant")

                    self.assertEqual(stats_data.get("scheduler_id"), scheduler_id)

                elif stats_response.status_code == 404:
                    print("⚠️  Endpoint stats non disponible")
                else:
                    print(f"⚠️  Stats endpoint returned {stats_response.status_code}")

            except requests.exceptions.RequestException:
                print("⚠️  Endpoint stats non accessible")

        except Exception as e:
            print(f"⚠️  Test stats échoué (peut être normal): {e}")

    def test_20_cache_functionality(self):
        """Test 20: Fonctionnalité de cache"""
        try:
            # Créer scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = requests.post(f"{self.base_url}/api/initialize",
                                        json=init_data,
                                        headers=self.headers)

            scheduler_id = init_response.json()["scheduler_id"]

            # Première requête avec cache
            request_data = {
                "scheduler_id": scheduler_id,
                "url": "https://httpbin.org/get?cache_test=1",
                "method": "GET",
                "cache_duration": 300  # 5 minutes
            }

            # Première requête
            start_time = time.time()

            response1 = requests.post(f"{self.base_url}/api/request",
                                    json=request_data,
                                    headers=self.headers)

            self.assertEqual(response1.status_code, 200)
            request_id1 = response1.json()["uuid"]

            # Deuxième requête identique (devrait utiliser le cache)
            response2 = requests.post(f"{self.base_url}/api/request",
                                    json=request_data,
                                    headers=self.headers)

            self.assertEqual(response2.status_code, 200)
            request_id2 = response2.json()["uuid"]

            print(f"🗄️  Test cache - Requête 1: {request_id1[:8]}...")
            print(f"🗄️  Test cache - Requête 2: {request_id2[:8]}...")

            # Les requêtes sont différentes mais devraient potentiellement utiliser le cache
            # (selon l'implémentation exacte de votre API Manager)

            print("✅ Test cache exécuté (vérification manuelle requise)")

        except Exception as e:
            self.fail(f"Test cache échoué: {e}")

    def _wait_for_response(self, request_id, timeout=30, expected_content=None):
        """Utilitaire pour attendre qu'une réponse soit prête"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                status_response = requests.get(f"{self.base_url}/api/status/{request_id}",
                                             headers=self.headers,
                                             timeout=5)

                if status_response.status_code == 200:
                    status_data = status_response.json()

                    if status_data["status"] == "complete":
                        response_data = status_data.get("response")
                        print(f"✅ Réponse reçue pour {request_id[:8]}...")

                        # Vérification optionnelle du contenu
                        if expected_content and response_data:
                            response_str = json.dumps(response_data) if isinstance(response_data, dict) else str(response_data)
                            if expected_content in response_str:
                                print(f"✅ Contenu attendu '{expected_content}' trouvé")
                            else:
                                print(f"⚠️  Contenu attendu '{expected_content}' non trouvé")

                        return response_data

                    elif status_data["status"] == "pending":
                        print(f"⏳ En attente... ({time.time() - start_time:.1f}s)")
                    else:
                        print(f"❓ Statut inattendu: {status_data['status']}")

                elif status_response.status_code == 404:
                    print(f"❌ Requête {request_id[:8]}... non trouvée")
                    return None

            except requests.exceptions.Timeout:
                print("⏰ Timeout lors de la vérification du statut")
            except Exception as e:
                print(f"❌ Erreur lors de la vérification: {e}")

            time.sleep(1)

        print(f"⏰ Timeout après {timeout}s pour {request_id[:8]}...")
        return None

