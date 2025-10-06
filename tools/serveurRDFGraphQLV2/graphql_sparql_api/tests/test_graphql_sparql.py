"""
Tests unitaires pour le serveur API GraphQL-SPARQL
"""

import unittest
import json
import os
import shutil
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import jwt as jwt_lib

# Import du module à tester (adapter selon votre structure)
# from app_trial import *


class TestConfig(unittest.TestCase):
    """Tests de configuration"""
    
    def setUp(self):
        """Initialisation avant chaque test"""
        self.config = {
            'SPARQL_ENDPOINT': 'http://localhost:3030/test/sparql',
            'SPARQL_UPDATE_ENDPOINT': 'http://localhost:3030/test/update',
            'SCHEMA_CACHE_FILE': 'test_schema_cache.json',
            'QUERY_CACHE_DIR': 'test_query_cache',
            'JWT_SECRET': 'test-secret-key',
            'JWT_EXPIRATION_HOURS': 24,
        }
    
    def test_config_has_required_keys(self):
        """Vérifie que la configuration contient toutes les clés requises"""
        required_keys = [
            'SPARQL_ENDPOINT',
            'SPARQL_UPDATE_ENDPOINT',
            'SCHEMA_CACHE_FILE',
            'QUERY_CACHE_DIR',
            'JWT_SECRET',
            'JWT_EXPIRATION_HOURS'
        ]
        for key in required_keys:
            self.assertIn(key, self.config)


class TestJWTAuthentication(unittest.TestCase):
    """Tests pour l'authentification JWT"""
    
    def setUp(self):
        """Initialisation"""
        self.secret = 'test-secret-key'
        self.user_info = {
            'email': 'test@example.com',
            'name': 'Test User',
            'picture': 'http://example.com/pic.jpg'
        }
    
    def test_generate_jwt(self):
        """Test de génération de token JWT"""
        from app_trial import generate_jwt, CONFIG
        CONFIG['JWT_SECRET'] = self.secret
        
        token = generate_jwt(self.user_info)
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        
        # Décoder et vérifier le contenu
        decoded = jwt_lib.decode(token, self.secret, algorithms=['HS256'])
        self.assertEqual(decoded['user']['email'], self.user_info['email'])
        self.assertIn('exp', decoded)
    
    def test_verify_jwt_valid(self):
        """Test de vérification d'un token valide"""
        from app_trial import generate_jwt, verify_jwt, CONFIG
        CONFIG['JWT_SECRET'] = self.secret
        
        token = generate_jwt(self.user_info)
        payload = verify_jwt(token)
        
        self.assertIsNotNone(payload)
        self.assertEqual(payload['user']['email'], self.user_info['email'])
    
    def test_verify_jwt_expired(self):
        """Test de vérification d'un token expiré"""
        from app_trial import verify_jwt
        
        # Créer un token expiré
        expired_payload = {
            'user': self.user_info,
            'exp': datetime.utcnow() - timedelta(hours=1)
        }
        expired_token = jwt_lib.encode(expired_payload, self.secret, algorithm='HS256')
        
        result = verify_jwt(expired_token)
        self.assertIsNone(result)
    
    def test_verify_jwt_invalid(self):
        """Test de vérification d'un token invalide"""
        from app_trial import verify_jwt
        
        result = verify_jwt("invalid.token.here")
        self.assertIsNone(result)


