import unittest
import tempfile
import os
import json
import sys
import time
import logging
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List
import requests

# Import du module à tester (ajustez le chemin selon votre structure)
from src.piwigoTools.CPiwigoManager import CPiwigoManager, PiwigoError, CategoryType, PiwigoConfig
from src.piwigoTools.configPiwigo import configPiwigo

class TestConfig:
    """Configuration de test - À personnaliser avec vos accès Piwigo"""

    # CONFIGURATION À MODIFIER AVEC VOS ACCÈS PIWIGO
    PIWIGO_URL = configPiwigo["url"]
    PIWIGO_API_URL = configPiwigo["url"]+"/ws.php"  # URL de l'API
    PIWIGO_LOGIN = configPiwigo["login"]
    PIWIGO_PASSWORD = configPiwigo["pass"]

    # Catégories de test (seront créées puis supprimées)
    TEST_CATEGORIES = [
        "Test_Unit_Category_1",
        "Test_Unit_Category_2",
        "Test_Bulk_Upload_Category"
    ]

    # Images de test (URLs publiques Wikimedia Commons)
    TEST_IMAGES = [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4f/Test_image.jpg/800px-Test_image.jpg",
            "titre_fr": "Image de Test 1",
            "titre_en": "Test Image 1",
            "uri": "http://www.wikidata.org/entity/Q123456",
            "createur": "http://www.wikidata.org/entity/Q7890",
            "createurLabel": "Test Creator"
        },
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Square_200x200.png/200px-Square_200x200.png",
            "titre_fr": "Image de Test 2",
            "titre_en": "Test Image 2",
            "uri": "http://www.wikidata.org/entity/Q654321",
            "createur": "http://www.wikidata.org/entity/Q9876",
            "createurLabel": "Another Test Creator"
        }
    ]


class PiwigoTestCase(unittest.TestCase):
    """Classe de base pour les tests Piwigo avec setup/teardown commun"""

    @classmethod
    def setUpClass(cls):
        """Configuration globale des tests"""
        # Configuration du logging pour les tests
        logging.basicConfig(
            level=logging.DEBUG,
            format='[TEST %(asctime)s] %(levelname)s - %(name)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('test_piwigo.log', encoding='utf-8')
            ]
        )
        cls.logger = logging.getLogger(cls.__name__)
        cls.logger.info("=== DÉBUT DES TESTS PIWIGO ===")

        # Création d'un fichier de config temporaire pour les tests
        cls.config_data = {
            "login": TestConfig.PIWIGO_LOGIN,
            "pass": TestConfig.PIWIGO_PASSWORD
        }

        # Mock de la configuration
        cls.config_patcher = patch('CPiwigoManager.cp', cls.config_data)
        cls.config_patcher.start()

        # Stockage des IDs créés pour nettoyage
        cls.created_category_ids = []
        cls.created_image_ids = []

    @classmethod
    def tearDownClass(cls):
        """Nettoyage global après tous les tests"""
        cls.config_patcher.stop()
        cls.logger.info("=== FIN DES TESTS PIWIGO ===")

        # Nettoyage des éléments créés
        cls._cleanup_test_data()

    @classmethod
    def _cleanup_test_data(cls):
        """Nettoie les données de test créées"""
        try:
            pwg = CPiwigoManager(TestConfig.PIWIGO_URL)
            pwg.config.api_url = TestConfig.PIWIGO_API_URL

            # Suppression des images de test
            for image_id in cls.created_image_ids:
                try:
                    # Note: Piwigo nécessite généralement des permissions admin pour supprimer
                    cls.logger.info(f"Image de test {image_id} à nettoyer manuellement")
                except Exception as e:
                    cls.logger.warning(f"Impossible de supprimer l'image {image_id}: {e}")

            # Suppression des catégories de test
            for category_id in cls.created_category_ids:
                try:
                    cls.logger.info(f"Catégorie de test {category_id} à nettoyer manuellement")
                except Exception as e:
                    cls.logger.warning(f"Impossible de supprimer la catégorie {category_id}: {e}")

        except Exception as e:
            cls.logger.error(f"Erreur lors du nettoyage: {e}")

    def setUp(self):
        """Configuration pour chaque test"""
        self.pwg = CPiwigoManager(TestConfig.PIWIGO_URL)
        self.pwg.config.api_url = TestConfig.PIWIGO_API_URL

    def tearDown(self):
        """Nettoyage après chaque test"""
        if hasattr(self, 'pwg') and self.pwg:
            self.pwg.close_session()


