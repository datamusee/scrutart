"""
API GraphQL pour interroger et modifier des données RDF via SPARQL
Serveur Flask avec authentification OAuth/JWT et cache persistant
"""

import os
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from functools import wraps
import threading

from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
import graphene
from graphene import ObjectType, String, Int, Float, DateTime, Field, List as GList, Mutation, Schema
from graphql import GraphQLError
import requests
from SPARQLWrapper import SPARQLWrapper, JSON, POST
import jwt
from authlib.integrations.flask_client import OAuth
import unidecode

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    'SPARQL_ENDPOINT': 'http://localhost:3030/scrutartState/sparql',
    'SPARQL_UPDATE_ENDPOINT': 'http://localhost:3030/scrutartState/update',
    'SCHEMA_CACHE_FILE': 'schema_cache.json',
    'QUERY_CACHE_DIR': 'query_cache',
    'ASYNC_RESULTS_DIR': 'async_results',
    'JWT_SECRET': 'your-secret-key-change-in-production',
    'JWT_EXPIRATION_HOURS': 24,
    'GOOGLE_CLIENT_ID': 'your-google-client-id',
    'GOOGLE_CLIENT_SECRET': 'your-google-client-secret',
    'TYPE_TO_GRAPH': {
        # Configuration statique type -> graphe nommé
        'Painting': 'http://example.org/graphs/artworks',
        'Artist': 'http://example.org/graphs/persons',
        'Museum': 'http://example.org/graphs/places',
    }
}

from dotenv import load_dotenv

load_result = load_dotenv()
CONFIG["GOOGLE_CLIENT_ID"] = os.environ.get('GOOGLE_CLIENT_ID', '❌ NON DÉFINI')
CONFIG["GOOGLE_CLIENT_SECRET"] = os.environ.get('GOOGLE_CLIENT_SECRET', '❌ NON DÉFINI')
SECRET_KEY = os.environ.get('SECRET_KEY', '❌ NON DÉFINI')

# ============================================================================
# INITIALISATION FLASK ET OAUTH
# ============================================================================

