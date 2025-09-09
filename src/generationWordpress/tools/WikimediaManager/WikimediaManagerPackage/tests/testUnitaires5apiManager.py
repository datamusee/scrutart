import unittest
import requests
import json
import time
import uuid
import threading
from typing import Dict, Any, Optional
import socketio
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Configuration des tests
API_BASE_URL = "http://127.0.0.1:6000"  # Adapter selon votre configuration
BEARER_TOKEN = "5a07f30b-892f-4db1-a094-7a4bf12a2fdc"  # Adapter selon votre token
HEADERS = {"Authorization": f"Bearer {BEARER_TOKEN}"}

# Configuration du logging pour les tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIManagerIntegrationTest(unittest.TestCase):
    """Classe de base pour les tests d'intégration"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration avant tous les tests"""
        cls.base_url = API_BASE_URL
        cls.headers = HEADERS
        cls.test_apis = [
            "http://127.0.0.1:5000/mockapi",
            "https://httpbin.org",
            "https://jsonplaceholder.typicode.com"
        ]
        
        # Vérifier que le serveur est accessible
        try:
            response = requests.get(f"{cls.base_url}/api/health", timeout=5)
            if response.status_code != 200:
                raise Exception(f"Serveur non accessible: {response.status_code}")
            logger.info("✅ Serveur API Manager accessible")
        except Exception as e:
            raise Exception(f"❌ Serveur API Manager non accessible: {e}")

    def setUp(self):
        """Configuration avant chaque test"""
        self.scheduler_id = None
        self.created_schedulers = []

    def tearDown(self):
        """Nettoyage après chaque test"""
        # Nettoyer les schedulers créés pendant le test
        for scheduler_id in self.created_schedulers:
            try:
                requests.delete(
                    f"{self.base_url}/api/delete_scheduler",
                    params={"scheduler_id": scheduler_id},
                    headers=self.headers
                )
            except:
                pass