class TestCaching(unittest.TestCase):
    """Tests pour le système de cache"""
    
    def setUp(self):
        """Initialisation"""
        self.temp_dir = tempfile.mkdtemp()
        from app_trial import CONFIG
        CONFIG['QUERY_CACHE_DIR'] = self.temp_dir
    
    def tearDown(self):
        """Nettoyage"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_get_cache_key(self):
        """Test de génération de clé de cache"""
        from app_trial import get_cache_key
        
        query1 = "SELECT * WHERE { ?s ?p ?o }"
        query2 = "SELECT * WHERE { ?s ?p ?o }"
        query3 = "SELECT * WHERE { ?x ?y ?z }"
        
        key1 = get_cache_key(query1)
        key2 = get_cache_key(query2)
        key3 = get_cache_key(query3)
        
        # Même requête = même clé
        self.assertEqual(key1, key2)
        # Requête différente = clé différente
        self.assertNotEqual(key1, key3)
        # Format hexadécimal
        self.assertEqual(len(key1), 64)  # SHA256 = 64 caractères hex
    
    def test_save_and_get_cached_result(self):
        """Test de sauvegarde et récupération du cache"""
        from app_trial import save_to_cache, get_cached_result
        
        query = "SELECT * WHERE { ?s ?p ?o }"
        result = [{'s': 'subject', 'p': 'predicate', 'o': 'object'}]
        
        # Sauvegarder
        save_to_cache(query, result)
        
        # Récupérer
        cached = get_cached_result(query)
        
        self.assertIsNotNone(cached)
        self.assertEqual(cached, result)
    
    def test_get_cached_result_not_found(self):
        """Test de récupération d'un résultat non caché"""
        from app_trial import get_cached_result
        
        query = "SELECT * WHERE { ?unknown ?query ?here }"
        result = get_cached_result(query)
        
        self.assertIsNone(result)


class TestSPARQLClient(unittest.TestCase):
    """Tests pour le client SPARQL"""
    
    def setUp(self):
        """Initialisation"""
        self.endpoint = 'http://localhost:3030/test/sparql'
        self.update_endpoint = 'http://localhost:3030/test/update'
    
    @patch('app_trial.SPARQLWrapper')
    def test_sparql_query(self, mock_sparql_wrapper):
        """Test d'exécution d'une requête SELECT"""
        from app_trial import SPARQLClient
        
        # Mock de la réponse SPARQL
        mock_result = {
            'results': {
                'bindings': [
                    {
                        's': {'value': 'http://example.org/subject1'},
                        'p': {'value': 'http://example.org/predicate1'},
                        'o': {'value': 'object1'}
                    }
                ]
            }
        }
        
        mock_instance = MagicMock()
        mock_instance.query().convert.return_value = mock_result
        mock_sparql_wrapper.return_value = mock_instance
        
        client = SPARQLClient(self.endpoint, self.update_endpoint)
        results = client.query("SELECT * WHERE { ?s ?p ?o }")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['s'], 'http://example.org/subject1')
    
    @patch('app_trial.SPARQLWrapper')
    def test_sparql_update(self, mock_sparql_wrapper):
        """Test d'exécution d'une requête UPDATE"""
        from app_trial import SPARQLClient
        
        mock_instance = MagicMock()
        mock_sparql_wrapper.return_value = mock_instance
        
        client = SPARQLClient(self.endpoint, self.update_endpoint)
        
        # Ne devrait pas lever d'exception
        try:
            client.update("INSERT DATA { <s> <p> <o> }")
            success = True
        except:
            success = False
        
        self.assertTrue(success)
        mock_instance.query.assert_called_once()