app = Flask(__name__)
app.secret_key = SECRET_KEY # 'flask-secret-key-change-in-production'
CORS(app)

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=CONFIG['GOOGLE_CLIENT_ID'],
    client_secret=CONFIG['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Créer les répertoires nécessaires
os.makedirs(CONFIG['QUERY_CACHE_DIR'], exist_ok=True)
os.makedirs(CONFIG['ASYNC_RESULTS_DIR'], exist_ok=True)


# ============================================================================
# AUTHENTIFICATION
# ============================================================================

def generate_jwt(user_info: Dict) -> str:
    """Génère un token JWT pour l'utilisateur"""
    payload = {
        'user': user_info,
        'exp': datetime.utcnow() + timedelta(hours=CONFIG['JWT_EXPIRATION_HOURS'])
    }
    return jwt.encode(payload, CONFIG['JWT_SECRET'], algorithm='HS256')


def verify_jwt(token: str) -> Optional[Dict]:
    """Vérifie et décode un token JWT"""
    try:
        return jwt.decode(token, CONFIG['JWT_SECRET'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
    """Décorateur pour protéger les routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_jwt(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        request.user = payload['user']
        return f(*args, **kwargs)

    return decorated_function


# ============================================================================
# CACHE
# ============================================================================

def get_cache_key(query: str) -> str:
    """Génère une clé de cache à partir d'une requête"""
    return hashlib.sha256(query.encode()).hexdigest()


def get_cached_result(query: str, cache_type: str = 'sparql') -> Optional[Any]:
    """Récupère un résultat du cache"""
    cache_key = get_cache_key(query)
    cache_file = os.path.join(CONFIG['QUERY_CACHE_DIR'], f"{cache_type}_{cache_key}.json")

    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    return None


def save_to_cache(query: str, result: Any, cache_type: str = 'sparql'):
    """Sauvegarde un résultat dans le cache"""
    cache_key = get_cache_key(query)
    cache_file = os.path.join(CONFIG['QUERY_CACHE_DIR'], f"{cache_type}_{cache_key}.json")

    with open(cache_file, 'w') as f:
        json.dump(result, f, indent=2)


# ============================================================================
# SPARQL
# ============================================================================

class SPARQLClient:
    """Client pour interagir avec l'endpoint SPARQL"""

    def __init__(self, endpoint: str, update_endpoint: str):
        self.endpoint = endpoint
        self.update_endpoint = update_endpoint

    def query(self, sparql_query: str, use_cache: bool = False) -> List[Dict]:
        """Exécute une requête SPARQL SELECT"""
        if use_cache:
            cached = get_cached_result(sparql_query, 'sparql')
            if cached:
                return cached

        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)

        results = sparql.query().convert()
        bindings = results['results']['bindings']

        # Convertir en format plus simple
        simplified = []
        for binding in bindings:
            row = {}
            for key, value in binding.items():
                row[key] = value['value']
            simplified.append(row)

        if use_cache:
            save_to_cache(sparql_query, simplified, 'sparql')

        return simplified

    def update(self, sparql_update: str):
        """Exécute une requête SPARQL UPDATE"""
        sparql = SPARQLWrapper(self.update_endpoint)
        sparql.setQuery(sparql_update)
        sparql.method = POST
        sparql.query()

    def get_all_named_graphs(self) -> List[str]:
        """Récupère tous les graphes nommés"""
        query = "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }"
        results = self.query(query)
        return [r['g'] for r in results]


sparql_client = SPARQLClient(CONFIG['SPARQL_ENDPOINT'], CONFIG['SPARQL_UPDATE_ENDPOINT'])


# ============================================================================
# DÉTECTION DES TYPES RDF
# ============================================================================

def detect_rdf_types() -> Dict[str, Any]:
    """Détecte tous les types RDF dans le graphe"""

    # Requête pour détecter les types avec P31 (Wikidata) ou rdf:type
    query = """

    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

    SELECT DISTINCT ?type ?label ?graph WHERE {
  {
                ?instance rdf:type ?type .
                OPTIONAL { ?type rdfs:label ?label }
  } UNION
  {
                ?instance wdt:P31 ?type .
                OPTIONAL { ?type rdfs:label ?label }
  } UNION
        {
            GRAPH ?graph {
                ?instance wdt:P31 ?type .
                OPTIONAL { ?type rdfs:label ?label }
            }
        } UNION {
            GRAPH ?graph {
                ?instance rdf:type ?type .
                OPTIONAL { ?type rdfs:label ?label }
            }
        }
        FILTER(?type != rdf:Property && ?type != rdfs:Class)
    }
        """

    results = sparql_client.query(query)

    types_info = {}
    for result in results:
        type_uri = result['type']
        label = result.get('label', type_uri.split('/')[-1].split('#')[-1])
        graph = result['graph'] if 'graph' in result else None

        if type_uri not in types_info:
            types_info[type_uri] = {
                'uri': type_uri,
                'label': label,
                'graphs': set(),
                'properties': {}
            }

        types_info[type_uri]['graphs'].add(graph)

    # Convertir les sets en listes pour la sérialisation JSON
    for type_info in types_info.values():
        type_info['graphs'] = list(type_info['graphs'])

    return types_info


@app.route('/schema/info')
def schema_info():
    """Affiche les informations sur le schéma actuel"""

    schema_cache = load_schema_cache()
    merged = merge_schema_definitions(
        schema_cache.get('auto_generated', {}),
        schema_cache.get('manual', {})
    )

    types_html = ""
    for type_uri, type_info in merged.items():
        type_name = sanitize_name(type_info['label'])
        props_html = ""
        for prop_uri, prop_info in type_info.get('properties', {}).items():
            props_html += f"<li><strong>{sanitize_name(prop_info['label'])}</strong>: {prop_info['type']}</li>"

        types_html += f"""
        <div class="type-box">
            <h3>{type_name}</h3>
            <p><small>URI: {type_uri}</small></p>
            <p><strong>Graphes:</strong> {', '.join(type_info.get('graphs', ["Pas de graphe"]) if type_info["graphs"]!=[None] else [])}</p>
            <p><strong>Propriétés:</strong></p>
            <ul>{props_html if props_html else '<li>Aucune propriété détectée</li>'}</ul>

            <div class="queries">
                <strong>Requêtes disponibles:</strong>
                <ul>
                    <li><code>get{type_name}(id: String!)</code></li>
                    <li><code>all{type_name}s</code></li>
                </ul>
            </div>

            <div class="mutations">
                <strong>Mutations disponibles:</strong>
                <ul>
                    <li><code>create{type_name}(id: String!, data: String!)</code></li>
                    <li><code>delete{type_name}(id: String!)</code></li>
                </ul>
            </div>
        </div>
        """

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Schéma GraphQL - Info</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 20px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            h1 {{
                color: #2c3e50;
            }}
            .header {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .type-box {{
                background: white;
                padding: 20px;
                margin: 15px 0;
                border-radius: 8px;
                border-left: 4px solid #3498db;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .type-box h3 {{
                margin-top: 0;
                color: #2c3e50;
            }}
            .type-box ul {{
                padding-left: 20px;
            }}
            .queries, .mutations {{
                background: #f8f9fa;
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
            }}
            code {{
                background: #e8f5e9;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
            }}
            .btn {{
                display: inline-block;
                padding: 10px 20px;
                margin: 5px;
                background: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }}
            .btn-refresh {{
                background: #27ae60;
            }}
            .btn:hover {{
                opacity: 0.9;
            }}
            .warning {{
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 15px 0;
                border-radius: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Schéma GraphQL - Informations</h1>
            <p>
                <strong>Types détectés:</strong> {len(merged)}<br>
                <strong>Cache:</strong> {'✓ Présent' if os.path.exists(CONFIG['SCHEMA_CACHE_FILE']) else '✗ Absent'}
            </p>
            <div>
                <a href="/" class="btn">🏠 Accueil</a>
                <a href="/graphiql" class="btn">🎨 GraphiQL</a>
                <a href="#" onclick="refreshSchema()" class="btn btn-refresh">🔄 Régénérer le schéma</a>
            </div>
        </div>

        {types_html if types_html else '<div class="warning">⚠️ Aucun type RDF détecté. Cliquez sur "Régénérer le schéma" pour scanner votre endpoint SPARQL.</div>'}

        <script>
            function refreshSchema() {{
                if (confirm('Régénérer le schéma depuis l\'endpoint SPARQL ?')) {{
                    fetch('/schema/refresh', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }}
                    }})
                    .then(r => r.json())
                    .then(data => {{
                        alert('Schéma régénéré: ' + data.types_detected + ' types détectés');
                        location.reload();
                    }})
                    .catch(err => {{
                        alert('Erreur: ' + err);
                    }});
                }}
            }}
        </script>
    </body>
    </html>
    '''
    """Vide le cache des requêtes"""
    import shutil
    shutil.rmtree(CONFIG['QUERY_CACHE_DIR'])
    os.makedirs(CONFIG['QUERY_CACHE_DIR'])
    return jsonify({'message': 'Cache cleared successfully'})


def detect_properties_for_type(type_uri: str) -> Dict[str, Any]:
    """Détecte les propriétés utilisées pour un type donné"""

    query = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?property ?propertyLabel ?valueType WHERE {{
        {{
            ?instance wdt:P31 <{type_uri}> .
            ?instance ?property ?value .
        }} UNION {{
            ?instance rdf:type <{type_uri}> .
            ?instance ?property ?value .
        }}

        OPTIONAL {{ ?property rdfs:label ?propertyLabel }}

        BIND(
            IF(isLiteral(?value),
                IF(datatype(?value) = <http://www.w3.org/2001/XMLSchema#integer>, "int",
                IF(datatype(?value) = <http://www.w3.org/2001/XMLSchema#float>, "float",
                IF(datatype(?value) = <http://www.w3.org/2001/XMLSchema#double>, "float",
                IF(datatype(?value) = <http://www.w3.org/2001/XMLSchema#dateTime>, "datetime",
                IF(datatype(?value) = <http://www.w3.org/2001/XMLSchema#date>, "date",
                "string"))))),
                "reference"
            ) AS ?valueType
        )
    }}
    LIMIT 1000
    """

    results = sparql_client.query(query)

    properties = {}
    for result in results:
        prop_uri = result['property']
        prop_label = result.get('propertyLabel', prop_uri.split('/')[-1].split('#')[-1])
        value_type = result['valueType']

        if prop_uri not in properties:
            properties[prop_uri] = {
                'uri': prop_uri,
                'label': prop_label,
                'type': value_type
            }

    return properties


# ============================================================================
# GÉNÉRATION DU SCHÉMA GRAPHQL
# ============================================================================

def generate_graphql_schema() -> Dict[str, Any]:
    """Génère le schéma GraphQL à partir des types RDF détectés"""

    print("Détection des types RDF...")
    types_info = detect_rdf_types()

    print(f"Types détectés: {len(types_info)}")

    # Détecter les propriétés pour chaque type
    for type_uri, type_info in types_info.items():
        print(f"Détection des propriétés pour {type_info['label']}...")
        type_info['properties'] = detect_properties_for_type(type_uri)

    schema = {
        'auto_generated': types_info,
        'manual': {}
    }

    return schema


def load_schema_cache() -> Dict[str, Any]:
    """Charge le schéma depuis le cache"""
    if os.path.exists(CONFIG['SCHEMA_CACHE_FILE']):
        with open(CONFIG['SCHEMA_CACHE_FILE'], 'r') as f:
            return json.load(f)
    return {'auto_generated': {}, 'manual': {}}


def save_schema_cache(schema: Dict[str, Any]):
    """Sauvegarde le schéma dans le cache"""
    with open(CONFIG['SCHEMA_CACHE_FILE'], 'w') as f:
        json.dump(schema, f, indent=2)


def merge_schema_definitions(auto: Dict, manual: Dict) -> Dict:
    """Fusionne les définitions auto et manuelles avec priorité au manuel"""
    merged = auto.copy()

    for type_uri, manual_def in manual.items():
        if type_uri in merged:
            # Fusion des propriétés
            merged[type_uri]['properties'].update(manual_def.get('properties', {}))
            # Surcharge des autres attributs
            for key, value in manual_def.items():
                if key != 'properties':
                    merged[type_uri][key] = value
        else:
            merged[type_uri] = manual_def

    return merged


# ============================================================================
# CONSTRUCTION DYNAMIQUE DES TYPES GRAPHQL
# ============================================================================

def graphql_type_from_rdf_type(rdf_type: str) -> type:
    """Convertit un type RDF en type GraphQL"""
    mapping = {
        'string': String,
        'int': Int,
        'float': Float,
        'datetime': DateTime,
        'date': String,  # On utilise String pour les dates
        'reference': String  # Les références sont des URIs (String)
    }
    return mapping.get(rdf_type, String)


def sanitize_name(name: str) -> str:
    """Nettoie un nom pour qu'il soit valide en GraphQL"""
    # Remplacer les caractères non alphanumériques
    name = ''.join(c if c.isalnum() else '_' for c in name)
    name = unidecode.unidecode(name)
    # S'assurer que ça commence par une lettre
    if name and not name[0].isalpha():
        name = 'T_' + name
    return name or 'Unknown'


def build_graphql_types(schema_def: Dict) -> Dict[str, type]:
    """Construit les types GraphQL à partir du schéma"""

    graphql_types = {}

    for type_uri, type_info in schema_def.items():
        type_name = sanitize_name(type_info['label'])

        # Préparer les champs
        fields = {
            'id': Field(String, description="URI de l'entité"),
        }

        for prop_uri, prop_info in type_info.get('properties', {}).items():
            prop_name = sanitize_name(prop_info['label'])
            prop_type = graphql_type_from_rdf_type(prop_info['type'])

            # Pour les références, on utilise String (URI) pour l'instant
            # Dans une version plus avancée, on pourrait résoudre les types
            fields[prop_name] = Field(prop_type, description=prop_uri)

        # Créer le type dynamiquement
        graphql_type = type(type_name, (ObjectType,), fields)
        graphql_types[type_name] = graphql_type

    return graphql_types


# ============================================================================
# RÉSOLVEURS GRAPHQL
# ============================================================================

class DynamicQuery(ObjectType):
    """Classe de requête GraphQL construite dynamiquement"""
    pass


def create_resolver(type_name: str, type_uri: str):
    """Crée un résolveur pour un type donné"""

    def resolver(root, info, id=None, use_cache=False):
        """Résout une requête pour ce type"""

        # Construire la requête SPARQL
        if id:
            # Requête pour un objet spécifique
            query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>

            SELECT ?property ?value WHERE {{
                {{
                    <{id}> wdt:P31 <{type_uri}> .
                    <{id}> ?property ?value .
                }} UNION {{
                    <{id}> rdf:type <{type_uri}> .
                    <{id}> ?property ?value .
                }}
            }}
            """
        else:
            # Requête pour tous les objets du type
            query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>

            SELECT DISTINCT ?instance WHERE {{
                {{
                    ?instance wdt:P31 <{type_uri}> .
                }} UNION {{
                    ?instance rdf:type <{type_uri}> .
                }}
            }}
            LIMIT 100
            """

        results = sparql_client.query(query, use_cache=use_cache)

        # Transformer les résultats
        if id:
            obj = {'id': id}
            for r in results:
                prop = r['property'].split('/')[-1]
                obj[prop] = r['value']
            return obj
        else:
            return [{'id': r['instance']} for r in results]

    return resolver


# ============================================================================
# MUTATIONS GRAPHQL
# ============================================================================

def get_graph_for_type(type_name: str, type_uri: str) -> str:
    """Détermine le graphe nommé pour un type"""
    # D'abord chercher dans la config statique
    if type_name in CONFIG['TYPE_TO_GRAPH']:
        return CONFIG['TYPE_TO_GRAPH'][type_name]

    # Sinon, chercher dans le schéma
    schema = load_schema_cache()
    merged = merge_schema_definitions(schema['auto_generated'], schema['manual'])

    if type_uri in merged:
        graphs = merged[type_uri].get('graphs', [])
        if graphs:
            return graphs[0]  # Prendre le premier graphe

    # Par défaut
    return 'http://example.org/graphs/default'


def create_mutation(type_name: str, type_uri: str):
    """Crée une mutation pour un type donné"""

    class TypeMutation(Mutation):
        class Arguments:
            id = String(required=True)
            data = String(required=True)  # JSON stringifié

        success = Field(String)
        entity = Field(String)

        def mutate(root, info, id, data):
            """Effectue la mutation"""
            try:
                data_dict = json.loads(data)
                graph = get_graph_for_type(type_name, type_uri)

                # Construire la requête INSERT
                triples = []
                triples.append(f"<{id}> rdf:type <{type_uri}> .")

                for prop, value in data_dict.items():
                    if isinstance(value, str) and value.startswith('http'):
                        # C'est une référence
                        triples.append(f"<{id}> <{prop}> <{value}> .")
                    else:
                        # C'est un litéral
                        escaped_value = str(value).replace('"', '\\"')
                        triples.append(f'<{id}> <{prop}> "{escaped_value}" .')

                update_query = f"""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                INSERT DATA {{
                    GRAPH <{graph}> {{
                        {' '.join(triples)}
                    }}
                }}
                """

                sparql_client.update(update_query)

                return TypeMutation(
                    success="Entity created/updated successfully",
                    entity=id
                )
            except Exception as e:
                raise GraphQLError(f"Mutation failed: {str(e)}")

    return TypeMutation


# ============================================================================
# REQUÊTES ASYNCHRONES
# ============================================================================

async_jobs = {}


def execute_async_query(job_id: str, query: str, variables: Dict):
    """Exécute une requête GraphQL de manière asynchrone"""
    try:
        # Simuler l'exécution (à adapter avec votre schéma réel)
        result = {'data': 'async result', 'job_id': job_id}

        # Sauvegarder le résultat
        result_file = os.path.join(CONFIG['ASYNC_RESULTS_DIR'], f"{job_id}.json")
        with open(result_file, 'w') as f:
            json.dump(result, f)

        async_jobs[job_id] = {'status': 'completed', 'result_file': result_file}
    except Exception as e:
        async_jobs[job_id] = {'status': 'failed', 'error': str(e)}


# ============================================================================
# ROUTES FLASK
# ============================================================================

@app.route('/login')
def login():
    """Initie le flux OAuth Google"""
    redirect_uri = request.url_root.rstrip('/') + '/auth/callback'
    return google.authorize_redirect(redirect_uri)


@app.route('/auth/callback')
def auth_callback():
    """Callback OAuth Google"""
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if user_info:
            jwt_token = generate_jwt({
                'email': user_info.get('email'),
                'name': user_info.get('name')
            })

            # Stocker le token dans la session
            session['jwt_token'] = jwt_token
            session['user_info'] = user_info

            # Rediriger vers GraphiQL ou la page demandée initialement
            next_page = session.pop('next', '/graphiql')
            return redirect(next_page)

        return jsonify({'error': 'Authentication failed'}), 401
    except Exception as e:
        return jsonify({'error': f'Authentication error: {str(e)}'}), 401


@app.route('/logout')
def logout():
    """Déconnexion"""
    session.clear()
    return redirect('/')


@app.route('/graphql', methods=['POST'])
@require_auth
def graphql_endpoint():
    """Endpoint GraphQL principal (mode synchrone)"""
    # Vérifier l'authentification (session ou token Bearer)
    jwt_token = None

    # Priorité 1: Token Bearer dans le header (pour les appels API)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        jwt_token = auth_header.split(' ')[1]

    # Priorité 2: Session (pour GraphiQL)
    elif 'jwt_token' in session:
        jwt_token = session['jwt_token']

    # Si pas de token trouvé
    if not jwt_token:
        return jsonify({'error': 'Missing or invalid authorization'}), 401

    # Vérifier le token
    payload = verify_jwt(jwt_token)
    if not payload:
        return jsonify({'error': 'Invalid or expired token'}), 401

    data = request.get_json()
    query = data.get('query')
    variables = data.get('variables', {})
    use_cache = data.get('use_cache', False)

    # En mode synchrone, on retourne directement le résultat
    # (À implémenter avec votre schéma GraphQL réel)
    result = schema.execute(
        query,
        variables=variables,
        operation_name=POST,
        context_value={'user': payload['user']}
    )

    response_data = {'data': result.data}
    if result.errors:
        response_data['errors'] = [str(e) for e in result.errors]

    return jsonify(response_data)


@app.route('/graphql/async', methods=['POST'])
def graphql_async_endpoint():
    """Endpoint GraphQL en mode asynchrone"""
    # Vérifier l'authentification (session ou token Bearer)
    jwt_token = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        jwt_token = auth_header.split(' ')[1]
    elif 'jwt_token' in session:
        jwt_token = session['jwt_token']

    if not jwt_token:
        return jsonify({'error': 'Missing or invalid authorization'}), 401

    payload = verify_jwt(jwt_token)
    if not payload:
        return jsonify({'error': 'Invalid or expired token'}), 401

    data = request.get_json()
    query = data.get('query')
    variables = data.get('variables', {})

    # Créer un job ID
    job_id = hashlib.sha256(f"{query}{datetime.utcnow()}".encode()).hexdigest()

    # Lancer l'exécution en arrière-plan
    async_jobs[job_id] = {'status': 'running'}
    thread = threading.Thread(
        target=execute_async_query,
        args=(job_id, query, variables)
    )
    thread.start()

    return jsonify({
        'job_id': job_id,
        'status_url': f'/graphql/async/status/{job_id}',
        'result_url': f'/graphql/async/result/{job_id}'
    })


@app.route('/graphql/async/status/<job_id>')
def async_status(job_id):
    """Vérifie le statut d'une requête asynchrone"""
    # Vérifier l'authentification
    jwt_token = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        jwt_token = auth_header.split(' ')[1]
    elif 'jwt_token' in session:
        jwt_token = session['jwt_token']

    if not jwt_token or not verify_jwt(jwt_token):
        return jsonify({'error': 'Missing or invalid authorization'}), 401

    if job_id not in async_jobs:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(async_jobs[job_id])


@app.route('/graphql/async/result/<job_id>')
def async_result(job_id):
    """Récupère le résultat d'une requête asynchrone"""
    # Vérifier l'authentification
    jwt_token = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        jwt_token = auth_header.split(' ')[1]
    elif 'jwt_token' in session:
        jwt_token = session['jwt_token']

    if not jwt_token or not verify_jwt(jwt_token):
        return jsonify({'error': 'Missing or invalid authorization'}), 401

    if job_id not in async_jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = async_jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed', 'status': job['status']}), 400

    with open(job['result_file'], 'r') as f:
        result = json.load(f)

    return jsonify(result)


@app.route('/schema/refresh', methods=['POST'])
@require_auth
def refresh_schema():
    """Régénère le schéma GraphQL"""
    schema = generate_graphql_schema()
    save_schema_cache(schema)
    return jsonify({'message': 'Schema refreshed successfully'})


@app.route('/cache/clear', methods=['POST'])
@require_auth
def clear_cache():
    """Vide le cache des requêtes"""
    import shutil
    shutil.rmtree(CONFIG['QUERY_CACHE_DIR'])
    os.makedirs(CONFIG['QUERY_CACHE_DIR'])
    return jsonify({'message': 'Cache cleared successfully'})


@app.route('/graphiql')
def graphiql():
    """Interface GraphiQL avec authentification"""
    # Vérifier si l'utilisateur est authentifié via session
    if 'jwt_token' not in session:
        # Sauvegarder la page demandée pour y revenir après login
        session['next'] = '/graphiql'
        return redirect('/login')

    jwt_token = session['jwt_token']
    user_info = session.get('user_info', {})

    # Servir l'interface GraphiQL avec le token intégré
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>GraphiQL - API GraphQL-SPARQL</title>
          <link href="https://unpkg.com/graphiql@2.4.7/graphiql.min.css" rel="stylesheet" />
          <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
            }}
            #header {{
                background: #2c3e50;
                color: white;
                padding: 10px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            #user-info {{
                display: flex;
                align-items: center;
                gap: 15px;
            }}
            #logout-btn {{
                background: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
            }}
            #logout-btn:hover {{
                background: #c0392b;
            }}
            #graphiql {{
                height: calc(100vh - 50px);
            }}
        </style>
    </head>
    <body>
        <div id="header">
            <h2 style="margin: 0;">GraphiQL Interface</h2>
            <div id="user-info">
                <span>👤 {user_info.get('name', 'User')}</span>
                <span>({user_info.get('email', '')})</span>
                <button id="logout-btn" onclick="logout()">Déconnexion</button>
            </div>
        </div>
        <div id="graphiql"></div>

        <script crossorigin src="https://unpkg.com/react@17.0.2/umd/react.production.min.js"></script>
        <script crossorigin src="https://unpkg.com/react-dom@17.0.2/umd/react-dom.production.min.js"></script>
        <script crossorigin src="https://unpkg.com/graphiql@2.4.7/graphiql.min.js"></script>
            <script>
            // Stocker le token pour les requêtes
            const jwtToken = '{jwt_token}';

            // Configurer le fetcher avec le token
            const fetcher = GraphiQL.createFetcher({{
                url: '/graphql',
                headers: {{
                    'Authorization': 'Bearer ' + jwtToken
                }}
            }});

            // Rendre GraphiQL
            ReactDOM.render(
                React.createElement(GraphiQL, {{ 
                    fetcher: fetcher,
                    defaultQuery: `# Bienvenue dans GraphiQL!
# Voici quelques exemples de requêtes:

# Exemple 1: Récupérer une peinture
# query {{
#   getPainting(id: "http://example.org/painting/1") {{
#     id
#     title
#   }}
# }}

# Exemple 2: Liste de toutes les peintures
# query {{
#   allPaintings {{
#     id
#     title
#   }}
# }}

# Exemple 3: Créer une nouvelle peinture
# mutation {{
#   createPainting(
#     id: "http://example.org/painting/new"
#     data: "{{\\\\"title\\\\": \\\\"Mon œuvre\\\\"}}"
#   ) {{
#     success
#     entity
#   }}
# }}
`
                }}),
                document.getElementById('graphiql')
            );

            function logout() {{
                if (confirm('Êtes-vous sûr de vouloir vous déconnecter ?')) {{
                    window.location.href = '/logout';
                }}
            }}
        </script>
    </body>
    </html>
    '''


@app.route('/')
def home():
    """Page d'accueil"""
    is_authenticated = 'jwt_token' in session
    user_info = session.get('user_info', {}) if is_authenticated else None

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>API GraphQL-SPARQL</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                max-width: 600px;
            }}
            h1 {{
                margin-bottom: 20px;
                font-size: 2.5em;
            }}
            p {{
                font-size: 1.2em;
                margin-bottom: 30px;
            }}
            .btn {{
                display: inline-block;
                padding: 15px 30px;
                margin: 10px;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 50px;
                font-weight: bold;
                transition: all 0.3s;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
            }}
            .user-badge {{
                background: rgba(255, 255, 255, 0.2);
                padding: 15px 25px;
                border-radius: 10px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 API GraphQL-SPARQL</h1>
            <p>Interrogez et modifiez vos données RDF via GraphQL</p>

            {"<div class='user-badge'>👤 Connecté en tant que <strong>" + user_info.get('name', '') + "</strong></div>" if is_authenticated else ""}

            <div>
                {"<a href='/graphiql' class='btn'>🎨 Ouvrir GraphiQL</a>" if is_authenticated else "<a href='/login' class='btn'>🔐 Se connecter avec Google</a>"}
                <a href='/docs' class='btn'>📚 Documentation</a>
                {"<a href='/logout' class='btn'>🚪 Déconnexion</a>" if is_authenticated else ""}
            </div>

            {"<p style='margin-top: 30px; font-size: 0.9em;'>Token JWT disponible pour les appels d'API</p>" if is_authenticated else ""}
        </div>
    </body>
    </html>
    '''


@app.route('/token')
def get_token():
    """Endpoint pour récupérer le token JWT (pour usage API)"""
    if 'jwt_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    return jsonify({
        'token': session['jwt_token'],
        'user': session.get('user_info', {})
    })


# ============================================================================
# EXEMPLES D'UTILISATION
# ============================================================================

def example_synchronous():
    """Exemple d'utilisation synchrone"""
    import requests

    # 1. Authentification
    response = requests.post('http://localhost:5000/login')
    # Après le flux OAuth, vous obtenez un token
    token = "votre-jwt-token"

    # 2. Requête GraphQL synchrone
    query = """
    query {
        Painting(id: "http://example.org/painting/1") {
            id
            title
            artist {
                id
                name
            }
        }
    }
    """

    response = requests.post(
        'http://localhost:5000/graphql',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'query': query,
            'use_cache': True
        }
    )

    result = response.json()
    print("Résultat synchrone:", result)

    # 3. Mutation (création/modification)
    mutation = """
    mutation {
        createPainting(
            id: "http://example.org/painting/new",
            data: "{\"title\": \"La Joconde\", \"artist\": \"http://example.org/artist/davinci\"}"
        ) {
            success
            entity
        }
    }
    """

    response = requests.post(
        'http://localhost:5000/graphql',
        headers={'Authorization': f'Bearer {token}'},
        json={'query': mutation}
    )

    print("Résultat mutation:", response.json())


def example_asynchronous():
    """Exemple d'utilisation asynchrone"""
    import requests
    import time

    token = "votre-jwt-token"

    # 1. Lancer une requête asynchrone
    query = """
    query {
        allPaintings {
            id
            title
        }
    }
    """

    response = requests.post(
        'http://localhost:5000/graphql/async',
        headers={'Authorization': f'Bearer {token}'},
        json={'query': query}
    )

    job_info = response.json()
    job_id = job_info['job_id']
    print(f"Job créé: {job_id}")

    # 2. Vérifier le statut périodiquement
    while True:
        status_response = requests.get(
            f'http://localhost:5000/graphql/async/status/{job_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        status = status_response.json()
        print(f"Statut: {status['status']}")

        if status['status'] == 'completed':
            break
        elif status['status'] == 'failed':
            print(f"Erreur: {status['error']}")
            return

        time.sleep(1)

    # 3. Récupérer le résultat
    result_response = requests.get(
        f'http://localhost:5000/graphql/async/result/{job_id}',
        headers={'Authorization': f'Bearer {token}'}
    )

    result = result_response.json()
    print("Résultat asynchrone:", result)


# ============================================================================
# CONSTRUCTION COMPLÈTE DU SCHÉMA GRAPHQL
# ============================================================================

def build_complete_graphql_schema():
    """Construit le schéma GraphQL complet avec Query et Mutation"""

    # Charger le schéma depuis le cache
    schema_cache = load_schema_cache()
    merged_schema = merge_schema_definitions(
        schema_cache['auto_generated'],
        schema_cache['manual']
    )

    # Construire les types GraphQL
    graphql_types = build_graphql_types(merged_schema)

    # Construire la classe Query dynamiquement
    query_fields = {}
    mutation_fields = {}

    for type_uri, type_info in merged_schema.items():
        type_name = sanitize_name(type_info['label'])

        if type_name not in graphql_types:
            continue

        graphql_type = graphql_types[type_name]

        # Ajouter les champs de requête
        # 1. Requête pour un seul objet par ID
        query_fields[f'get{type_name}'] = Field(
            graphql_type,
            id=String(required=True),
            use_cache=graphene.Boolean(default_value=False),
            resolver=create_resolver(type_name, type_uri)
        )

        # 2. Requête pour tous les objets du type
        query_fields[f'all{type_name}s'] = Field(
            GList(graphql_type),
            use_cache=graphene.Boolean(default_value=False),
            resolver=create_resolver(type_name, type_uri)
        )

        # Ajouter la mutation
        mutation_class = create_mutation(type_name, type_uri)
        mutation_fields[f'create{type_name}'] = mutation_class.Field()

    # Créer les classes Query et Mutation dynamiquement
    Query = type('Query', (ObjectType,), query_fields)
    Mutations = type('Mutations', (ObjectType,), mutation_fields)

    # Créer le schéma
    schema = Schema(query=Query, mutation=Mutations)

    return schema


# Variable globale pour le schéma GraphQL
graphql_schema = None


def get_graphql_schema():
    """Récupère ou construit le schéma GraphQL"""
    global graphql_schema
    if graphql_schema is None:
        graphql_schema = build_complete_graphql_schema()
    return graphql_schema


# ============================================================================
# RÉSOLVEURS AMÉLIORÉS AVEC SOUS-OBJETS
# ============================================================================

def resolve_subobject(uri: str, requested_fields: List[str]) -> Dict[str, Any]:
    """Résout un sous-objet référencé avec les champs demandés"""

    # Déterminer le type de l'objet référencé
    type_query = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

    SELECT ?type WHERE {{
        {{
            <{uri}> wdt:P31 ?type .
        }} UNION {{
            <{uri}> rdf:type ?type .
        }}
    }}
    LIMIT 1
    """

    type_results = sparql_client.query(type_query)
    if not type_results:
        return {'id': uri}

    type_uri = type_results[0]['type']

    # Récupérer les propriétés demandées
    properties_filter = ""
    if requested_fields:
        fields_uri = [f"<{field}>" for field in requested_fields if field.startswith('http')]
        if fields_uri:
            properties_filter = f"FILTER(?property IN ({', '.join(fields_uri)}))"

    data_query = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?property ?value ?label WHERE {{
        <{uri}> ?property ?value .
        OPTIONAL {{ ?property rdfs:label ?label }}
        {properties_filter}
    }}
    """

    results = sparql_client.query(data_query)

    obj = {'id': uri}
    for result in results:
        prop_label = result.get('label', result['property'].split('/')[-1])
        prop_name = sanitize_name(prop_label)
        obj[prop_name] = result['value']

    return obj


def create_advanced_resolver(type_name: str, type_uri: str, single: bool = True):
    """Crée un résolveur avancé qui gère les sous-objets"""

    def resolver(root, info, id=None, use_cache=False):
        """Résolveur avec support des sous-objets"""

        # Analyser les champs demandés dans la requête GraphQL
        selection_set = info.field_nodes[0].selection_set
        requested_fields = {}

        if selection_set:
            for selection in selection_set.selections:
                field_name = selection.name.value
                # Si le champ a des sous-sélections, c'est un objet référencé
                if selection.selection_set:
                    subfields = [s.name.value for s in selection.selection_set.selections]
                    requested_fields[field_name] = subfields
                else:
                    requested_fields[field_name] = None

        if single and id:
            # Requête pour un objet spécifique
            query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?property ?value ?propertyLabel WHERE {{
                {{
                    <{id}> wdt:P31 <{type_uri}> .
                    <{id}> ?property ?value .
                }} UNION {{
                    <{id}> rdf:type <{type_uri}> .
                    <{id}> ?property ?value .
                }}
                OPTIONAL {{ ?property rdfs:label ?propertyLabel }}
            }}
            """

            results = sparql_client.query(query, use_cache=use_cache)

            obj = {'id': id}
            for result in results:
                prop_label = result.get('propertyLabel', result['property'].split('/')[-1])
                prop_name = sanitize_name(prop_label)
                value = result['value']

                # Si c'est une URI et que des sous-champs sont demandés, résoudre le sous-objet
                if value.startswith('http') and prop_name in requested_fields and requested_fields[prop_name]:
                    obj[prop_name] = resolve_subobject(value, requested_fields[prop_name])
                else:
                    obj[prop_name] = value

            return obj
        else:
            # Requête pour tous les objets du type
            query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX wdt: <http://www.wikidata.org/prop/direct/>

            SELECT DISTINCT ?instance WHERE {{
                {{
                    ?instance wdt:P31 <{type_uri}> .
                }} UNION {{
                    ?instance rdf:type <{type_uri}> .
                }}
            }}
            LIMIT 100
            """

            results = sparql_client.query(query, use_cache=use_cache)

            objects = []
            for result in results:
                instance_id = result['instance']
                # Pour chaque instance, récupérer les données si nécessaire
                if requested_fields:
                    obj = resolver(root, info, id=instance_id, use_cache=use_cache)
                    objects.append(obj)
                else:
                    objects.append({'id': instance_id})

            return objects

    return resolver


# ============================================================================
# MUTATIONS AVANCÉES
# ============================================================================

def create_advanced_mutation(type_name: str, type_uri: str):
    """Crée une mutation avancée avec support des relations"""

    class AdvancedMutation(Mutation):
        class Arguments:
            id = String(required=True, description="URI de l'entité")
            data = String(required=True, description="Données JSON de l'entité")
            replace = graphene.Boolean(default_value=False, description="Remplacer ou fusionner")

        success = Field(String)
        entity = Field(String)
        created = Field(graphene.Boolean)

        def mutate(root, info, id, data, replace=False):
            """Effectue la mutation avec gestion des relations"""
            try:
                data_dict = json.loads(data)
                graph = get_graph_for_type(type_name, type_uri)

                # Vérifier si l'entité existe déjà
                check_query = f"""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                PREFIX wdt: <http://www.wikidata.org/prop/direct/>

                ASK WHERE {{
                    {{
                        <{id}> wdt:P31 <{type_uri}> .
                    }} UNION {{
                        <{id}> rdf:type <{type_uri}> .
                    }}
                }}
                """

                sparql = SPARQLWrapper(CONFIG['SPARQL_ENDPOINT'])
                sparql.setQuery(check_query)
                sparql.setReturnFormat(JSON)
                exists = sparql.query().convert()['boolean']

                # Si replace=True et que l'entité existe, la supprimer d'abord
                if replace and exists:
                    delete_query = f"""
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                    DELETE WHERE {{
                        GRAPH <{graph}> {{
                            <{id}> ?p ?o .
                        }}
                    }}
                    """
                    sparql_client.update(delete_query)

                # Construire les triples à insérer
                triples = []
                triples.append(f"<{id}> rdf:type <{type_uri}> .")

                # Charger le schéma pour déterminer les types de propriétés
                schema_cache = load_schema_cache()
                merged_schema = merge_schema_definitions(
                    schema_cache['auto_generated'],
                    schema_cache['manual']
                )

                type_info = merged_schema.get(type_uri, {})
                properties_info = type_info.get('properties', {})

                for prop, value in data_dict.items():
                    # Trouver l'URI de la propriété
                    prop_uri = None
                    for p_uri, p_info in properties_info.items():
                        if sanitize_name(p_info['label']) == prop:
                            prop_uri = p_uri
                            break

                    if not prop_uri:
                        # Propriété inconnue, utiliser un namespace par défaut
                        prop_uri = f"http://example.org/prop/{prop}"

                    # Déterminer si c'est une référence ou un littéral
                    if isinstance(value, str) and value.startswith('http'):
                        # C'est une référence à un autre objet
                        triples.append(f"<{id}> <{prop_uri}> <{value}> .")
                    elif isinstance(value, bool):
                        triples.append(
                            f'<{id}> <{prop_uri}> "{str(value).lower()}"^^<http://www.w3.org/2001/XMLSchema#boolean> .')
                    elif isinstance(value, int):
                        triples.append(f'<{id}> <{prop_uri}> "{value}"^^<http://www.w3.org/2001/XMLSchema#integer> .')
                    elif isinstance(value, float):
                        triples.append(f'<{id}> <{prop_uri}> "{value}"^^<http://www.w3.org/2001/XMLSchema#double> .')
                    else:
                        # Littéral string
                        escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                        triples.append(f'<{id}> <{prop_uri}> "{escaped_value}" .')

                # Insérer les données
                insert_query = f"""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                INSERT DATA {{
                    GRAPH <{graph}> {{
                        {' '.join(triples)}
                    }}
                }}
                """

                sparql_client.update(insert_query)

                return AdvancedMutation(
                    success="Entity created/updated successfully",
                    entity=id,
                    created=not exists
                )
            except Exception as e:
                raise GraphQLError(f"Mutation failed: {str(e)}")

    return AdvancedMutation


# ============================================================================
# MUTATION DE SUPPRESSION
# ============================================================================

def create_delete_mutation(type_name: str, type_uri: str):
    """Crée une mutation de suppression pour un type"""

    class DeleteMutation(Mutation):
        class Arguments:
            id = String(required=True, description="URI de l'entité à supprimer")

        success = Field(String)
        deleted_id = Field(String)

        def mutate(root, info, id):
            """Supprime une entité du graphe"""
            try:
                graph = get_graph_for_type(type_name, type_uri)

                # Supprimer tous les triples où l'entité est sujet
                delete_query = f"""
                DELETE WHERE {{
                    GRAPH <{graph}> {{
                        <{id}> ?p ?o .
                    }}
                }}
                """

                sparql_client.update(delete_query)

                return DeleteMutation(
                    success="Entity deleted successfully",
                    deleted_id=id
                )
            except Exception as e:
                raise GraphQLError(f"Delete failed: {str(e)}")

    return DeleteMutation


# ============================================================================
# ENDPOINTS FLASK AMÉLIORÉS
# ============================================================================

@app.route('/graphql', methods=['POST', 'GET'])
def graphql_endpoint_improved():
    """Endpoint GraphQL principal avec support complet"""

    # Vérifier l'authentification (session ou token Bearer)
    jwt_token = None

    # Priorité 1: Token Bearer dans le header (pour les appels API)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        jwt_token = auth_header.split(' ')[1]

    # Priorité 2: Session (pour GraphiQL)
    elif 'jwt_token' in session:
        jwt_token = session['jwt_token']

    # Si pas de token trouvé
    if not jwt_token:
        return jsonify({'error': 'Missing or invalid authorization'}), 401

    # Vérifier le token
    payload = verify_jwt(jwt_token)
    if not payload:
        return jsonify({'error': 'Invalid or expired token'}), 401

    # Récupérer le schéma GraphQL
    schema = get_graphql_schema()

    # Traiter la requête
    if request.method == 'POST':
        data = request.get_json()
        query = data.get('query')
        variables = data.get('variables', {})
        operation_name = data.get('operationName')
    else:
        query = request.args.get('query')
        variables = {}
        operation_name = None

    # Exécuter la requête
    result = schema.execute(
        query,
        variables=variables,
        operation_name=operation_name,
        context_value={'user': payload['user']}
    )

    response_data = {'data': result.data}
    if result.errors:
        response_data['errors'] = [str(e) for e in result.errors]

    return jsonify(response_data)


# ============================================================================
# CONFIGURATION ET DOCUMENTATION
# ============================================================================

@app.route('/config', methods=['GET', 'POST'])
@require_auth
def manage_config():
    """Gère la configuration du serveur"""

    if request.method == 'GET':
        # Retourner la configuration (sans les secrets)
        safe_config = CONFIG.copy()
        safe_config.pop('JWT_SECRET', None)
        safe_config.pop('GOOGLE_CLIENT_SECRET', None)
        return jsonify(safe_config)

    elif request.method == 'POST':
        # Mettre à jour la configuration
        data = request.get_json()
        for key, value in data.items():
            if key in CONFIG and key not in ['JWT_SECRET', 'GOOGLE_CLIENT_SECRET']:
                CONFIG[key] = value

        return jsonify({'message': 'Configuration updated'})


@app.route('/docs')
def documentation():
    """Documentation de l'API"""
    docs = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API GraphQL-SPARQL Documentation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            h1, h2, h3 { color: #333; }
            code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
            pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
            .endpoint { background: #e8f5e9; padding: 10px; margin: 10px 0; border-left: 4px solid #4caf50; }
        </style>
    </head>
    <body>
        <h1>API GraphQL-SPARQL - Documentation</h1>

        <h2>Vue d'ensemble</h2>
        <p>Cette API permet d'interroger et de modifier des données RDF via GraphQL.</p>

        <h2>Authentification</h2>
        <p>Toutes les requêtes nécessitent un token JWT dans le header Authorization:</p>
        <pre>Authorization: Bearer &lt;your-jwt-token&gt;</pre>

        <h3>Obtenir un token</h3>
        <div class="endpoint">
            <strong>GET</strong> /login<br>
            Initie le flux OAuth Google
        </div>

        <h2>Endpoints</h2>

        <div class="endpoint">
            <strong>POST</strong> /graphql<br>
            Endpoint GraphQL principal (mode synchrone)<br>
            Body: <code>{"query": "...", "variables": {...}, "use_cache": false}</code>
        </div>

        <div class="endpoint">
            <strong>POST</strong> /graphql/async<br>
            Endpoint GraphQL asynchrone<br>
            Retourne un job_id pour suivre l'exécution
        </div>

        <div class="endpoint">
            <strong>GET</strong> /graphql/async/status/&lt;job_id&gt;<br>
            Vérifie le statut d'une requête asynchrone
        </div>

        <div class="endpoint">
            <strong>GET</strong> /graphql/async/result/&lt;job_id&gt;<br>
            Récupère le résultat d'une requête asynchrone terminée
        </div>

        <div class="endpoint">
            <strong>POST</strong> /schema/refresh<br>
            Régénère le schéma GraphQL à partir du graphe RDF
        </div>

        <div class="endpoint">
            <strong>POST</strong> /cache/clear<br>
            Vide le cache des requêtes
        </div>

        <h2>Exemples de requêtes GraphQL</h2>

        <h3>Lecture simple</h3>
        <pre>
query {
  getPainting(id: "http://example.org/painting/1") {
    id
    title
    creationDate
  }
}
        </pre>

        <h3>Lecture avec sous-objets</h3>
        <pre>
query {
  getPainting(id: "http://example.org/painting/1") {
    id
    title
    artist {
      id
      name
      birthDate
    }
  }
}
        </pre>

        <h3>Mutation (création/modification)</h3>
        <pre>
mutation {
  createPainting(
    id: "http://example.org/painting/new"
    data: "{\\"title\\": \\"Mona Lisa\\", \\"artist\\": \\"http://example.org/artist/davinci\\"}"
  ) {
    success
    entity
    created
  }
}
        </pre>

        <h3>Suppression</h3>
        <pre>
mutation {
  deletePainting(id: "http://example.org/painting/old") {
    success
    deleted_id
  }
}
        </pre>

        <h2>Cache</h2>
        <p>Le cache peut être activé par requête avec le paramètre <code>use_cache: true</code></p>

        <h2>Mode asynchrone</h2>
        <p>Pour les requêtes longues, utilisez l'endpoint /graphql/async qui retourne immédiatement un job_id.</p>
    </body>
    </html>
    """
    return docs


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Charger ou générer le schéma au démarrage
    if not os.path.exists(CONFIG['SCHEMA_CACHE_FILE']):
        print("Génération du schéma initial...")
        schema = generate_graphql_schema()
        save_schema_cache(schema)
        print(f"Schéma généré avec {len(schema['auto_generated'])} types")
    else:
        print("Chargement du schéma depuis le cache...")
        schema = load_schema_cache()
        print(f"Schéma chargé avec {len(schema['auto_generated'])} types auto + {len(schema['manual'])} types manuels")

    # Construire le schéma GraphQL
    print("Construction du schéma GraphQL...")
    graphql_schema = build_complete_graphql_schema()

    print("\n" + "=" * 60)
    print("Serveur démarré sur http://localhost:5000")
    print("=" * 60)
    print("GraphiQL:      http://localhost:5000/graphiql")
    print("Documentation: http://localhost:5000/docs")
    print("Login OAuth:   http://localhost:5000/login")
    print("=" * 60 + "\n")

    app.run(debug=False, port=5000, threaded=True)