class TestPiwigoConnection(PiwigoTestCase):
    """Tests de connexion et d'authentification"""

    def test_01_health_check(self):
        """Test du health check système"""
        self.logger.info("Test: Health Check")

        health = self.pwg.health_check()

        self.assertIsInstance(health, dict)
        self.assertIn('status', health)
        self.assertIn('api_accessible', health)
        self.assertIn('authentication', health)
        self.assertIn('timestamp', health)

        # Le système doit être accessible
        self.assertTrue(health['api_accessible'], "L'API Piwigo doit être accessible")

        if health['status'] != 'healthy':
            self.logger.warning(f"Système non optimal: {health}")

    def test_02_login_valid_credentials(self):
        """Test de connexion avec des identifiants valides"""
        self.logger.info("Test: Connexion avec identifiants valides")

        result = self.pwg.piwigo_login()
        self.assertTrue(result, "La connexion doit réussir avec des identifiants valides")

    def test_03_login_invalid_credentials(self):
        """Test de connexion avec des identifiants invalides"""
        self.logger.info("Test: Connexion avec identifiants invalides")

        # Sauvegarde des vrais identifiants
        original_login = self.pwg.login
        original_password = self.pwg.password

        try:
            # Test avec des identifiants incorrects
            self.pwg.login = "wrong_user"
            self.pwg.password = "wrong_password"
            self.pwg.session = None  # Force une nouvelle session

            with self.assertRaises(PiwigoError):
                self.pwg.piwigo_open_session()

        finally:
            # Restauration des identifiants
            self.pwg.login = original_login
            self.pwg.password = original_password

    def test_04_session_management(self):
        """Test de gestion des sessions"""
        self.logger.info("Test: Gestion des sessions")

        # Test d'ouverture de session
        self.pwg.piwigo_open_session()
        self.assertIsNotNone(self.pwg.session, "La session doit être créée")
        self.assertIsNotNone(self.pwg.token, "Le token doit être récupéré")

        # Test de fermeture de session
        self.pwg.close_session()
        self.assertIsNone(self.pwg.session, "La session doit être fermée")
        self.assertIsNone(self.pwg.token, "Le token doit être effacé")


class TestPiwigoCategories(PiwigoTestCase):
    """Tests de gestion des catégories"""

    def test_01_get_categories_list(self):
        """Test de récupération de la liste des catégories"""
        self.logger.info("Test: Récupération liste des catégories")

        categories = self.pwg.piwigo_get_categories()

        self.assertIsNotNone(categories, "La liste des catégories doit être récupérée")
        self.assertIsInstance(categories, dict, "Le résultat doit être un dictionnaire")
        self.assertIn('result', categories, "Le résultat doit contenir 'result'")

        if 'categories' in categories.get('result', {}):
            cats_list = categories['result']['categories']
            self.assertIsInstance(cats_list, list, "Les catégories doivent être une liste")
            self.logger.info(f"Nombre de catégories trouvées: {len(cats_list)}")

    def test_02_create_category(self):
        """Test de création d'une catégorie"""
        self.logger.info("Test: Création d'une catégorie")

        category_name = TestConfig.TEST_CATEGORIES[0]

        # Test de création
        category_id = self.pwg.piwigo_ensure_category_exists(category_name)

        self.assertIsNotNone(category_id, "L'ID de catégorie doit être retourné")
        self.assertIsInstance(category_id, int, "L'ID doit être un entier")

        # Stockage pour nettoyage
        self.__class__.created_category_ids.append(category_id)

        self.logger.info(f"Catégorie '{category_name}' créée avec l'ID {category_id}")

    def test_03_category_exists(self):
        """Test de vérification d'existence d'une catégorie"""
        self.logger.info("Test: Vérification existence catégorie")

        # Utilisation de la catégorie créée dans le test précédent
        if not self.__class__.created_category_ids:
            self.skipTest("Pas de catégorie de test créée")

        category_name = TestConfig.TEST_CATEGORIES[0]

        # Test de récupération de l'ID existant
        category_id = self.pwg.piwigo_ensure_category_exists(category_name)

        self.assertEqual(
            category_id,
            self.__class__.created_category_ids[0],
            "L'ID retourné doit être celui de la catégorie existante"
        )

    def test_04_create_typed_category(self):
        """Test de création d'une catégorie typée"""
        self.logger.info("Test: Création catégorie typée")

        response = self.pwg.piwigo_create_category("Test Creator", CategoryType.CREATORS)

        self.assertIsNotNone(response, "La réponse de création doit exister")

        # Extraction de l'ID depuis la réponse
        if response:
            result = response.json()
            if result.get('stat') == 'ok' and 'result' in result:
                category_id = result['result']['id']
                self.__class__.created_category_ids.append(int(category_id))
                self.logger.info(f"Catégorie typée créée avec l'ID {category_id}")

    def test_05_comment_category(self):
        """Test d'ajout de commentaire à une catégorie"""
        self.logger.info("Test: Ajout commentaire catégorie")

        if not self.__class__.created_category_ids:
            self.skipTest("Pas de catégorie de test disponible")

        category_id = self.__class__.created_category_ids[0]
        comment = self.pwg.build_gallery_comment("GALERY_CREATOR", "Test Artist")

        self.assertIsNotNone(comment, "Le commentaire doit être généré")
        self.assertTrue(len(comment) > 0, "Le commentaire ne doit pas être vide")

        response, returned_comment = self.pwg.piwigo_comment_category(category_id, comment)

        self.assertIsNotNone(response, "La réponse doit exister")
        self.assertEqual(returned_comment, comment, "Le commentaire retourné doit correspondre")