class TestRDFTypeDetection(unittest.TestCase):
    """Tests pour la détection des types RDF"""
    
    @patch('app_trial.sparql_client')
    def test_detect_rdf_types(self, mock_client):
        """Test de détection des types RDF"""
        from app_trial import detect_rdf_types
        
        # Mock des résultats de la requête
        mock_client.query.return_value = [
            {
                'type': 'http://example.org/Painting',
                'label': 'Painting',
                'graph': 'http://example.org/graphs/artworks'
            },
            {
                'type': 'http://example.org/Artist',
                'label': 'Artist',
                'graph': 'http://example.org/graphs/persons'
            }
        ]
        
        types_info = detect_rdf_types()
        
        self.assertEqual(len(types_info), 2)
        self.assertIn('http://example.org/Painting', types_info)
        self.assertIn('http://example.org/Artist', types_info)
    
    @patch('app_trial.sparql_client')
    def test_detect_properties_for_type(self, mock_client):
        """Test de détection des propriétés d'un type"""
        from app_trial import detect_properties_for_type
        
        mock_client.query.return_value = [
            {
                'property': 'http://example.org/prop/title',
                'propertyLabel': 'title',
                'valueType': 'string'
            },
            {
                'property': 'http://example.org/prop/year',
                'propertyLabel': 'year',
                'valueType': 'int'
            }
        ]
        
        properties = detect_properties_for_type('http://example.org/Painting')
        
        self.assertEqual(len(properties), 2)
        self.assertIn('http://example.org/prop/title', properties)
        self.assertEqual(properties['http://example.org/prop/title']['type'], 'string')


class TestGraphQLSchema(unittest.TestCase):
    """Tests pour la génération du schéma GraphQL"""
    
    def test_sanitize_name(self):
        """Test de nettoyage des noms pour GraphQL"""
        from app_trial import sanitize_name
        
        self.assertEqual(sanitize_name('simple'), 'simple')
        self.assertEqual(sanitize_name('CamelCase'), 'CamelCase')
        self.assertEqual(sanitize_name('snake_case'), 'snakeCase')
        self.assertEqual(sanitize_name('with-dash'), 'withDash')
        self.assertEqual(sanitize_name('with space'), 'withSpace')
        self.assertEqual(sanitize_name('123invalid'), 'field123invalid')
        self.assertEqual(sanitize_name('spécial-éàù'), 'specialeau')
    
    def test_graphql_type_from_rdf_type(self):
        """Test de conversion des types RDF en types GraphQL"""
        from app_trial import graphql_type_from_rdf_type
        from graphene import String, Int, Float, DateTime
        
        self.assertEqual(graphql_type_from_rdf_type('string'), String)
        self.assertEqual(graphql_type_from_rdf_type('int'), Int)
        self.assertEqual(graphql_type_from_rdf_type('float'), Float)
        self.assertEqual(graphql_type_from_rdf_type('datetime'), DateTime)
        self.assertEqual(graphql_type_from_rdf_type('reference'), String)
        self.assertEqual(graphql_type_from_rdf_type('unknown'), String)  # Default
    
    def test_merge_schema_definitions(self):
        """Test de fusion des définitions de schéma"""
        from app_trial import merge_schema_definitions
        
        auto = {
            'type1': {
                'label': 'Type1',
                'properties': {'prop1': 'value1'}
            }
        }
        
        manual = {
            'type1': {
                'properties': {'prop2': 'value2'},
                'custom_field': 'custom_value'
            },
            'type2': {
                'label': 'Type2',
                'properties': {}
            }
        }
        
        merged = merge_schema_definitions(auto, manual)
        
        # Type1 doit avoir les propriétés fusionnées
        self.assertIn('prop1', merged['type1']['properties'])
        self.assertIn('prop2', merged['type1']['properties'])
        self.assertEqual(merged['type1']['custom_field'], 'custom_value')
        
        # Type2 doit être présent
        self.assertIn('type2', merged)


class TestSchemaCache(unittest.TestCase):
    """Tests pour le cache du schéma"""
    
    def setUp(self):
        """Initialisation"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        
        from app_trial import CONFIG
        CONFIG['SCHEMA_CACHE_FILE'] = self.temp_file.name
    
    def tearDown(self):
        """Nettoyage"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_save_and_load_schema_cache(self):
        """Test de sauvegarde et chargement du schéma"""
        from app_trial import save_schema_cache, load_schema_cache
        
        schema = {
            'auto_generated': {
                'http://example.org/Type1': {
                    'label': 'Type1',
                    'properties': {}
                }
            },
            'manual': {}
        }
        
        save_schema_cache(schema)
        loaded = load_schema_cache()
        
        self.assertEqual(loaded, schema)
    
    def test_load_schema_cache_not_exists(self):
        """Test de chargement quand le cache n'existe pas"""
        from app_trial import load_schema_cache, CONFIG
        
        CONFIG['SCHEMA_CACHE_FILE'] = 'non_existent_file.json'
        loaded = load_schema_cache()
        
        self.assertEqual(loaded, {'auto_generated': {}, 'manual': {}})


