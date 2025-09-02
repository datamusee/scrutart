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
import psutil  # Ajout pour gestion avancée des processus

# Configuration des tests d'intégration
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
        self.session = None  # Session réutilisable pour éviter les connexions multiples

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

        # Créer une session requests réutilisable
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {TEST_BEARER_TOKEN}"})

        return self.temp_dir

    def start_server(self, api_manager_path="apiManagerClaude.py"):
        """Démarre le serveur API Manager en subprocess"""
        try:
            # Tuer tout processus existant sur le port de test
            self._kill_existing_processes()

            # Variables d'environnement pour le test
            env = os.environ.copy()
            env.update({
                'PYTHONPATH': self.temp_dir,
                'API_IP_ADDRESS': TEST_API_HOST,
                'API_PORT': str(TEST_API_PORT),
                'LOG_LEVEL': 'INFO',  # Réduire le niveau de log pour éviter la saturation
                'PYTHONUNBUFFERED': '1'  # Assurer la sortie immédiate des logs
            })

            # Créer une version modifiée du script pour les tests
            test_script = self._create_test_script(api_manager_path)

            # Démarrer le serveur
            self.process = subprocess.Popen(
                [sys.executable, test_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.temp_dir,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Créer un groupe de processus
            )

            # Attendre que le serveur démarre
            self._wait_for_server_start()

            return True

        except Exception as e:
            print(f"Erreur lors du démarrage du serveur: {e}")
            return False

    def _kill_existing_processes(self):
        """Tue les processus existants sur le port de test"""
        try:
            # Utiliser psutil pour trouver les processus utilisant le port
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    connections = proc.info['connections']
                    if connections:
                        for conn in connections:
                            if hasattr(conn, 'laddr') and conn.laddr and conn.laddr.port == TEST_API_PORT:
                                print(
                                    f"Tuant le processus {proc.info['pid']} ({proc.info['name']}) utilisant le port {TEST_API_PORT}")
                                proc.terminate()
                                proc.wait(timeout=3)
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    pass
        except ImportError:
            # Fallback si psutil n'est pas disponible
            try:
                import subprocess
                result = subprocess.run(['lsof', '-ti', f':{TEST_API_PORT}'],
                                        capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            print(f"Processus {pid} terminé")
                        except ProcessLookupError:
                            pass
            except FileNotFoundError:
                pass  # lsof non disponible

    def _create_test_script(self, original_path):
        """Crée une version du script adaptée aux tests"""
        test_script_path = os.path.join(self.temp_dir, "test_api_manager.py")

        with open("apiManagerClaude.py", encoding="utf-8") as fs:
            script_content = fs.read()

        # Modification pour améliorer l'arrêt propre dans les tests
        modified_content = script_content.replace(
            'socketio.run(',
            '''try:
        socketio.run('''
        ).replace(
            'use_reloader=False  # Évite les problèmes avec les threads',
            '''use_reloader=False,  # Évite les problèmes avec les threads
            allow_unsafe_werkzeug=True  # Pour les tests seulement
        )
    except KeyboardInterrupt:
        pass  # Gestion propre de l'interruption
    except Exception as e:
        logger.error(f"Erreur serveur: {e}")
    finally:
        cleanup_on_shutdown()'''
        )

        with open(test_script_path, 'w', encoding="UTF-8") as f:
            f.write(modified_content)

        return test_script_path

    def _wait_for_server_start(self, max_wait=30):
        """Attend que le serveur démarre avec retry et backoff"""
        start_time = time.time()
        retry_count = 0
        max_retries = 5

        while time.time() - start_time < max_wait:
            try:
                # Utiliser la session réutilisable
                response = self.session.get(f"{TEST_BASE_URL}/api/health", timeout=3)
                if response.status_code == 200:
                    print(f"✅ Serveur démarré après {time.time() - start_time:.1f}s")
                    return True
            except requests.exceptions.RequestException as e:
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"Tentative {retry_count}: {e}")
                time.sleep(min(2 ** retry_count, 5))  # Backoff exponentiel limité à 5s

        # Vérifier si le processus est encore vivant
        if self.process and self.process.poll() is None:
            # Le processus tourne mais ne répond pas
            print("⚠️ Le serveur est démarré mais ne répond pas aux requêtes HTTP")
            return False
        else:
            print("❌ Le processus serveur s'est arrêté de manière inattendue")
            return False

        raise Exception(f"Le serveur n'a pas démarré dans les {max_wait}s")

    def stop_server(self):
        """Arrête le serveur proprement"""
        if self.process:
            try:
                # Essayer d'abord un arrêt propre
                if hasattr(os, 'killpg'):
                    # Unix: tuer le groupe de processus
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    # Windows: terminer le processus
                    self.process.terminate()

                # Attendre l'arrêt
                try:
                    self.process.wait(timeout=10)
                    print("✅ Serveur arrêté proprement")
                except subprocess.TimeoutExpired:
                    print("⚠️ Timeout lors de l'arrêt propre, passage à l'arrêt forcé")
                    if hasattr(os, 'killpg'):
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    else:
                        self.process.kill()
                    self.process.wait()
                    print("⚠️ Serveur forcé à s'arrêter")

            except Exception as e:
                print(f"Erreur lors de l'arrêt: {e}")
                try:
                    self.process.kill()
                    self.process.wait()
                except:
                    pass

        # Fermer la session requests
        if self.session:
            self.session.close()

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

        # Session réutilisable pour tous les tests
        cls.session = requests.Session()
        cls.session.headers.update(cls.headers)

    @classmethod
    def tearDownClass(cls):
        """Nettoyage après tous les tests"""
        if hasattr(cls, 'session'):
            cls.session.close()
        cls.server.cleanup()

    def setUp(self):
        """Configuration avant chaque test"""
        # Nettoyer tous les schedulers existants avant chaque test
        self._cleanup_schedulers()

    def _cleanup_schedulers(self):
        """Nettoie tous les schedulers existants"""
        try:
            # Obtenir la liste des schedulers actifs
            status_response = self.session.get(f"{self.base_url}/api/openstatus")
            if status_response.status_code == 200:
                status_data = status_response.json()
                for scheduler_info in status_data.get("schedulers", []):
                    scheduler_id = scheduler_info.get("scheduler_id")
                    if scheduler_id:
                        # Tenter de supprimer le scheduler
                        delete_url = f"{self.base_url}/api/delete_scheduler?scheduler_id={scheduler_id}"
                        try:
                            self.session.delete(delete_url)
                        except:
                            pass  # Ignorer les erreurs de suppression

            # Attendre un peu pour que le nettoyage soit effectif
            time.sleep(0.5)

        except Exception as e:
            print(f"Erreur lors du nettoyage des schedulers: {e}")

    def tearDown(self):
        """Nettoyage après chaque test"""
        self._cleanup_schedulers()
        # Pause entre les tests pour éviter les race conditions
        time.sleep(0.2)

    def test_server_health_check(self):
        """Test du health check du serveur"""
        response = self.session.get(f"{self.base_url}/api/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")

    def test_home_page(self):
        """Test de la page d'accueil"""
        response = self.session.get(f"{self.base_url}/")

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

        response = self.session.post(
            f"{self.base_url}/api/initialize",
            json=init_data
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

        # Utiliser requests directement sans la session (pas d'auth)
        response = requests.post(
            f"{self.base_url}/api/initialize",
            json=init_data
        )

        self.assertEqual(response.status_code, 401)

    def test_real_api_request_mockapi_test(self):
        """Test d'une vraie requête API vers mockapi - VERSION CORRIGÉE"""
        try:
            # ÉTAPE 1: Initialiser un scheduler proprement
            init_data = {"api_patterns": ["http://127.0.0.1:5000", "http://127.0.0.1:5000/mockapi/test"]}
            init_response = self.session.post(
                f"{self.base_url}/api/initialize",
                json=init_data
            )

            self.assertEqual(init_response.status_code, 200)
            scheduler_id = init_response.json()["scheduler_id"]

            # ÉTAPE 2: Attendre que le scheduler soit prêt
            time.sleep(1.0)

            # ÉTAPE 3: Faire la requête avec timeout plus long
            request_data = {
                "scheduler_id": scheduler_id,
                "url": "http://127.0.0.1:5000/mockapi/test",
                "method": "GET"
            }

            # ✅ POINT CRITIQUE: Utiliser un timeout plus long et une session dédiée
            try:
                request_response = self.session.post(
                    f"{self.base_url}/api/request",
                    json=request_data,
                    timeout=30  # Timeout plus long pour éviter les blocages
                )
            except requests.exceptions.Timeout:
                self.fail("Timeout lors de la soumission de la requête - Le serveur ne répond pas")
            except requests.exceptions.ConnectionError as e:
                self.fail(f"Erreur de connexion lors de la soumission: {e}")

            self.assertEqual(200, request_response.status_code)
            request_result = request_response.json()

            self.assertIn("uuid", request_result)
            self.assertIn("status_url", request_result)

            # ÉTAPE 4: Polling du statut avec backoff
            request_id = request_result["uuid"]
            status_url = f"{self.base_url}/api/status/{request_id}"

            max_attempts = 120  # 2 minutes maximum
            attempt = 0
            last_status = None

            while attempt < max_attempts:
                try:
                    status_response = self.session.get(status_url, timeout=10)
                    self.assertEqual(200, status_response.status_code)

                    status_data = status_response.json()
                    last_status = status_data.get("status")

                    if status_data["status"] == "complete":
                        self.assertIn("response", status_data)
                        response = status_data["response"]

                        # Vérifier que c'est bien une réponse de mockapi
                        self.assertIn("data", response)
                        self.assertIn("test", response["data"])
                        return  # Test réussi

                    elif status_data["status"] == "pending":
                        # Backoff progressif: 0.5s -> 1s -> 1.5s -> 2s -> 2s...
                        wait_time = min(0.5 + (attempt * 0.1), 2.0)
                        time.sleep(wait_time)
                        attempt += 1

                    else:
                        self.fail(f"Statut inattendu: {status_data}")

                except requests.exceptions.RequestException as e:
                    print(f"Erreur de requête statut (tentative {attempt}): {e}")
                    time.sleep(1.0)
                    attempt += 1

            # Si on arrive ici, le timeout est atteint
            self.fail(f"La requête n'a pas été traitée dans les temps (dernier statut: {last_status})")

        except Exception as e:
            self.fail(f"Erreur inattendue dans test_real_api_request_mockapi_test: {e}")

    def test_real_api_request_jsonplaceholder(self):
        """Test d'une vraie requête API vers jsonplaceholder"""
        # Initialiser scheduler
        init_data = {"api_patterns": ["https://jsonplaceholder.typicode.com"]}
        init_response = self.session.post(
            f"{self.base_url}/api/initialize",
            json=init_data
        )

        scheduler_id = init_response.json()["scheduler_id"]

        # Attendre que le scheduler soit prêt
        time.sleep(0.5)

        # Requête GET vers jsonplaceholder
        request_data = {
            "scheduler_id": scheduler_id,
            "url": "https://jsonplaceholder.typicode.com/posts/1",
            "method": "GET"
        }

        request_response = self.session.post(
            f"{self.base_url}/api/request",
            json=request_data,
            timeout=15
        )

        self.assertEqual(200, request_response.status_code)
        request_id = request_response.json()["uuid"]

        # Attendre la réponse avec timeout plus long
        max_attempts = 60
        for attempt in range(max_attempts):
            try:
                status_response = self.session.get(
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
                    return

                time.sleep(1.0)

            except requests.exceptions.RequestException as e:
                print(f"Erreur statut jsonplaceholder (tentative {attempt}): {e}")
                time.sleep(1.0)

        self.fail("Requête jsonplaceholder non traitée dans les temps")

    def test_rate_limiting_functionality(self):
        """Test de la fonctionnalité de limitation de taux"""
        # Initialiser scheduler avec limite de taux très basse
        init_data = {"api_patterns": ["http://127.0.0.1:5000", "http://127.0.0.1:5000/mockapi/unicode"]}
        init_response = self.session.post(
            f"{self.base_url}/api/initialize",
            json=init_data
        )

        scheduler_id = init_response.json()["scheduler_id"]

        # Attendre que le scheduler soit prêt
        time.sleep(0.5)

        # Configurer une limite très basse (0.1 requête/seconde)
        rate_data = {"scheduler_id": scheduler_id, "limit": 0.1}
        rate_response = self.session.post(
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
                response = self.session.post(
                    f"{self.base_url}/api/request",
                    json=request_data,
                    timeout=10
                )

                if response.status_code == 200:
                    request_ids.append(response.json()["uuid"])
            except requests.exceptions.RequestException:
                pass  # Ignorer les erreurs de connexion dans ce test

        # Vérifier qu'au moins une requête a été acceptée
        self.assertGreater(len(request_ids), 0)

    def test_multiple_schedulers(self):
        """Test de gestion de plusieurs schedulers"""
        # Créer le premier scheduler
        init_data1 = {"api_patterns": ["http://127.0.0.1:5000/mockapi/test"]}
        response1 = self.session.post(
            f"{self.base_url}/api/initialize",
            json=init_data1
        )

        scheduler_id1 = response1.json()["scheduler_id"]

        # Créer le deuxième scheduler
        init_data2 = {"api_patterns": ["http://127.0.0.1:5000/mockapi/unicode"]}
        response2 = self.session.post(
            f"{self.base_url}/api/initialize",
            json=init_data2
        )

        scheduler_id2 = response2.json()["scheduler_id"]

        # Vérifier que les schedulers sont différents
        self.assertNotEqual(scheduler_id1, scheduler_id2)

    def test_error_handling_invalid_url(self):
        """Test de gestion d'erreur avec URL invalide"""
        # Initialiser scheduler
        init_data = {"api_patterns": ["https://httpbin.org"]}
        init_response = self.session.post(
            f"{self.base_url}/api/initialize",
            json=init_data
        )

        scheduler_id = init_response.json()["scheduler_id"]

        # Tenter une requête vers une URL non autorisée
        request_data = {
            "scheduler_id": scheduler_id,
            "url": "https://127.0.0.1:5000/test",
            "method": "GET"
        }

        response = self.session.post(
            f"{self.base_url}/api/request",
            json=request_data,
            timeout=10
        )

        self.assertEqual(400, response.status_code)
        error_data = response.json()
        self.assertIn("error", error_data)

    def test_nonexistent_scheduler(self):
        """Test avec un scheduler inexistant"""
        request_data = {
            "scheduler_id": "nonexistent-scheduler-id",
            "url": "http://127.0.0.1:5000/mockapi/test",
            "method": "GET"
        }

        response = self.session.post(
            f"{self.base_url}/api/request",
            json=request_data,
            timeout=10
        )

        self.assertEqual(response.status_code, 404)

    def test_invalid_json_request(self):
        """Test avec données JSON invalides"""
        # Envoyer des données non-JSON
        response = requests.post(
            f"{self.base_url}/api/initialize",
            data="invalid json data",
            headers={**self.headers, "Content-Type": "application/json"},
            timeout=10
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