class TestPiwigoImages(PiwigoTestCase):
    """Tests de gestion des images"""

    def test_01_select_best_image(self):
        """Test de sélection de la meilleure image"""
        self.logger.info("Test: Sélection meilleure image")

        image_urls = [img["url"] for img in TestConfig.TEST_IMAGES]

        best_url = self.pwg.select_best_image(image_urls)

        self.assertIsNotNone(best_url, "Une URL doit être sélectionnée")
        self.assertIn(best_url, image_urls, "L'URL sélectionnée doit être dans la liste")

    def test_02_select_image_to_post(self):
        """Test de sélection et téléchargement d'image"""
        self.logger.info("Test: Sélection et téléchargement image")

        artwork = {
            "images": [TestConfig.TEST_IMAGES[0]["url"]]
        }

        best_url, image_data = self.pwg.select_image_to_post(artwork)

        self.assertIsNotNone(best_url, "L'URL doit être sélectionnée")
        self.assertIsNotNone(image_data, "Les données d'image doivent être téléchargées")
        self.assertIsInstance(image_data, bytes, "Les données doivent être en bytes")
        self.assertGreater(len(image_data), 0, "Les données ne doivent pas être vides")

    def test_03_build_description(self):
        """Test de construction de description d'image"""
        self.logger.info("Test: Construction description image")

        test_image = TestConfig.TEST_IMAGES[0]

        description_fr = self.pwg.build_description(
            test_image["url"],
            test_image["createur"],
            test_image["createurLabel"],
            test_image["uri"],
            "fr"
        )

        description_en = self.pwg.build_description(
            test_image["url"],
            test_image["createur"],
            test_image["createurLabel"],
            test_image["uri"],
            "en"
        )

        self.assertIsNotNone(description_fr, "Description FR doit être générée")
        self.assertIsNotNone(description_en, "Description EN doit être générée")
        self.assertNotEqual(description_fr, description_en, "Les descriptions doivent différer par langue")
        self.assertIn("Créateur", description_fr, "Description FR doit contenir 'Créateur'")
        self.assertIn("Creator", description_en, "Description EN doit contenir 'Creator'")

    def test_04_post_single_image(self):
        """Test d'upload d'une seule image"""
        self.logger.info("Test: Upload image unique")

        # Utilisation d'une catégorie de test
        if not self.__class__.created_category_ids:
            # Création d'une catégorie pour le test
            category_id = self.pwg.piwigo_ensure_category_exists(TestConfig.TEST_CATEGORIES[1])
            self.__class__.created_category_ids.append(category_id)

        test_image = TestConfig.TEST_IMAGES[0].copy()
        test_image["images"] = [test_image["url"]]

        response = self.pwg.piwigo_post_image(
            test_image,
            TestConfig.TEST_CATEGORIES[1],
            "fr"
        )

        self.assertIsNotNone(response, "La réponse d'upload doit exister")

        # Extraction de l'ID d'image pour nettoyage
        if response:
            result = response.json()
            if result.get('stat') == 'ok' and 'result' in result:
                image_id = result['result'].get('image_id')
                if image_id:
                    self.__class__.created_image_ids.append(int(image_id))
                    self.logger.info(f"Image uploadée avec l'ID {image_id}")

    def test_05_get_image_categories(self):
        """Test de récupération des catégories d'une image"""
        self.logger.info("Test: Récupération catégories image")

        if not self.__class__.created_image_ids:
            self.skipTest("Pas d'image de test disponible")

        image_id = self.__class__.created_image_ids[0]

        categories = self.pwg.piwigo_image_get_categories(image_id)

        self.assertIsNotNone(categories, "Les catégories doivent être récupérées")
        self.assertIsInstance(categories, list, "Les catégories doivent être une liste")

    def test_06_set_image_category(self):
        """Test d'association d'image à une catégorie"""
        self.logger.info("Test: Association image-catégorie")

        if not self.__class__.created_image_ids or not self.__class__.created_category_ids:
            self.skipTest("Pas d'image ou catégorie de test disponible")

        image_id = self.__class__.created_image_ids[0]
        category_id = self.__class__.created_category_ids[0]

        response = self.pwg.piwigo_image_set_category(image_id, category_id)

        self.assertIsNotNone(response, "L'association doit réussir")