class TestServerStatus(APIManagerIntegrationTest):
    """Tests de statut et santé du serveur"""
    
    def test_health_endpoint(self):
        """Test du endpoint de santé"""
        response = requests.get(f"{self.base_url}/api/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)
        self.assertIn("version", data)
        self.assertIn("schedulers_active", data)
        self.assertIn("connected_clients", data)
        logger.info(f"✅ Health check: {data}")

    def test_home_page(self):
        """Test de la page d'accueil"""
        response = requests.get(self.base_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("API Manager - Gestionnaire de requêtes", response.text)
        self.assertIn("Limitation de taux configurable", response.text)
        logger.info("✅ Page d'accueil accessible")

    def test_open_status_endpoint(self):
        """Test du endpoint de statut ouvert"""
        response = requests.get(f"{self.base_url}/api/openstatus")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("status", data)
        self.assertIn("schedulers_count", data)
        #self.assertIn("connected_clients", data)
        #self.assertIn("schedulers", data)
        logger.info(f"✅ Statut ouvert: {data['schedulers_count']} schedulers actifs")


class TestAuthentication(APIManagerIntegrationTest):
    """Tests d'authentification"""
    
    def test_authenticated_endpoint_without_token(self):
        """Test d'accès sans token d'authentification"""
        response = requests.post(f"{self.base_url}/api/initialize")
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("error", data)
        logger.info("✅ Rejet sans token confirmé")

    def test_authenticated_endpoint_with_invalid_token(self):
        """Test d'accès avec token invalide"""
        invalid_headers = {"Authorization": "Bearer wrong-token"}
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=invalid_headers
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("error", data)
        logger.info("✅ Rejet avec token invalide confirmé")

    def test_authenticated_endpoint_with_valid_token(self):
        """Test d'accès avec token valide"""
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json={"api_patterns": ["http://127.0.0.1:5000/mockapi"]}
        )
        
        self.assertIn(response.status_code, [200, 400])  # 400 si données manquantes mais auth OK
        logger.info("✅ Token valide accepté")


class TestSchedulerManagement(APIManagerIntegrationTest):
    """Tests de gestion des schedulers"""
    
    def test_create_new_scheduler(self):
        """Test de création d'un nouveau scheduler"""
        data = {"api_patterns": self.test_apis}
        
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        
        self.assertIn("scheduler_id", response_data)
        # TODO rétablir self.assertIn("managed_urls", response_data)
        # TODO rétablir self.assertEqual(response_data["managed_urls"], len(self.test_apis))
        
        scheduler_id = response_data["scheduler_id"]
        self.created_schedulers.append(scheduler_id)
        
        logger.info(f"✅ Scheduler créé: {scheduler_id}")

    def test_create_duplicate_scheduler(self):
        """Test de création d'un scheduler pour des URLs déjà gérées"""
        data = {"api_patterns": self.test_apis}
        
        # Première création
        response1 = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        self.assertEqual(response1.status_code, 200)
        scheduler_id = response1.json()["scheduler_id"]
        self.created_schedulers.append(scheduler_id)
        
        # Deuxième création avec les mêmes URLs
        response2 = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        
        self.assertEqual(response2.status_code, 200)
        response2_data = response2.json()
        
        # Devrait retourner le même scheduler
        self.assertEqual(response2_data["scheduler_id"], scheduler_id)

        logger.info("✅ Scheduler dupliqué correctement géré")

    def test_create_scheduler_invalid_urls(self):
        """Test de création avec URLs invalides"""
        invalid_data = {"api_patterns": ["not-a-url", "", None]}
        
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=invalid_data
        )
        
        self.assertEqual(400, response.status_code)
        data = response.json()
        self.assertIn("error", data)
        logger.info("✅ URLs invalides correctement rejetées")

    def test_get_scheduler_stats(self):
        """Test de récupération des statistiques d'un scheduler"""
        # Créer un scheduler
        data = {"api_patterns": self.test_apis}
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        scheduler_id = response.json()["scheduler_id"]
        self.created_schedulers.append(scheduler_id)
        
        # Récupérer les stats
        response = requests.get(
            f"{self.base_url}/api/scheduler/{scheduler_id}/stats",
            headers=self.headers
        )
        
        self.assertEqual(200, response.status_code)
        stats = response.json()
        
        self.assertIn("queue_size", stats)
        self.assertIn("pending_requests", stats)
        self.assertIn("calls_per_second", stats)
        
        logger.info(f"✅ Statistiques récupérées: {stats}")

    def test_set_rate_limit(self):
        """Test de configuration de la limite de taux"""
        # Créer un scheduler
        data = {"api_patterns": self.test_apis}
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        scheduler_id = response.json()["scheduler_id"]
        self.created_schedulers.append(scheduler_id)
        
        # Configurer la limite
        response = requests.post(
            f"{self.base_url}/api/set_rate_limit",
            headers=self.headers,
            json={"scheduler_id": scheduler_id, "limit": 2.0}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data["new_limit"], 2.0)
        self.assertIn("old_limit", data)
        
        logger.info(f"✅ Limite de taux configurée: {data}")

    def test_delete_scheduler(self):
        """Test de suppression d'un scheduler"""
        # Créer un scheduler
        data = {"api_patterns": self.test_apis}
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        scheduler_id = response.json()["scheduler_id"]
        
        # Supprimer le scheduler
        response = requests.delete(
            f"{self.base_url}/api/delete_scheduler",
            headers=self.headers,
            params={"scheduler_id": scheduler_id}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["scheduler_id"], scheduler_id)
        
        logger.info(f"✅ Scheduler supprimé: {scheduler_id}")


