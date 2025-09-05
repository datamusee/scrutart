# tests/test_monitoring.py
import unittest
import time
import concurrent.futures
from src.generationWordpress.tools.WikimediaManager.WikimediaManagerPackage.WikimediaAccess import WikimediaAccess
from src.generationWordpress.tools.WikimediaManager.WikimediaManagerPackage.metrics import metrics_collector


class TestMonitoring(unittest.TestCase):

    def setUp(self):
        """Reset des métriques avant chaque test"""
        metrics_collector.operations.clear()
        metrics_collector.start_time = time.time()

    def test_metrics_collection(self):
        """Test que les métriques sont bien collectées"""
        with WikimediaAccess("Q762") as wma:
            # Exécuter quelques opérations
            occupations = wma.getOccupations()
            types = wma.getTypes()

            # Vérifier les métriques
            metrics = wma.get_instance_metrics()

            self.assertIn('get_occupations', metrics['metrics']['operations'])
            self.assertIn('get_types', metrics['metrics']['operations'])

            # Vérifier qu'on a des données
            ops_metrics = metrics['metrics']['operations']['get_occupations']
            self.assertGreater(ops_metrics['total_calls'], 0)
            self.assertGreater(ops_metrics['successful_calls'], 0)

    def test_health_check(self):
        """Test du health check"""
        with WikimediaAccess("Q762") as wma:
            health = wma.get_health_status()

            self.assertEqual(health['status'], 'healthy')
            self.assertIn('response_time_ms', health)
            self.assertTrue(health['test_query_success'])

    def test_load_performance(self):
        """Test de charge basique"""

        def single_operation():
            with WikimediaAccess("Q762") as wma:
                return wma.getOccupations()

        # Exécuter 10 opérations en parallèle
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(single_operation) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        duration = time.time() - start_time

        # Vérifier les résultats
        self.assertEqual(len(results), 10)
        self.assertLess(duration, 30)  # Doit terminer en moins de 30s

        # Vérifier les métriques
        metrics = metrics_collector.get_metrics()
        self.assertGreaterEqual(metrics['operations']['get_occupations']['total_calls'], 10)


if __name__ == "__main__":
    unittest.main()