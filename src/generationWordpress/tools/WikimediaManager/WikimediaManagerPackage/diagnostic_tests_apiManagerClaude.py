#!/usr/bin/env python3
"""
Script de diagnostic pour identifier les problèmes dans l'API Manager
Problème: request_id créé avec succès mais introuvable lors de la vérification du statut
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
API_BASE_URL = "http://127.0.0.1:6000"
BEARER_TOKEN = "5a07f30b-892f-4db1-a094-7a4bf12a2fdc"  # ⚠️ REMPLACEZ par votre vrai token
HEADERS = {"Authorization": f"Bearer {BEARER_TOKEN}"}


class APIManagerDiagnostic:
    """Classe de diagnostic pour l'API Manager"""

    def __init__(self):
        self.base_url = API_BASE_URL
        self.headers = HEADERS
        self.scheduler_id = None
        self.debug = True

    def log(self, message, level="INFO"):
        """Log avec timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {level}: {message}")

    def test_basic_connectivity(self):
        """Test 1: Connectivité de base"""
        self.log("=== TEST 1: CONNECTIVITÉ DE BASE ===")

        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            self.log(f"Page d'accueil: {response.status_code}")

            # Test health endpoint
            try:
                health_response = requests.get(f"{self.base_url}/api/health", timeout=5)
                self.log(f"Health endpoint: {health_response.status_code}")
                if health_response.status_code == 200:
                    self.log(f"Health data: {health_response.json()}")
            except:
                self.log("Health endpoint non disponible", "WARNING")

            return response.status_code == 200

        except Exception as e:
            self.log(f"Erreur de connectivité: {e}", "ERROR")
            return False

    def test_authentication(self):
        """Test 2: Authentification"""
        self.log("=== TEST 2: AUTHENTIFICATION ===")

        # Test sans token
        response_no_auth = requests.post(f"{self.base_url}/api/initialize",
                                         json={"api_patterns": ["https://httpbin.org"]})
        self.log(f"Sans token: {response_no_auth.status_code} (attendu: 401)")

        # Test avec token
        response_with_auth = requests.post(f"{self.base_url}/api/initialize",
                                           json={"api_patterns": ["https://httpbin.org"]},
                                           headers=self.headers)
        self.log(f"Avec token: {response_with_auth.status_code}")

        if response_with_auth.status_code == 401:
            self.log("❌ PROBLÈME: Token d'authentification invalide ou mal configuré", "ERROR")
            self.log("Vérifiez que TEST_BEARER_TOKEN correspond à config['admin']['Bearer']", "ERROR")
            return False
        elif response_with_auth.status_code == 200:
            self.log("✅ Authentification OK")
            return True
        else:
            self.log(f"Réponse inattendue: {response_with_auth.text}", "WARNING")
            return False

    def create_scheduler(self):
        """Test 3: Création de scheduler avec diagnostic détaillé"""
        self.log("=== TEST 3: CRÉATION DE SCHEDULER ===")

        init_data = {"api_patterns": ["https://httpbin.org"]}

        try:
            response = requests.post(f"{self.base_url}/api/initialize",
                                     json=init_data,
                                     headers=self.headers,
                                     timeout=10)

            self.log(f"Status code: {response.status_code}")
            self.log(f"Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                data = response.json()
                self.scheduler_id = data["scheduler_id"]
                self.log(f"✅ Scheduler créé: {self.scheduler_id}")

                # Vérifier immédiatement via openstatus
                self.check_scheduler_existence()
                return True

            else:
                self.log(f"❌ Échec création: {response.text}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Exception lors de la création: {e}", "ERROR")
            return False

    def check_scheduler_existence(self):
        """Vérifier que le scheduler existe dans openstatus"""
        self.log("=== VÉRIFICATION EXISTENCE SCHEDULER ===")

        try:
            response = requests.get(f"{self.base_url}/api/openstatus", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log(f"Schedulers actifs: {data.get('schedulers_count', 'N/A')}")

                # Chercher notre scheduler
                schedulers = data.get('schedulers', [])
                found = False
                for scheduler in schedulers:
                    if scheduler.get('scheduler_id')== self.scheduler_id:
                        found = True
                        self.log(f"✅ Scheduler trouvé dans openstatus")
                        self.log(f"   Stats: {scheduler.get('stats', {})}")
                        break

                if not found:
                    self.log(f"❌ Scheduler {self.scheduler_id} NON trouvé dans openstatus", "ERROR")

            else:
                self.log("⚠️ Openstatus non disponible", "WARNING")

        except Exception as e:
            self.log(f"Erreur openstatus: {e}", "WARNING")

    def diagnose_request_lifecycle(self):
        """Test 4: Diagnostic complet du cycle de vie d'une requête"""
        self.log("=== TEST 4: CYCLE DE VIE D'UNE REQUÊTE ===")

        if not self.scheduler_id:
            self.log("❌ Pas de scheduler disponible", "ERROR")
            return False

        # ÉTAPE 1: Créer la requête
        request_data = {
            "scheduler_id": self.scheduler_id,
            "url": "https://httpbin.org/get?diagnostic=test",
            "method": "GET"
        }

        self.log("Soumission de la requête...")
        self.log(f"Payload: {json.dumps(request_data, indent=2)}")

        try:
            start_time = time.time()

            response = requests.post(f"{self.base_url}/api/request",
                                     json=request_data,
                                     headers=self.headers,
                                     timeout=10)

            creation_time = time.time() - start_time

            self.log(f"Temps de création: {creation_time:.3f}s")
            self.log(f"Status création: {response.status_code}")

            if response.status_code != 200:
                self.log(f"❌ Échec création requête: {response.text}", "ERROR")
                return False

            response_data = response.json()
            request_id = response_data["uuid"]
            estimated_delay = response_data.get("estimated_delay", 0)

            self.log(f"✅ Requête créée: {request_id}")
            self.log(f"Délai estimé: {estimated_delay}s")

            # ÉTAPE 2: Vérification immédiate du statut
            self.log("\n--- VÉRIFICATION IMMÉDIATE ---")

            immediate_check_time = time.time()
            status_response = requests.get(f"{self.base_url}/api/status/{request_id}",
                                           headers=self.headers,
                                           timeout=5)

            immediate_check_duration = time.time() - immediate_check_time

            self.log(f"Status immédiat: {status_response.status_code} (en {immediate_check_duration:.3f}s)")

            if status_response.status_code == 404:
                self.log("❌ PROBLÈME IDENTIFIÉ: Request_id non trouvé immédiatement après création", "ERROR")
                self.log("Cela indique un problème de synchronisation dans l'API Manager", "ERROR")

                # Diagnostic approfondi
                self.detailed_request_diagnosis(request_id)
                return False

            elif status_response.status_code == 200:
                status_data = status_response.json()
                self.log(f"✅ Statut trouvé: {status_data['status']}")

                # ÉTAPE 3: Monitoring du traitement
                return self.monitor_request_processing(request_id, estimated_delay)

            else:
                self.log(f"❌ Status code inattendu: {status_response.status_code}", "ERROR")
                self.log(f"Response: {status_response.text}")
                return False

        except Exception as e:
            self.log(f"❌ Exception dans le cycle de vie: {e}", "ERROR")
            return False

    def detailed_request_diagnosis(self, request_id):
        """Diagnostic détaillé quand une requête n'est pas trouvée"""
        self.log("=== DIAGNOSTIC DÉTAILLÉ DE LA REQUÊTE ===")

        # Vérifier openstatus pour voir les requêtes en cours
        try:
            response = requests.get(f"{self.base_url}/api/openstatus", timeout=5)
            if response.status_code == 200:
                data = response.json()

                self.log("État des schedulers:")
                schedulers = data.get('schedulers', [])

                for scheduler in schedulers:
                    scheduler_id = scheduler.get('scheduler_id', 'N/A')
                    stats = scheduler.get('stats', {})
                    pending_requests = scheduler.get('pending_requests', [])

                    self.log(f"  Scheduler: {scheduler_id}")
                    self.log(f"    Queue size: {stats.get('queue_size', 'N/A')}")
                    self.log(f"    Pending requests: {stats.get('pending_requests', 'N/A')}")
                    self.log(f"    Pending responses: {stats.get('pending_responses', 'N/A')}")

                    # Chercher notre request_id
                    if request_id in pending_requests:
                        self.log(f"    ✅ Notre request_id trouvé dans pending_requests")
                    else:
                        self.log(f"    ❌ Notre request_id PAS dans pending_requests")
                        self.log(f"    Pending IDs: {pending_requests[:5]}...")  # Montrer les premiers

        except Exception as e:
            self.log(f"Erreur diagnostic détaillé: {e}", "ERROR")

        # Réessayer plusieurs fois avec des délais
        self.log("\n--- TENTATIVES RÉPÉTÉES ---")
        for attempt in range(5):
            time.sleep(0.2 * (attempt + 1))  # Délais croissants

            try:
                status_response = requests.get(f"{self.base_url}/api/status/{request_id}",
                                               headers=self.headers,
                                               timeout=3)

                self.log(f"Tentative {attempt + 1}: Status {status_response.status_code}")

                if status_response.status_code == 200:
                    self.log("✅ Requête finalement trouvée!")
                    return True

            except Exception as e:
                self.log(f"Tentative {attempt + 1} échouée: {e}")

        return False

    def monitor_request_processing(self, request_id, estimated_delay):
        """Monitor le traitement d'une requête"""
        self.log("=== MONITORING DU TRAITEMENT ===")

        start_monitoring = time.time()
        max_wait = max(estimated_delay * 2, 30)  # Au moins 30s

        self.log(f"Monitoring pendant {max_wait}s max...")

        last_status = None
        status_changes = 0

        while time.time() - start_monitoring < max_wait:
            try:
                response = requests.get(f"{self.base_url}/api/status/{request_id}",
                                        headers=self.headers,
                                        timeout=5)

                if response.status_code == 200:
                    status_data = response.json()
                    current_status = status_data["status"]

                    if current_status != last_status:
                        elapsed = time.time() - start_monitoring
                        self.log(f"[{elapsed:.1f}s] Statut: {current_status}")
                        last_status = current_status
                        status_changes += 1

                    if current_status == "complete":
                        response_data = status_data.get("response", {})
                        self.log(f"✅ Requête terminée avec succès")

                        if isinstance(response_data, dict) and "url" in response_data:
                            self.log("✅ Réponse valide de httpbin reçue")

                        return True

                elif response.status_code == 404:
                    self.log("❌ Requête disparue pendant le traitement!", "ERROR")
                    return False

                else:
                    self.log(f"Status code inattendu: {response.status_code}", "WARNING")

            except Exception as e:
                self.log(f"Erreur monitoring: {e}", "WARNING")

            time.sleep(1)

        self.log(f"⏰ Timeout après {max_wait}s")
        self.log(f"Changements de statut observés: {status_changes}")
        return False

    def test_multiple_requests(self):
        """Test 5: Comportement avec plusieurs requêtes"""
        self.log("=== TEST 5: REQUÊTES MULTIPLES ===")

        if not self.scheduler_id:
            return False

        request_ids = []

        # Créer 3 requêtes rapidement
        for i in range(3):
            request_data = {
                "scheduler_id": self.scheduler_id,
                "url": f"https://httpbin.org/get?multi_test={i}",
                "method": "GET"
            }

            try:
                response = requests.post(f"{self.base_url}/api/request",
                                         json=request_data,
                                         headers=self.headers,
                                         timeout=5)

                if response.status_code == 200:
                    req_id = response.json()["uuid"]
                    request_ids.append(req_id)
                    self.log(f"Requête {i + 1} créée: {req_id[:8]}...")

            except Exception as e:
                self.log(f"Erreur requête {i + 1}: {e}", "ERROR")

        # Vérifier immédiatement toutes les requêtes
        self.log("\nVérification immédiate de toutes les requêtes:")

        found_count = 0
        for i, req_id in enumerate(request_ids):
            try:
                response = requests.get(f"{self.base_url}/api/status/{req_id}",
                                        headers=self.headers,
                                        timeout=3)

                if response.status_code == 200:
                    found_count += 1
                    self.log(f"  Requête {i + 1}: ✅ trouvée")
                elif response.status_code == 404:
                    self.log(f"  Requête {i + 1}: ❌ non trouvée")
                else:
                    self.log(f"  Requête {i + 1}: ? status {response.status_code}")

            except Exception as e:
                self.log(f"  Requête {i + 1}: Erreur {e}")

        success_rate = found_count / len(request_ids) * 100 if request_ids else 0
        self.log(f"\nTaux de succès immédiat: {success_rate:.1f}% ({found_count}/{len(request_ids)})")

        return success_rate > 80

    def test_race_conditions(self):
        """Test 6: Conditions de course potentielles"""
        self.log("=== TEST 6: CONDITIONS DE COURSE ===")

        if not self.scheduler_id:
            return False

        import threading
        import queue

        results = queue.Queue()

        def create_and_check_request(thread_id):
            """Créer une requête et vérifier immédiatement son statut"""
            try:
                # Créer requête
                request_data = {
                    "scheduler_id": self.scheduler_id,
                    "url": f"https://httpbin.org/get?race_test={thread_id}",
                    "method": "GET"
                }

                start_time = time.time()
                response = requests.post(f"{self.base_url}/api/request",
                                         json=request_data,
                                         headers=self.headers,
                                         timeout=5)

                if response.status_code == 200:
                    request_id = response.json()["uuid"]

                    # Vérifier immédiatement
                    check_response = requests.get(f"{self.base_url}/api/status/{request_id}",
                                                  headers=self.headers,
                                                  timeout=3)

                    elapsed = time.time() - start_time

                    result = {
                        'thread_id': thread_id,
                        'request_created': True,
                        'request_id': request_id,
                        'status_found': check_response.status_code == 200,
                        'status_code': check_response.status_code,
                        'elapsed_time': elapsed
                    }
                else:
                    result = {
                        'thread_id': thread_id,
                        'request_created': False,
                        'error': f"Status {response.status_code}"
                    }

                results.put(result)

            except Exception as e:
                results.put({
                    'thread_id': thread_id,
                    'request_created': False,
                    'error': str(e)
                })

        # Lancer 5 threads simultanément
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_check_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Attendre tous les threads
        for thread in threads:
            thread.join(timeout=15)

        # Analyser les résultats
        all_results = []
        while not results.empty():
            all_results.append(results.get())

        self.log(f"\nRésultats des tests de concurrence:")

        created_count = sum(1 for r in all_results if r.get('request_created', False))
        found_count = sum(1 for r in all_results if r.get('status_found', False))

        for result in all_results:
            thread_id = result['thread_id']
            if result.get('request_created'):
                status = "✅" if result.get('status_found') else "❌"
                elapsed = result.get('elapsed_time', 0)
                self.log(f"  Thread {thread_id}: {status} ({elapsed:.3f}s)")
            else:
                error = result.get('error', 'Unknown error')
                self.log(f"  Thread {thread_id}: ❌ {error}")

        self.log(f"\nRésumé concurrence:")
        self.log(f"  Requêtes créées: {created_count}/5")
        self.log(f"  Statuts trouvés: {found_count}/{created_count}")

        if created_count > 0:
            success_rate = found_count / created_count * 100
            self.log(f"  Taux de succès: {success_rate:.1f}%")

            if success_rate < 80:
                self.log("❌ PROBLÈME DÉTECTÉ: Faible taux de succès en concurrence", "ERROR")
                self.log("Cela suggère des problèmes de synchronisation/race conditions", "ERROR")
                return False

        return True

    def run_full_diagnostic(self):
        """Lancer tous les diagnostics"""
        self.log("🔍 DIAGNOSTIC COMPLET DE L'API MANAGER")
        self.log("=" * 50)

        results = {}

        # Test 1: Connectivité
        results['connectivity'] = self.test_basic_connectivity()

        if not results['connectivity']:
            self.log("❌ ARRÊT: Problème de connectivité de base", "ERROR")
            return False

        # Test 2: Authentification
        results['authentication'] = self.test_authentication()

        if not results['authentication']:
            self.log("❌ ARRÊT: Problème d'authentification", "ERROR")
            return False

        # Test 3: Création scheduler
        results['scheduler_creation'] = self.create_scheduler()

        if not results['scheduler_creation']:
            self.log("❌ ARRÊT: Impossible de créer un scheduler", "ERROR")
            return False

        # Test 4: Cycle de vie requête
        results['request_lifecycle'] = self.diagnose_request_lifecycle()

        # Test 5: Requêtes multiples
        results['multiple_requests'] = self.test_multiple_requests()

        # Test 6: Race conditions
        results['race_conditions'] = self.test_race_conditions()

        # Résumé final
        self.log("\n" + "=" * 50)
        self.log("📊 RÉSUMÉ DU DIAGNOSTIC")
        self.log("=" * 50)

        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            self.log(f"{test_name.replace('_', ' ').title()}: {status}")

        failed_tests = [name for name, success in results.items() if not success]

        if failed_tests:
            self.log(f"\n❌ {len(failed_tests)} test(s) échoué(s): {', '.join(failed_tests)}", "ERROR")
            self.log("\n🔧 RECOMMANDATIONS:", "INFO")

            if 'request_lifecycle' in failed_tests:
                self.log("• Problème de synchronisation dans l'API Manager")
                self.log("• Vérifiez la gestion des threads et des queues")
                self.log("• Le request_dict n'est peut-être pas mis à jour correctement")

            if 'race_conditions' in failed_tests:
                self.log("• Problèmes de concurrence détectés")
                self.log("• Ajoutez plus de verrous (locks) dans le code")
                self.log("• Vérifiez la thread safety")

        else:
            self.log("\n✅ TOUS LES TESTS SONT PASSÉS!", "INFO")

        return len(failed_tests) == 0


def main():
    """Fonction principale"""
    print("🔍 DIAGNOSTIC API MANAGER - Problème Request ID non trouvé")
    print("=" * 60)

    # Instructions
    print("\n📋 AVANT DE COMMENCER:")
    print("1. Assurez-vous que votre API Manager tourne sur localhost:6000")
    print("2. Modifiez BEARER_TOKEN dans ce script pour correspondre à votre configuration")
    print("3. Ce script va faire des vraies requêtes vers httpbin.org")
    print("\n" + "=" * 60)

    diagnostic = APIManagerDiagnostic()

    try:
        success = diagnostic.run_full_diagnostic()

        if success:
            print("\n🎉 Diagnostic terminé avec succès!")
            sys.exit(0)
        else:
            print("\n❌ Problèmes détectés dans l'API Manager")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⏹️  Diagnostic interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()