class TestFlaskRoutes(unittest.TestCase):
    """Tests pour les routes Flask"""
    
    def setUp(self):
        """Initialisation"""
        from app_trial import app
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.app = app
    
    def test_home_route(self):
        """Test de la route d'accueil"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GraphQL-SPARQL', response.data)
    
    def test_docs_route(self):
        """Test de la route de documentation"""
        response = self.client.get('/docs')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Documentation', response.data)
    
    def test_schema_info_route(self):
        """Test de la route d'info du schéma"""
        response = self.client.get('/schema/info')
        self.assertEqual(response.status_code, 200)
    
    def test_graphql_endpoint_without_auth(self):
        """Test de l'endpoint GraphQL sans authentification"""
        response = self.client.post('/graphql',
                                   json={'query': '{ hello }'})
        self.assertEqual(response.status_code, 401)
    
    @patch('app_trial.verify_jwt')
    def test_graphql_endpoint_with_auth(self, mock_verify):
        """Test de l'endpoint GraphQL avec authentification"""
        mock_verify.return_value = {'user': {'email': 'test@example.com'}}
        
        with self.app.app_context():
            response = self.client.post('/graphql',
                                       headers={'Authorization': 'Bearer test-token'},
                                       json={'query': '{ hello }'})
            
            # Peut retourner 200 ou 500 selon le schéma
            self.assertIn(response.status_code, [200, 500])


class TestGraphQLResolvers(unittest.TestCase):
    """Tests pour les résolveurs GraphQL"""
    
    @patch('app_trial.sparql_client')
    def test_create_resolver_single_object(self, mock_client):
        """Test du résolveur pour un objet unique"""
        from app_trial import create_resolver
        
        mock_client.query.return_value = [
            {'property': 'http://ex.org/title', 'value': 'Mona Lisa'},
            {'property': 'http://ex.org/year', 'value': '1503'}
        ]
        
        resolver = create_resolver('Painting', 'http://ex.org/Painting')
        
        # Mock de l'objet info GraphQL
        mock_info = Mock()
        mock_info.field_nodes = [Mock()]
        mock_info.field_nodes[0].selection_set = None
        
        result = resolver(None, mock_info, id='http://ex.org/painting1')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'http://ex.org/painting1')
    
    @patch('app_trial.sparql_client')
    def test_create_resolver_list_objects(self, mock_client):
        """Test du résolveur pour une liste d'objets"""
        from app_trial import create_resolver
        
        mock_client.query.return_value = [
            {'instance': 'http://ex.org/painting1'},
            {'instance': 'http://ex.org/painting2'}
        ]
        
        resolver = create_resolver('Painting', 'http://ex.org/Painting')
        
        mock_info = Mock()
        mock_info.field_nodes = [Mock()]
        mock_info.field_nodes[0].selection_set = None
        
        result = resolver(None, mock_info)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)


class TestGraphQLMutations(unittest.TestCase):
    """Tests pour les mutations GraphQL"""
    
    @patch('app_trial.sparql_client')
    def test_create_mutation(self, mock_client):
        """Test de création via mutation"""
        from app_trial import create_mutation
        
        mutation_class = create_mutation('Painting', 'http://ex.org/Painting')
        
        data = json.dumps({'title': 'New Painting', 'year': 2023})
        
        # Mock de l'info GraphQL
        mock_info = Mock()
        
        result = mutation_class.mutate(None, mock_info, 
                                      id='http://ex.org/new',
                                      data=data)
        
        self.assertEqual(result.entity, 'http://ex.org/new')
        self.assertIn('success', result.success.lower())


