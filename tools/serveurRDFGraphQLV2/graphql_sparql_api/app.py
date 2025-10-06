import os
from flask import Flask
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth

from config import Config

# Variable globale pour le schéma GraphQL
graphql_schema = None

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    
    oauth = OAuth(app)
    google = oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
    
    os.makedirs(app.config['QUERY_CACHE_DIR'], exist_ok=True)
    os.makedirs(app.config['ASYNC_RESULTS_DIR'], exist_ok=True)
    
    from core.authentication import AuthenticationManager
    from core.cache import CacheManager
    from core.sparql_client import SPARQLClient
    from core.schema_generator import SchemaGenerator
    
    auth_manager = AuthenticationManager(app.config['JWT_SECRET'], app.config['JWT_EXPIRATION_HOURS'])
    cache_manager = CacheManager(app.config['QUERY_CACHE_DIR'])
    sparql_client = SPARQLClient(app.config['SPARQL_ENDPOINT'], app.config['SPARQL_UPDATE_ENDPOINT'], cache_manager)
    schema_generator = SchemaGenerator(sparql_client, app.config["TYPE_TO_GRAPH"], app.config['SCHEMA_CACHE_FILE'])
    
    async_jobs = {}
    
    from routes.auth_routes import init_auth_routes
    from routes.api_routes import init_api_routes
    from routes.admin_routes import init_admin_routes
    from routes.graphql_routes import init_graphql_routes
    
    init_auth_routes(app, oauth, google, auth_manager)
    init_api_routes(app)
    init_admin_routes(app, auth_manager, schema_generator, cache_manager, app.config, schema= graphql_schema)
    init_graphql_routes(app, auth_manager, schema_generator, async_jobs, app.config['ASYNC_RESULTS_DIR'])
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("Serveur sur http://localhost:5000")
    app.run(debug=False, port=5000, threaded=True)