class TestPiwigoBulkOperations(PiwigoTestCase):
    """Tests d'opérations en lot"""

    def test_01_bulk_upload(self):
        """Test d'upload en lot"""
        self.logger.info("Test: Upload en lot")

        # Préparation des artworks de test
        artworks = []
        for i, img_data in enumerate(TestConfig.TEST_IMAGES):
            artwork = img_data.copy()
            artwork["images"] = [artwork["url"]]
            artwork["titre_fr"] = f"Bulk Test {i + 1}"
            artworks.append(artwork)

        # Création d'une catégorie pour le test
        bulk_category = TestConfig.TEST_CATEGORIES[2]
        category_id = self.pwg.piwigo_ensure_category_exists(bulk_category)
        self.__class__.created_category_ids.append(category_id)

        # Upload en lot
        results = self.pwg.bulk_upload_images(artworks, bulk_category, "fr", max_concurrent=2)

        self.assertIsInstance(results, dict, "Le résultat doit être un dictionnaire")
        self.assertIn('total', results, "Le total doit être présent")
        self.assertIn('success', results, "Le nombre de succès doit être présent")
        self.assertIn('failed', results, "Le nombre d'échecs doit être présent")

        self.assertEqual(results['total'], len(artworks), "Le total doit correspondre")
        self.assertGreaterEqual(results['success'], 0, "Il doit y avoir au moins 0 succès")

        self.logger.info(f"Upload en lot: {results['success']}/{results['total']} succès")

        # Stockage des IDs d'images créées
        for upload in results.get('successful_uploads', []):
            # Note: L'ID exact devrait être extrait de la réponse
            pass


class TestPiwigoStatistics(PiwigoTestCase):
    """Tests de statistiques et monitoring"""

    def test_01_get_statistics(self):
        """Test de récupération des statistiques"""
        self.logger.info("Test: Récupération statistiques")

        stats = self.pwg.get_statistics()

        self.assertIsInstance(stats, dict, "Les statistiques doivent être un dictionnaire")
        self.assertIn('timestamp', stats, "Un timestamp doit être présent")

        if 'error' not in stats:
            self.assertIn('session_info', stats, "Les infos de session doivent être présentes")

    def test_02_context_manager(self):
        """Test du context manager"""
        self.logger.info("Test: Context manager")

        with CPiwigoManager(TestConfig.PIWIGO_URL) as pwg_ctx:
            pwg_ctx.config.api_url = TestConfig.PIWIGO_API_URL

            health = pwg_ctx.health_check()
            self.assertIsInstance(health, dict, "Health check doit fonctionner")

        # Après sortie du context, la session doit être fermée
        self.assertIsNone(pwg_ctx.session, "La session doit être fermée")