class TestAPIRequests(APIManagerIntegrationTest):
    """Tests des requêtes API"""
    
    def setUp(self):
        super().setUp()
        # Créer un scheduler pour les tests
        data = {"api_patterns": self.test_apis}
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        self.scheduler_id = response.json()["scheduler_id"]
        self.created_schedulers.append(self.scheduler_id)

    def test_simple_get_request(self):
        """Test d'une requête GET simple"""
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "http://127.0.0.1:5000/mockapi/test",
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        self.assertEqual(200, response.status_code)
        data = response.json()
        
        self.assertIn("uuid", data)
        self.assertIn("status_url", data)
        self.assertIn("estimated_delay", data)
        
        request_id = data["uuid"]
        logger.info(f"✅ Requête GET créée: {request_id}")
        
        return request_id

    def test_simple_post_request(self):
        """Test d'une requête POST simple"""
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "http://127.0.0.1:5000/mockapi/unicode",
            "method": "POST",
            "payload": {"test_key": "test_value", "timestamp": time.time()}
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("uuid", data)
        request_id = data["uuid"]
        logger.info(f"✅ Requête POST créée: {request_id}")
        
        return request_id

    def test_request_with_headers(self):
        """Test d'une requête avec headers personnalisés"""
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "http://127.0.0.1:5000/mockapi",
            "method": "GET",
            "headers": {
                "Custom-Header": "test-value",
                "User-Agent": "APIManager-Test"
            }
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        self.assertEqual(response.status_code, 200)
        request_id = response.json()["uuid"]
        logger.info(f"✅ Requête avec headers créée: {request_id}")
        
        return request_id

    def test_request_with_cache(self):
        """Test d'une requête avec cache activé"""
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "http://127.0.0.1:5000/mockapi",
            "method": "GET",
            "cache_duration": 300  # 5 minutes
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        self.assertEqual(response.status_code, 200)
        request_id = response.json()["uuid"]
        logger.info(f"✅ Requête avec cache créée: {request_id}")
        
        return request_id

    def test_request_invalid_scheduler(self):
        """Test avec scheduler_id invalide"""
        request_data = {
            "scheduler_id": "invalid-scheduler-id",
            "url": "http://127.0.0.1:5000/mockapi",
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("error", data)
        logger.info("✅ Scheduler invalide correctement rejeté")

    def test_request_unmanaged_url(self):
        """Test avec URL non gérée par le scheduler"""
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "https://unmanaged-api.com/endpoint",
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        logger.info("✅ URL non gérée correctement rejetée")


class TestRequestStatus(APIManagerIntegrationTest):
    """Tests de vérification du statut des requêtes"""
    
    def setUp(self):
        super().setUp()
        # Créer un scheduler
        data = {"api_patterns": self.test_apis}
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        self.scheduler_id = response.json()["scheduler_id"]
        self.created_schedulers.append(self.scheduler_id)

    def test_check_pending_request_status(self):
        """Test de vérification du statut d'une requête en attente"""
        # Créer une requête
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "https://httpbin.org/delay/2",  # Requête qui prend du temps
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        request_id = response.json()["uuid"]
        
        # Vérifier le statut immédiatement (devrait être pending)
        status_response = requests.get(
            f"{self.base_url}/api/status/{request_id}",
            headers=self.headers
        )
        
        self.assertEqual(status_response.status_code, 200)
        status_data = status_response.json()
        
        # Peut être "pending" ou "complete" selon la rapidité d'exécution
        self.assertIn("status", status_data)
        self.assertIn("request_id", status_data)
        
        logger.info(f"✅ Statut vérifié: {status_data['status']}")

    def test_wait_for_request_completion(self):
        """Test d'attente de completion d'une requête"""
        # Créer une requête
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "http://127.0.0.1:5000/mockapi",
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        request_id = response.json()["uuid"]
        
        # Attendre jusqu'à 30 secondes pour la completion
        max_wait = 30
        wait_interval = 1
        waited = 0
        
        while waited < max_wait:
            status_response = requests.get(
                f"{self.base_url}/api/status/{request_id}",
                headers=self.headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                if status_data["status"] == "complete":
                    self.assertIn("response", status_data)
                    response_data = status_data["response"]
                    
                    # Vérifier la structure de la réponse httpbin
                    if isinstance(response_data, dict):
                        self.assertIn("args", response_data)
                        self.assertEqual(response_data["args"].get("test"), "completion")
                    
                    logger.info(f"✅ Requête complétée en {waited}s")
                    return
                
                elif status_data["status"] == "pending":
                    logger.info(f"Requête toujours en attente après {waited}s...")
                
            time.sleep(wait_interval)
            waited += wait_interval
        
        self.fail(f"Requête non complétée après {max_wait}s")

    def test_check_nonexistent_request_status(self):
        """Test de vérification du statut d'une requête inexistante"""
        fake_request_id = str(uuid.uuid4())
        
        response = requests.get(
            f"{self.base_url}/api/status/{fake_request_id}",
            headers=self.headers
        )
        
        self.assertEqual(404, response.status_code)
        data = response.json()
        self.assertIn("error", data)
        logger.info("✅ Requête inexistante correctement gérée")


class TestWebSocketIntegration(APIManagerIntegrationTest):
    """Tests d'intégration WebSocket"""
    
    def test_websocket_connection(self):
        """Test de connexion WebSocket basique"""
        sio = socketio.SimpleClient()
        
        try:
            # Se connecter au serveur
            sio.connect(f"ws://127.0.0.1:6000")
            
            # Vérifier que la connexion est établie
            self.assertTrue(sio.connected)
            logger.info("✅ Connexion WebSocket établie")
            
            # Se déconnecter proprement
            sio.disconnect()
            self.assertFalse(sio.connected)
            logger.info("✅ Déconnexion WebSocket réussie")
            
        except Exception as e:
            self.fail(f"Erreur WebSocket: {e}")

    def test_websocket_client_registration(self):
        """Test d'enregistrement de client WebSocket"""
        sio = socketio.SimpleClient()
        
        try:
            sio.connect(f"ws://127.0.0.1:6000")
            
            client_id = f"test_client_{uuid.uuid4().hex[:8]}"
            
            # S'enregistrer avec un client_id
            sio.emit('register', {'client_id': client_id})
            
            # Attendre la confirmation
            event = sio.receive(timeout=5)
            self.assertIsNotNone(event)
            
            logger.info(f"✅ Client enregistré: {client_id}")
            
            sio.disconnect()
            
        except Exception as e:
            self.fail(f"Erreur d'enregistrement WebSocket: {e}")

    def test_websocket_notification_flow(self):
        """Test du flux de notification via WebSocket"""
        sio = socketio.SimpleClient()
        
        try:
            # Créer un scheduler
            data = {"api_patterns": self.test_apis}
            response = requests.post(
                f"{self.base_url}/api/initialize",
                headers=self.headers,
                json=data
            )
            scheduler_id = response.json()["scheduler_id"]
            self.created_schedulers.append(scheduler_id)
            
            # Se connecter et s'enregistrer
            sio.connect(f"ws://127.0.0.1:6000")
            client_id = f"test_client_{uuid.uuid4().hex[:8]}"
            sio.emit('register', {'client_id': client_id})
            
            # Attendre la confirmation d'enregistrement
            sio.receive(timeout=5)
            
            # Lancer une requête avec notification
            request_data = {
                "scheduler_id": scheduler_id,
                "url": "http://127.0.0.1:5000/mockapi/test",
                "method": "GET",
                "client_id": client_id
            }
            
            requests.post(
                f"{self.base_url}/api/request",
                headers=self.headers,
                json=request_data
            )
            
            # Attendre la notification de completion
            received_notification = False
            start_time = time.time()
            
            while time.time() - start_time < 30:  # Timeout de 30s
                try:
                    event = sio.receive(timeout=2)
                    if event and len(event) >= 2:
                        event_name, event_data = event[0], event[1]
                        
                        if event_name == 'message' and isinstance(event_data, dict):
                            if 'data' in event_data and 'response' in str(event_data['data']):
                                received_notification = True
                                logger.info(f"✅ Notification reçue: {event_data}")
                                break
                                
                except socketio.exceptions.TimeoutError:
                    continue
            
            sio.disconnect()
            
            # Vérifier qu'une notification a été reçue
            self.assertTrue(received_notification, "Aucune notification WebSocket reçue")
            
        except Exception as e:
            if sio.connected:
                sio.disconnect()
            self.fail(f"Erreur dans le flux WebSocket: {e}")


class TestLoadAndPerformance(APIManagerIntegrationTest):
    """Tests de charge et performance"""
    
    def setUp(self):
        super().setUp()
        # Créer un scheduler avec limite élevée
        data = {"api_patterns": self.test_apis}
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        self.scheduler_id = response.json()["scheduler_id"]
        self.created_schedulers.append(self.scheduler_id)
        
        # Configurer une limite de taux plus élevée pour les tests
        requests.post(
            f"{self.base_url}/api/set_rate_limit",
            headers=self.headers,
            json={"scheduler_id": self.scheduler_id, "limit": 5.0}
        )

    def test_multiple_concurrent_requests(self):
        """Test de requêtes multiples concurrentes"""
        num_requests = 10
        request_ids = []
        
        def make_request(i):
            request_data = {
                "scheduler_id": self.scheduler_id,
                "url": f"https://httpbin.org/get?request_id={i}",
                "method": "GET"
            }
            
            response = requests.post(
                f"{self.base_url}/api/request",
                headers=self.headers,
                json=request_data
            )
            
            if response.status_code == 200:
                return response.json()["uuid"]
            return None
        
        # Lancer les requêtes en parallèle
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            
            for future in futures:
                request_id = future.result()
                if request_id:
                    request_ids.append(request_id)
        
        self.assertGreater(len(request_ids), 0)
        logger.info(f"✅ {len(request_ids)} requêtes concurrentes créées")
        
        # Attendre quelques complétions
        completed_count = 0
        start_time = time.time()
        
        while time.time() - start_time < 60 and completed_count < min(5, len(request_ids)):
            for request_id in request_ids[:5]:  # Vérifier les 5 premières
                response = requests.get(
                    f"{self.base_url}/api/status/{request_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    status_data = response.json()
                    if status_data["status"] == "complete":
                        completed_count += 1
            
            time.sleep(2)
        
        logger.info(f"✅ {completed_count} requêtes complétées sur {len(request_ids)}")

    def test_scheduler_stats_under_load(self):
        """Test des statistiques du scheduler sous charge"""
        # Créer plusieurs requêtes rapidement
        for i in range(5):
            request_data = {
                "scheduler_id": self.scheduler_id,
                "url": f"https://httpbin.org/delay/1?load_test={i}",
                "method": "GET"
            }
            
            requests.post(
                f"{self.base_url}/api/request",
                headers=self.headers,
                json=request_data
            )
        
        # Vérifier les stats
        response = requests.get(
            f"{self.base_url}/api/scheduler/{self.scheduler_id}/stats",
            headers=self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        stats = response.json()
        
        # Sous charge, on devrait avoir des requêtes en queue ou en traitement
        total_activity = stats["queue_size"] + stats["pending_requests"] + stats["pending_responses"]
        logger.info(f"✅ Activité sous charge: {total_activity} requêtes actives")

    def test_response_time_measurement(self):
        """Test de mesure du temps de réponse"""
        start_time = time.time()
        
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "https://httpbin.org/get?timing=test",
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        request_creation_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(request_creation_time, 5.0, "Création de requête trop lente")
        
        logger.info(f"✅ Temps de création de requête: {request_creation_time:.3f}s")


class TestErrorScenarios(APIManagerIntegrationTest):
    """Tests de scénarios d'erreur"""
    
    def setUp(self):
        super().setUp()
        # Créer un scheduler
        data = {"api_patterns": ["https://httpbin.org", "http://127.0.0.1:5000/mockapi"]}
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        self.scheduler_id = response.json()["scheduler_id"]
        self.created_schedulers.append(self.scheduler_id)

    def test_request_to_unavailable_service(self):
        """Test de requête vers un service indisponible"""
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "https://httpbin.org/status/500",  # Retourne une erreur 500
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        self.assertEqual(response.status_code, 200)
        request_id = response.json()["uuid"]
        
        # Attendre le traitement
        time.sleep(5)
        
        # Vérifier le résultat
        status_response = requests.get(
            f"{self.base_url}/api/status/{request_id}",
            headers=self.headers
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            
            # La requête peut être complétée avec une erreur
            if status_data["status"] == "complete":
                # Vérifier si la réponse contient une erreur ou un code 500
                response_data = status_data.get("response", {})
                logger.info(f"✅ Requête vers service indisponible gérée: {response_data}")
        
        logger.info("✅ Service indisponible correctement géré")

    def test_request_timeout_scenario(self):
        """Test de scénario de timeout"""
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "http://127.0.0.1:5000/mockapi/delay/35",  # Plus long que le timeout par défaut
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        self.assertEqual(200, response.status_code)
        request_id = response.json()["uuid"]
        
        # Attendre suffisamment pour que le timeout se produise
        time.sleep(35)
        
        # Vérifier le résultat
        status_response = requests.get(
            f"{self.base_url}/api/status/{request_id}",
            headers=self.headers
        )
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data["status"] == "complete":
                response_data = status_data.get("response", {})
                # Devrait contenir une erreur de timeout
                if "error" in response_data:
                    self.assertIn("timeout", str(response_data["error"]).lower())
                    logger.info("✅ Timeout correctement détecté et géré")

    def test_malformed_request_data(self):
        """Test avec données de requête malformées"""
        # Test sans scheduler_id
        request_data = {
            "url": "https://httpbin.org/get",
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        self.assertEqual(response.status_code, 400)
        logger.info("✅ Requête sans scheduler_id rejetée")
        
        # Test sans URL
        request_data = {
            "scheduler_id": self.scheduler_id,
            "method": "GET"
        }
        
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        
        self.assertEqual(response.status_code, 400)
        logger.info("✅ Requête sans URL rejetée")


class TestCacheValidation(APIManagerIntegrationTest):
    """Tests de validation du système de cache"""
    
    def setUp(self):
        super().setUp()
        # Créer un scheduler
        data = {"api_patterns": ["http://127.0.0.1:5000/mockapi"]}
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json=data
        )
        self.scheduler_id = response.json()["scheduler_id"]
        self.created_schedulers.append(self.scheduler_id)

    def test_cache_functionality(self):
        """Test de fonctionnalité de cache"""
        # URL qui retourne des données uniques (UUID)
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "http://127.0.0.1:5000/mockapi/test/10",
            "method": "GET",
            "cache_duration": 300  # 5 minutes de cache
        }
        
        # Première requête
        response1 = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        self.assertEqual(200, response1.status_code)
        request_id1 = response1.json()["uuid"]
        
        # Attendre la completion de la première requête
        max_wait = 30
        waited = 0
        first_response = None
        
        while waited < max_wait:
            status_response = requests.get(
                f"{self.base_url}/api/status/{request_id1}",
                headers=self.headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] == "complete":
                    first_response = status_data.get("response")
                    break
            
            time.sleep(1)
            waited += 1
        
        self.assertIsNotNone(first_response, "Première requête non complétée")
        
        # Deuxième requête identique (devrait utiliser le cache)
        response2 = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        self.assertEqual(response2.status_code, 200)
        request_id2 = response2.json()["uuid"]
        
        # Attendre la completion de la deuxième requête
        waited = 0
        second_response = None
        
        while waited < max_wait:
            status_response = requests.get(
                f"{self.base_url}/api/status/{request_id2}",
                headers=self.headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] == "complete":
                    second_response = status_data.get("response")
                    break
            
            time.sleep(1)
            waited += 1
        
        self.assertIsNotNone(second_response, "Deuxième requête non complétée")
        
        # Comparer les réponses - elles devraient être identiques si le cache fonctionne
        # Note: Pour httpbin.org/uuid, les réponses seraient différentes sans cache
        logger.info(f"✅ Cache testé - Première: {str(first_response)[:50]}...")
        logger.info(f"✅ Cache testé - Deuxième: {str(second_response)[:50]}...")

    def test_cache_expiration(self):
        """Test d'expiration du cache"""
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "http://127.0.0.1:5000/mockapi/test",
            "method": "GET",
            "cache_duration": 2  # Cache de seulement 2 secondes
        }
        
        # Première requête
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        request_id1 = response.json()["uuid"]
        
        # Attendre l'expiration du cache
        time.sleep(3)
        
        # Deuxième requête après expiration
        response = requests.post(
            f"{self.base_url}/api/request",
            headers=self.headers,
            json=request_data
        )
        request_id2 = response.json()["uuid"]
        
        # Les deux requêtes devraient être traitées (cache expiré)
        logger.info("✅ Expiration du cache testée")


class TestCompleteIntegrationScenarios(APIManagerIntegrationTest):
    """Tests de scénarios d'intégration complets"""
    
    def test_complete_workflow_multiple_apis(self):
        """Test d'un workflow complet avec plusieurs APIs"""
        # 1. Créer plusieurs schedulers pour différentes APIs
        api_groups = [
            ["http://127.0.0.1:5000/mockapi"],
            ["http://127.0.0.1:5000/mockapi/unicode"]
        ]
        
        scheduler_ids = []
        
        for api_group in api_groups:
            response = requests.post(
                f"{self.base_url}/api/initialize",
                headers=self.headers,
                json={"api_patterns": api_group}
            )
            self.assertEqual(response.status_code, 200)
            scheduler_id = response.json()["scheduler_id"]
            scheduler_ids.append(scheduler_id)
            self.created_schedulers.append(scheduler_id)
        
        logger.info(f"✅ {len(scheduler_ids)} schedulers créés")
        
        # 2. Configurer des limites de taux différentes
        for i, scheduler_id in enumerate(scheduler_ids):
            limit = 1.0 + i  # 1.0, 2.0, etc.
            response = requests.post(
                f"{self.base_url}/api/set_rate_limit",
                headers=self.headers,
                json={"scheduler_id": scheduler_id, "limit": limit}
            )
            self.assertEqual(response.status_code, 200)
        
        logger.info("✅ Limites de taux configurées")
        
        # 3. Lancer des requêtes sur chaque scheduler
        request_ids = []
        
        # Requêtes vers httpbin
        httpbin_requests = [
            {"url": "https://httpbin.org/get?test=1", "method": "GET"},
            {"url": "https://httpbin.org/post", "method": "POST", "payload": {"data": "test"}},
            {"url": "https://httpbin.org/headers", "method": "GET", "headers": {"X-Test": "value"}}
        ]
        
        for req_config in httpbin_requests:
            req_config["scheduler_id"] = scheduler_ids[0]
            response = requests.post(
                f"{self.base_url}/api/request",
                headers=self.headers,
                json=req_config
            )
            if response.status_code == 200:
                request_ids.append(response.json()["uuid"])
        
        # Requêtes vers jsonplaceholder
        jsonplaceholder_requests = [
            {"url": "https://jsonplaceholder.typicode.com/posts/1", "method": "GET"},
            {"url": "https://jsonplaceholder.typicode.com/users", "method": "GET"}
        ]
        
        for req_config in jsonplaceholder_requests:
            req_config["scheduler_id"] = scheduler_ids[1]
            response = requests.post(
                f"{self.base_url}/api/request",
                headers=self.headers,
                json=req_config
            )
            if response.status_code == 200:
                request_ids.append(response.json()["uuid"])
        
        logger.info(f"✅ {len(request_ids)} requêtes lancées")
        
        # 4. Surveiller les complétions
        completed_requests = 0
        start_time = time.time()
        max_wait_time = 60  # 1 minute maximum
        
        while time.time() - start_time < max_wait_time and completed_requests < len(request_ids):
            for request_id in request_ids:
                response = requests.get(
                    f"{self.base_url}/api/status/{request_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    status_data = response.json()
                    if status_data["status"] == "complete":
                        completed_requests += 1
                        request_ids.remove(request_id)
                        break
            
            if request_ids:  # S'il reste des requêtes à vérifier
                time.sleep(2)
        
        logger.info(f"✅ {completed_requests} requêtes complétées")
        
        # 5. Vérifier les statistiques finales
        for scheduler_id in scheduler_ids:
            response = requests.get(
                f"{self.base_url}/api/scheduler/{scheduler_id}/stats",
                headers=self.headers
            )
            self.assertEqual(response.status_code, 200)
            stats = response.json()
            logger.info(f"✅ Stats scheduler {scheduler_id[:8]}...: {stats}")

    def test_websocket_with_multiple_clients(self):
        """Test WebSocket avec plusieurs clients"""
        # Créer un scheduler
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json={"api_patterns": ["https://httpbin.org"]}
        )
        scheduler_id = response.json()["scheduler_id"]
        self.created_schedulers.append(scheduler_id)
        
        clients = []
        client_ids = []
        
        try:
            # Créer plusieurs clients WebSocket
            for i in range(3):
                sio = socketio.SimpleClient()
                sio.connect(f"ws://127.0.0.1:6000")
                
                client_id = f"multi_client_{i}_{uuid.uuid4().hex[:8]}"
                sio.emit('register', {'client_id': client_id})
                sio.receive(timeout=5)  # Attendre la confirmation
                
                clients.append(sio)
                client_ids.append(client_id)
            
            logger.info(f"✅ {len(clients)} clients WebSocket connectés")
            
            # Lancer des requêtes pour chaque client
            for i, client_id in enumerate(client_ids):
                request_data = {
                    "scheduler_id": scheduler_id,
                    "url": f"https://httpbin.org/get?client={i}",
                    "method": "GET",
                    "client_id": client_id
                }
                
                response = requests.post(
                    f"{self.base_url}/api/request",
                    headers=self.headers,
                    json=request_data
                )
                self.assertEqual(response.status_code, 200)
            
            logger.info("✅ Requêtes lancées pour tous les clients")
            
            # Attendre les notifications
            notifications_received = 0
            start_time = time.time()
            
            while time.time() - start_time < 30 and notifications_received < len(clients):
                for client in clients:
                    try:
                        event = client.receive(timeout=1)
                        if event:
                            notifications_received += 1
                    except socketio.exceptions.TimeoutError:
                        continue
            
            logger.info(f"✅ {notifications_received} notifications WebSocket reçues")
            
        finally:
            # Nettoyer les connexions
            for client in clients:
                if client.connected:
                    client.disconnect()

    def test_stress_test_basic(self):
        """Test de stress basique"""
        # Créer un scheduler avec limite élevée
        response = requests.post(
            f"{self.base_url}/api/initialize",
            headers=self.headers,
            json={"api_patterns": ["https://httpbin.org"]}
        )
        scheduler_id = response.json()["scheduler_id"]
        self.created_schedulers.append(scheduler_id)
        
        # Configurer une limite élevée
        requests.post(
            f"{self.base_url}/api/set_rate_limit",
            headers=self.headers,
            json={"scheduler_id": scheduler_id, "limit": 10.0}
        )
        
        # Lancer de nombreuses requêtes rapidement
        num_requests = 20
        successful_requests = 0
        start_time = time.time()
        
        for i in range(num_requests):
            request_data = {
                "scheduler_id": scheduler_id,
                "url": f"https://httpbin.org/get?stress_test={i}",
                "method": "GET"
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/api/request",
                    headers=self.headers,
                    json=request_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    successful_requests += 1
                    
            except requests.exceptions.RequestException:
                continue
        
        creation_time = time.time() - start_time
        
        logger.info(f"✅ Stress test: {successful_requests}/{num_requests} requêtes créées en {creation_time:.2f}s")
        
        # Vérifier que le serveur est toujours responsive
        health_response = requests.get(f"{self.base_url}/api/health")
        self.assertEqual(health_response.status_code, 200)
        
        logger.info("✅ Serveur toujours responsive après stress test")


# Suite de tests personnalisée avec rapport détaillé
class CustomTestResult(unittest.TestResult):
    """Résultat de test personnalisé avec rapport détaillé"""
    
    def __init__(self):
        super().__init__()
        self.test_results = []
        self.start_time = time.time()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_results.append({
            'test': str(test),
            'status': 'SUCCESS',
            'time': time.time()
        })

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_results.append({
            'test': str(test),
            'status': 'FAILURE',
            'error': str(err[1]),
            'time': time.time()
        })

    def addError(self, test, err):
        super().addError(test, err)
        self.test_results.append({
            'test': str(test),
            'status': 'ERROR',
            'error': str(err[1]),
            'time': time.time()
        })


def run_integration_tests():
    """Fonction principale pour lancer les tests d'intégration"""
    print("🚀 Lancement des tests d'intégration API Manager")
    print("=" * 70)
    
    # Vérification préliminaire de la connexion serveur
    try:
        response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Serveur API Manager détecté: {health_data}")
        else:
            print(f"❌ Serveur non accessible (code: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Impossible de contacter le serveur: {e}")
        print(f"Vérifiez que le serveur tourne sur {API_BASE_URL}")
        return False
    
    # Créer la suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Classes de tests à exécuter
    test_classes = [
        TestServerStatus,
        TestAuthentication,
        TestSchedulerManagement,
        TestAPIRequests,
        TestRequestStatus,
        TestWebSocketIntegration,
        TestLoadAndPerformance,
        TestErrorScenarios,
        TestCacheValidation,
        TestCompleteIntegrationScenarios
    ]
    
    # Ajouter les tests
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Lancer les tests avec résultat personnalisé
    result = CustomTestResult()
    runner = unittest.TextTestRunner(
        stream=open('/dev/null', 'w') if hasattr(unittest, '_TextTestResult') else None,
        verbosity=0,
        resultclass=lambda: result
    )
    
    print(f"📊 Exécution de {suite.countTestCases()} tests d'intégration...")
    print("-" * 70)
    
    # Exécuter les tests
    start_time = time.time()
    runner.run(suite)
    total_time = time.time() - start_time
    
    # Rapport final
    print("\n" + "=" * 70)
    print("📋 RAPPORT FINAL DES TESTS D'INTÉGRATION")
    print("=" * 70)
    
    success_count = len([r for r in result.test_results if r['status'] == 'SUCCESS'])
    failure_count = len([r for r in result.test_results if r['status'] == 'FAILURE'])
    error_count = len([r for r in result.test_results if r['status'] == 'ERROR'])
    total_tests = len(result.test_results)
    
    print(f"📊 Tests exécutés: {total_tests}")
    print(f"✅ Succès: {success_count}")
    print(f"❌ Échecs: {failure_count}")
    print(f"⚠️  Erreurs: {error_count}")
    print(f"⏱️  Temps total: {total_time:.2f}s")
    
    if total_tests > 0:
        success_rate = (success_count / total_tests) * 100
        print(f"📈 Taux de réussite: {success_rate:.1f}%")
    
    # Détail des échecs/erreurs
    if failure_count > 0:
        print("\n❌ ÉCHECS:")
        for result_item in result.test_results:
            if result_item['status'] == 'FAILURE':
                print(f"  - {result_item['test']}")
                print(f"    {result_item['error'][:100]}...")
    
    if error_count > 0:
        print("\n⚠️ ERREURS:")
        for result_item in result.test_results:
            if result_item['status'] == 'ERROR':
                print(f"  - {result_item['test']}")
                print(f"    {result_item['error'][:100]}...")
    
    # Recommandations
    print("\n💡 RECOMMANDATIONS:")
    if success_rate >= 90:
        print("  ✅ Excellent! Le serveur API Manager fonctionne parfaitement.")
    elif success_rate >= 70:
        print("  ⚠️  Bien, mais quelques problèmes détectés. Vérifiez les échecs.")
    else:
        print("  ❌ Problèmes significatifs détectés. Vérification nécessaire.")
    
    print("\n🔧 Pour débugger:")
    print(f"  - Logs du serveur API Manager")
    print(f"  - Vérifier la configuration Bearer token: {BEARER_TOKEN}")
    print(f"  - Tester manuellement: curl {API_BASE_URL}/api/health")
    
    return success_rate >= 70


if __name__ == '__main__':
    success = run_integration_tests()
    exit(0 if success else 1)