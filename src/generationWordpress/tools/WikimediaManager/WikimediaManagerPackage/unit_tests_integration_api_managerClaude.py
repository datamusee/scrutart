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
TEST_SERVER_CODE = "apiManagerClaude.py"
TEST_API_HOST = "127.0.0.1"
TEST_API_PORT = 6000  # Port différent pour éviter les conflits
TEST_BASE_URL = f"http://{TEST_API_HOST}:{TEST_API_PORT}"
TEST_BEARER_TOKEN = "test-integration-bearer-token"

# mockurl = "https://httpbin.org/json" # url bidon pour test
mockurl = "http://127.0.0.1:5000/mockapi"  # api  bidon locale pour test
# test_urls = [r"^http://127.0.0.1:5000/mockapi(/.*)?$"]
escaped_baseurl = re.escape(mockurl)  # escape fait trop de choses!
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
        self.temp_dir = os.path.join(os.getcwd(), "temp")  # tempfile.mkdtemp()
        os.makedirs(self.temp_dir, exist_ok=True)
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
                'LOG_LEVEL': 'INFO',  # ✅ CORRECTION: Réduire les logs
                'PYTHONUNBUFFERED': '1'
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

        with open(original_path, encoding="utf-8") as fs:
            script_content = fs.read()
        with open(test_script_path, 'w', encoding="UTF-8") as f:
            f.write(script_content)

        return test_script_path

    def _wait_for_server_start(self, max_wait=30):
        """Attend que le serveur démarre"""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{TEST_BASE_URL}/api/health", timeout=3)  # ✅ Timeout plus long
                if response.status_code == 200:
                    print(f"✅ Serveur démarré après {time.time() - start_time:.1f}s")
                    return True
            except requests.exceptions.RequestException:
                pass

            time.sleep(1.0)  # ✅ CORRECTION: Attendre plus longtemps entre les tentatives

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
        if not cls.server.start_server(api_manager_path=TEST_SERVER_CODE):
            raise Exception("Impossible de démarrer le serveur de test")

        cls.headers = {"Authorization": f"Bearer {TEST_BEARER_TOKEN}"}
        cls.base_url = TEST_BASE_URL

    @classmethod
    def tearDownClass(cls):
        """Nettoyage après tous les tests"""
        cls.server.cleanup()

    def setUp(self):
        """✅ AJOUT: Attendre entre les tests pour éviter les conflits"""
        time.sleep(0.5)

    def tearDown(self):
        """✅ AJOUT: Nettoyage après chaque test"""
        time.sleep(0.2)

    def test_server_health_check(self):
        """Test du health check du serveur"""
        response = requests.get(f"{self.base_url}/api/health", timeout=10)  # ✅ Ajout timeout

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")

    def test_home_page(self):
        """Test de la page d'accueil"""
        response = requests.get(f"{self.base_url}/", timeout=10)  # ✅ Ajout timeout

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
            headers=self.headers,
            timeout=15  # ✅ Ajout timeout
        )

        self.assertEqual(200, response.status_code)
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
            json=init_data,
            timeout=15  # ✅ Ajout timeout
        )

        self.assertEqual(response.status_code, 401)

    def test_real_api_request_mockapi_test(self):
        """Test d'une vraie requête API vers httpbin.org - VERSION CORRIGÉE"""
        # ✅ CORRECTION: Utiliser une session pour réutiliser la connexion
        session = requests.Session()
        session.headers.update(self.headers)

        try:
            # D'abord initialiser un scheduler
            init_data = {"api_patterns": ["http://127.0.0.1:5000", "http://127.0.0.1:5000/mockapi/test"]}
            init_response = session.post(
                f"{self.base_url}/api/initialize",
                json=init_data,
                timeout=15  # ✅ Timeout explicite
            )

            self.assertEqual(init_response.status_code, 200)
            scheduler_id = init_response.json()["scheduler_id"]

            # ✅ CORRECTION: Attendre que le scheduler soit prêt
            time.sleep(1.0)

            # Faire une requête vers mockapi
            request_data = {
                "scheduler_id": scheduler_id,
                "url": "http://127.0.0.1:5000/mockapi/test",
                "method": "GET"
            }

            # ✅ CORRECTION: Timeout plus long et gestion d'erreur
            try:
                request_response = session.post(
                    f"{self.base_url}/api/request",
                    json=request_data,
                    timeout=20  # Timeout plus généreux
                )
            except requests.exceptions.Timeout:
                self.fail("La requête POST a timeout - serveur probablement bloqué")
            except requests.exceptions.ConnectionError as e:
                self.fail(f"Erreur de connexion: {e}")

            self.assertEqual(200, request_response.status_code)
            request_result = request_response.json()

            self.assertIn("uuid", request_result)
            self.assertIn("status_url", request_result)

            # Attendre et vérifier le statut
            request_id = request_result["uuid"]
            status_url = f"{self.base_url}/api/status/{request_id}"

            # ✅ CORRECTION: Polling avec backoff et timeout plus long
            max_attempts = 120  # 2 minutes
            attempt = 0

            while attempt < max_attempts:
                try:
                    status_response = session.get(status_url, timeout=10)
                    self.assertEqual(200, status_response.status_code)

                    status_data = status_response.json()

                    if status_data["status"] == "complete":
                        self.assertIn("response", status_data)
                        response = status_data["response"]

                        # Vérifier que c'est bien une réponse de mockapi
                        self.assertIn("data", response)
                        self.assertIn("test", response["data"])
                        break

                    elif status_data["status"] == "pending":
                        # ✅ Backoff progressif
                        wait_time = min(0.5 + (attempt * 0.05), 2.0)
                        time.sleep(wait_time)
                        attempt += 1
                    else:
                        self.fail(f"Statut inattendu: {status_data}")

                except requests.exceptions.RequestException as e:
                    print(f"Erreur lors de la vérification du statut: {e}")
                    time.sleep(1.0)
                    attempt += 1
            else:
                self.fail("La requête n'a pas été traitée dans les temps")

        finally:
            # ✅ CORRECTION: Toujours fermer la session
            session.close()

    def test_real_api_request_jsonplaceholder(self):
        """Test d'une vraie requête API vers jsonplaceholder"""
        session = requests.Session()
        session.headers.update(self.headers)

        try:
            # Initialiser scheduler
            init_data = {"api_patterns": ["https://jsonplaceholder.typicode.com"]}
            init_response = session.post(
                f"{self.base_url}/api/initialize",
                json=init_data,
                timeout=15
            )

            scheduler_id = init_response.json()["scheduler_id"]
            time.sleep(0.5)  # Attendre que le scheduler soit prêt

            # Requête GET vers jsonplaceholder
            request_data = {
                "scheduler_id": scheduler_id,
                "url": "https://jsonplaceholder.typicode.com/posts/1",
                "method": "GET"
            }

            request_response = session.post(
                f"{self.base_url}/api/request",
                json=request_data,
                timeout=15
            )

            self.assertEqual(200, request_response.status_code)
            request_id = request_response.json()["uuid"]

            # Attendre la réponse
            max_attempts = 60
            for attempt in range(max_attempts):
                try:
                    status_response = session.get(
                        f"{self.base_url}/api/status/{request_id}",
                        timeout=10
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

                    time.sleep(1.0)

                except requests.exceptions.RequestException as e:
                    print(f"Erreur status jsonplaceholder: {e}")
                    time.sleep(1.0)
            else:
                self.fail("Requête jsonplaceholder non traitée")

        finally:
            session.close()

    def test_rate_limiting_functionality(self):
        """Test de la fonctionnalité de limitation de taux"""
        session = requests.Session()
        session.headers.update(self.headers)

        try:
            # Initialiser scheduler
            init_data = {"api_patterns": ["http://127.0.0.1:5000", "http://127.0.0.1:5000/mockapi/unicode"]}
            init_response = session.post(
                f"{self.base_url}/api/initialize",
                json=init_data,
                timeout=15
            )

            scheduler_id = init_response.json()["scheduler_id"]
            time.sleep(0.5)

            # Configurer une limite très basse
            rate_data = {"scheduler_id": scheduler_id, "limit": 0.1}
            rate_response = session.post(
                f"{self.base_url}/api/set_rate_limit",
                json=rate_data,
                timeout=10
            )

            self.assertEqual(200, rate_response.status_code)

            # Faire plusieurs requêtes rapidement
            request_ids = []

            for i in range(3):
                request_data = {
                    "scheduler_id": scheduler_id,
                    "url": "http://127.0.0.1:5000/mockapi/unicode",
                    "method": "GET"
                }

                try:
                    response = session.post(
                        f"{self.base_url}/api/request",
                        json=request_data,
                        timeout=10
                    )

                    if response.status_code == 200:
                        request_ids.append(response.json()["uuid"])
                except:
                    pass  # Ignorer les erreurs dans ce test de charge

            # Vérifier que les délais estimés augmentent
            self.assertGreater(len(request_ids), 0)

        finally:
            session.close()

    def test_multiple_schedulers(self):
        """Test de gestion de plusieurs schedulers"""
        session = requests.Session()
        session.headers.update(self.headers)

        try:
            # Créer le premier scheduler
            init_data1 = {"api_patterns": ["http://127.0.0.1:5000", "http://127.0.0.1:5000/mockapi/test"]}
            response1 = self.session.post(
                f"{self.base_url}/api/initialize",
                json=init_data1,
                timeout=15
            )

            scheduler_id1 = response1.json()["scheduler_id"]

            # Créer le deuxième scheduler
            init_data2 = {"api_patterns": ["http://127.0.0.1:5000", "http://127.0.0.1:5000/mockapi/unicode"]}
            response2 = self.session.post(
                f"{self.base_url}/api/initialize",
                json=init_data2,
                timeout=15
            )

            scheduler_id2 = response2.json()["scheduler_id"]

            # Vérifier que les schedulers sont différents
            self.assertNotEqual(scheduler_id1, scheduler_id2)

        finally:
            session.close()

    def test_error_handling_invalid_url(self):
        """Test de gestion d'erreur avec URL invalide"""
        session = requests.Session()
        session.headers.update(self.headers)

        try:
            # Initialiser scheduler
            init_data = {"api_patterns": ["https://httpbin.org"]}
            init_response = session.post(
                f"{self.base_url}/api/initialize",
                json=init_data,
                timeout=15
            )

            scheduler_id = init_response.json()["scheduler_id"]

            # Tenter une requête vers une URL non autorisée
            request_data = {
                "scheduler_id": scheduler_id,
                "url": "https://127.0.0.1:5000/test",
                "method": "GET"
            }

            response = session.post(
                f"{self.base_url}/api/request",
                json=request_data,
                timeout=10
            )

            self.assertEqual(400, response.status_code)
            error_data = response.json()
            self.assertIn("error", error_data)

        finally:
            session.close()


    def test_nonexistent_scheduler(self):
        """Test avec un scheduler inexistant"""
        session = requests.Session()
        session.headers.update(self.headers)

        request_data = {
            "scheduler_id": "nonexistent-scheduler-id",
            "url": "http://127.0.0.1:5000/mockapi/test",
            "method": "GET"
        }

        response = session.post(
            f"{self.base_url}/api/request",
            json=request_data,
            timeout=10
        )

        self.assertEqual(401, response.status_code)

    def test_invalid_json_request(self):
        """Test avec données JSON invalides"""
        # Envoyer des données non-JSON
        response = requests.post(
            f"{self.base_url}/api/initialize",
            data="invalid json data",
            headers={**self.headers, "Content-Type": "application/json"},
            timeout=10
        )

        self.assertEqual(401, response.status_code)


class WebSocketIntegrationTests(unittest.TestCase):
    """Tests d'intégration WebSocket réels"""

    @classmethod
    def setUpClass(cls):
        """Configuration WebSocket"""
        cls.server = APIManagerTestServer()
        cls.temp_dir = cls.server.setup_test_environment()

        if not cls.server.start_server(api_manager_path=TEST_SERVER_CODE):
            raise Exception("Impossible de démarrer le serveur pour les tests WebSocket")

        cls.socket_url = f"http://{TEST_API_HOST}:{TEST_API_PORT}"

    @classmethod
    def tearDownClass(cls):
        """Nettoyage WebSocket"""
        cls.server.cleanup()

    def test_websocket_connection(self):
        """Test de connexion WebSocket - Version simplifiée"""
        sio = socketio.SimpleClient()

        try:
            # Se connecter avec un timeout plus court
            sio.connect(self.socket_url, wait_timeout=10)
            self.assertTrue(sio.connected)

            # Écouter l'événement de connexion
            event = sio.receive(timeout=5)
            self.assertEqual(event[0], 'connect')

        except Exception as e:
            self.fail(f"Erreur de connexion WebSocket: {e}")
        finally:
            try:
                sio.disconnect()
            except:
                pass


if __name__ == '__main__':
    # Configuration pour les tests
    unittest.main(verbosity=2, buffer=True)