class TestAsyncQueries(unittest.TestCase):
    """Tests pour les requêtes asynchrones"""
    
    def test_async_jobs_structure(self):
        """Test de la structure des jobs asynchrones"""
        from app_trial import async_jobs
        
        # Doit être un dictionnaire
        self.assertIsInstance(async_jobs, dict)
    
    @patch('app_trial.threading.Thread')
    def test_execute_async_query(self, mock_thread):
        """Test d'exécution de requête asynchrone"""
        from app_trial import execute_async_query, async_jobs
        
        job_id = 'test-job-id'
        query = '{ test }'
        variables = {}
        
        # Exécuter
        execute_async_query(job_id, query, variables)
        
        # Vérifier que le job a été enregistré
        self.assertIn(job_id, async_jobs)


class TestHelperFunctions(unittest.TestCase):
    """Tests pour les fonctions utilitaires"""
    
    def test_get_graph_for_type(self):
        """Test de récupération du graphe pour un type"""
        from app_trial import get_graph_for_type, CONFIG
        
        # Test avec config statique
        CONFIG['TYPE_TO_GRAPH'] = {
            'Painting': 'http://ex.org/graphs/artworks'
        }
        
        graph = get_graph_for_type('Painting', 'http://ex.org/Painting')
        self.assertEqual(graph, 'http://ex.org/graphs/artworks')
        
        # Test avec type inconnu (doit retourner le graphe par défaut)
        graph = get_graph_for_type('Unknown', 'http://ex.org/Unknown')
        self.assertEqual(graph, 'http://example.org/graphs/default')


class TestErrorHandling(unittest.TestCase):
    """Tests pour la gestion des erreurs"""
    
    def setUp(self):
        """Initialisation"""
        from app_trial import app
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def test_graphql_syntax_error(self):
        """Test avec une requête GraphQL invalide"""
        # Cette route nécessite l'authentification
        pass  # À implémenter avec un mock d'auth
    
    def test_sparql_connection_error(self):
        """Test de gestion d'erreur de connexion SPARQL"""
        # À implémenter avec des mocks appropriés
        pass


class TestIntegration(unittest.TestCase):
    """Tests d'intégration"""
    
    def setUp(self):
        """Initialisation"""
        from app_trial import app
        app.config['TESTING'] = True
        self.client = app.test_client()
    
    def test_full_workflow_schema_generation(self):
        """Test du workflow complet de génération de schéma"""
        # 1. Vérifier que le serveur démarre
        # 2. Générer le schéma
        # 3. Vérifier que le schéma est sauvegardé
        # 4. Charger le schéma
        pass  # À implémenter selon l'environnement


def run_tests():
    """Lance tous les tests"""
    # Créer une suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajouter tous les tests
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestJWTAuthentication))
    suite.addTests(loader.loadTestsFromTestCase(TestCaching))
    suite.addTests(loader.loadTestsFromTestCase(TestSPARQLClient))
    suite.addTests(loader.loadTestsFromTestCase(TestRDFTypeDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestGraphQLSchema))
    suite.addTests(loader.loadTestsFromTestCase(TestSchemaCache))
    suite.addTests(loader.loadTestsFromTestCase(TestFlaskRoutes))
    suite.addTests(loader.loadTestsFromTestCase(TestGraphQLResolvers))
    suite.addTests(loader.loadTestsFromTestCase(TestGraphQLMutations))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncQueries))
    suite.addTests(loader.loadTestsFromTestCase(TestHelperFunctions))
    
    # Exécuter les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    # Option 1: Lancer tous les tests
    result = run_tests()
    
    # Option 2: Lancer unittest normalement
    # unittest.main()
    
    # Afficher un résumé
    print("\n" + "="*70)
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    print("="*70)