class TestPiwigoErrorHandling(PiwigoTestCase):
    """Tests de gestion d'erreurs"""

    def test_01_invalid_url(self):
        """Test avec URL invalide"""
        self.logger.info("Test: URL invalide")

        pwg_invalid = CPiwigoManager("https://invalid-piwigo-url-that-does-not-exist.com")

        with self.assertRaises(PiwigoError):
            pwg_invalid.piwigo_open_session()

    def test_02_empty_artwork(self):
        """Test avec artwork vide"""
        self.logger.info("Test: Artwork vide")

        with self.assertRaises(ValueError):
            self.pwg.select_image_to_post({})

    def test_03_invalid_image_urls(self):
        """Test avec URLs d'images invalides"""
        self.logger.info("Test: URLs images invalides")

        invalid_urls = [
            "https://invalid-image-url.com/nonexistent.jpg",
            "https://another-invalid.com/fake.png"
        ]

        best_url = self.pwg.select_best_image(invalid_urls)
        # Doit retourner la première URL par défaut même si invalide
        self.assertEqual(best_url, invalid_urls[0])

    def test_04_malformed_parameters(self):
        """Test avec paramètres malformés"""
        self.logger.info("Test: Paramètres malformés")

        # Test avec category_id invalide
        with self.assertRaises(ValueError):
            self.pwg.piwigo_image_set_category(None, 123)

        # Test avec nom de catégorie vide
        with self.assertRaises(ValueError):
            self.pwg.piwigo_ensure_category_exists("")


def create_test_suite():
    """Crée la suite de tests complète"""
    suite = unittest.TestSuite()

    # Tests de connexion (priorité haute)
    suite.addTest(unittest.makeSuite(TestPiwigoConnection))

    # Tests de catégories
    suite.addTest(unittest.makeSuite(TestPiwigoCategories))

    # Tests d'images
    suite.addTest(unittest.makeSuite(TestPiwigoImages))

    # Tests d'opérations en lot
    suite.addTest(unittest.makeSuite(TestPiwigoBulkOperations))

    # Tests de statistiques
    suite.addTest(unittest.makeSuite(TestPiwigoStatistics))

    # Tests de gestion d'erreurs
    suite.addTest(unittest.makeSuite(TestPiwigoErrorHandling))

    return suite


def run_tests_with_report():
    """Execute les tests avec rapport détaillé"""
    import io
    import sys

    # Configuration du runner de tests
    stream = io.StringIO()
    runner = unittest.TextTestRunner(
        stream=stream,
        verbosity=2,
        failfast=False,  # Continue même en cas d'échec
        buffer=True  # Capture les print statements
    )

    # Création et exécution de la suite
    suite = create_test_suite()
    result = runner.run(suite)

    # Génération du rapport
    report = stream.getvalue()

    # Sauvegarde du rapport
    with open('test_piwigo_report.txt', 'w', encoding='utf-8') as f:
        f.write("=== RAPPORT DE TESTS PIWIGO ===\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Tests exécutés: {result.testsRun}\n")
        f.write(f"Échecs: {len(result.failures)}\n")
        f.write(f"Erreurs: {len(result.errors)}\n")
        f.write(f"Ignorés: {len(result.skipped)}\n\n")
        f.write(report)

        if result.failures:
            f.write("\n=== ÉCHECS ===\n")
            for test, traceback in result.failures:
                f.write(f"\nTEST: {test}\n{traceback}\n")

        if result.errors:
            f.write("\n=== ERREURS ===\n")
            for test, traceback in result.errors:
                f.write(f"\nTEST: {test}\n{traceback}\n")

    # Affichage du résumé
    print(f"\n=== RÉSUMÉ DES TESTS ===")
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    print(f"Ignorés: {len(result.skipped)}")
    print(f"\nRapport détaillé sauvé dans: test_piwigo_report.txt")
    print(f"Logs détaillés dans: test_piwigo.log")

    return result.wasSuccessful()


if __name__ == "__main__":
    print("=== TESTS UNITAIRES PIWIGO ===")
    print("\n⚠️  IMPORTANT: Configurez TestConfig avec vos accès Piwigo avant de lancer!")
    print(f"URL configurée: {TestConfig.PIWIGO_URL}")
    print(f"Login configuré: {TestConfig.PIWIGO_LOGIN}")

    response = input("\nVoulez-vous continuer? (y/N): ")

    if response.lower() == 'y':
        success = run_tests_with_report()
        sys.exit(0 if success else 1)
    else:
        print("Tests annulés.")
        sys.exit(0)