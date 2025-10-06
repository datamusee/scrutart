# ============================================================================
# config.py - Configuration centralisée
# ============================================================================

"""
Configuration de l'application
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration de base"""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    # SPARQL
    SPARQL_ENDPOINT = os.environ.get('SPARQL_ENDPOINT', 'http://localhost:3030/scrutartState/sparql')
    SPARQL_UPDATE_ENDPOINT = os.environ.get('SPARQL_UPDATE_ENDPOINT', 'http://localhost:3030/scrutartState/update')

    # Cache
    SCHEMA_CACHE_FILE = os.environ.get('SCHEMA_CACHE_FILE', 'schema_cache.json')
    QUERY_CACHE_DIR = os.environ.get('QUERY_CACHE_DIR', 'query_cache')
    ASYNC_RESULTS_DIR = os.environ.get('ASYNC_RESULTS_DIR', 'async_results')

    # JWT
    JWT_SECRET = os.environ.get('JWT_SECRET', 'jwt-secret-key-change-in-production')
    JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))

    # OAuth Google
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

    # Mapping type -> graphe
    TYPE_TO_GRAPH = {
        # 'Painting': 'http://example.org/graphs/artworks',
        # 'Artist': 'http://example.org/graphs/persons',
    }
    # Active le cache par défaut pour toutes les requêtes
    ENABLE_QUERY_CACHE=True

    # Durée de vie du cache (en secondes)
    CACHE_TTL_SECONDS=3600

class DevelopmentConfig(Config):
    """Configuration de développement"""
    DEBUG = True


class ProductionConfig(Config):
    """Configuration de production"""
    DEBUG = False


# Configuration par défaut
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
