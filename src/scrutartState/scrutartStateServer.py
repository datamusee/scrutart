from flask import Flask, request, jsonify
from rdflib import Graph
from rdflib.plugins.sparql.processor import SPARQLResult
import os
import json
import time
import threading

app = Flask(__name__)


# Dossiers pour les fichiers TTL et JSON
TTL_DIRECTORY = 'ttl_files'      # Dossier contenant les fichiers TTL
USER_DIRECTORY = 'users'         # Dossier contenant les fichiers JSON des utilisateurs

# Initialise le graphe RDF
graph = Graph()

# Ensemble des Tokens autorisés
AUTHORIZED_TOKENS = set()

# Garde une trace des fichiers TTL déjà chargés
loaded_files = set()

def load_ttl_files(directory):
    """Charge les nouveaux fichiers .ttl depuis le dossier spécifié."""
    if not os.path.exists(directory):
        print(f"Erreur : le dossier '{directory}' n'existe pas.")
        return

    ttl_files = [f for f in os.listdir(directory) if f.endswith('.ttl')]

    for ttl_file in ttl_files:
        file_path = os.path.join(directory, ttl_file)
        if file_path not in loaded_files:
            try:
                graph.parse(file_path, format='ttl')
                loaded_files.add(file_path)
                print(f"Fichier TTL '{ttl_file}' chargé avec succès.")
            except Exception as e:
                print(f"Erreur lors du chargement du fichier '{ttl_file}' : {e}")

def load_user_tokens(directory):
    """Charge les Tokens des utilisateurs depuis les fichiers JSON."""
    if not os.path.exists(directory):
        print(f"Erreur : le dossier '{directory}' n'existe pas.")
        return

    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]

    for json_file in json_files:
        file_path = os.path.join(directory, json_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
                tokens = user_data.get("tokens", [])
                for token in tokens:
                    AUTHORIZED_TOKENS.add(token)
                print(f"Tokens de l'utilisateur '{user_data.get('email', 'inconnu')}' chargés avec succès.")
        except Exception as e:
            print(f"Erreur lors du chargement du fichier '{json_file}' : {e}")

def periodic_loader(interval=600):
    """Vérifie périodiquement le dossier pour de nouveaux fichiers TTL."""
    while True:
        load_ttl_files(TTL_DIRECTORY)
        time.sleep(interval)

# Charger les fichiers TTL et les Tokens des utilisateurs au démarrage du serveur
load_ttl_files(TTL_DIRECTORY)
load_user_tokens(USER_DIRECTORY)

# Démarre le thread pour le chargement périodique des fichiers TTL
loader_thread = threading.Thread(target=periodic_loader, args=(600,), daemon=True)
loader_thread.start()

@app.route('/')
def home():
    return "API Flask sécurisée pour exécuter des requêtes SPARQL sur le graphe RDF qui décrit l'état du projet Scrutart."

def check_token():
    """Vérifie le token d'authentification dans l'en-tête Authorization."""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False
    token = auth_header.replace('Bearer ', '')
    return token in AUTHORIZED_TOKENS

@app.route('/query', methods=['POST'])
def sparql_query():
    """
    Point d'entrée pour exécuter une requête SPARQL sur le graphe RDF.
    La requête doit être envoyée en POST avec un JSON : {"query": "votre requête sparql"}
    et un header Authorization : Bearer <token>.
    """
    # Vérifie si le token est valide
    if not check_token():
        return jsonify({"error": "Accès non autorisé. Token invalide ou manquant."}), 401

    try:
        # Récupère la requête SPARQL depuis le JSON de la requête
        data = request.get_json()
        sparql_query = data.get('query')

        if not sparql_query:
            return jsonify({"error": "Aucune requête SPARQL fournie"}), 400

        # Exécute la requête SPARQL sur le graphe
        results: SPARQLResult = graph.query(sparql_query)

        # Convertit les résultats en format lisible (liste de dictionnaires)
        result_list = []
        for row in results:
            result_list.append({str(var): str(row[var]) for var in row.labels})

        return jsonify({"results": result_list})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update', methods=['POST'])
def sparql_update():
    """
    Point d'entrée pour effectuer des mises à jour SPARQL sur le graphe RDF.
    La requête doit être envoyée en POST avec un JSON : {"update": "votre requête d'update sparql"}
    et un header Authorization : Bearer <token>.
    """
    # Vérifie si le token est valide
    if not check_token():
        return jsonify({"error": "Accès non autorisé. Token invalide ou manquant."}), 401

    try:
        # Récupère la requête SPARQL d'update depuis le JSON de la requête
        data = request.get_json()
        sparql_update_query = data.get('update')

        if not sparql_update_query:
            return jsonify({"error": "Aucune requête SPARQL d'update fournie"}), 400

        # Exécute la requête SPARQL d'update sur le graphe
        graph.update(sparql_update_query)

        # Sauvegarde la requête d'update dans un fichier
        with open('updates_log.txt', 'a', encoding='utf-8') as log_file:
            log_file.write(sparql_update_query + '\n')

        return jsonify({"message": "Mise à jour effectuée et sauvegardée avec succès."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/describe', methods=['POST'])
def sparql_describe():
    """
    Point d'entrée pour exécuter une requête SPARQL DESCRIBE sur le graphe RDF.
    La requête doit être envoyée en POST avec un JSON : {"query": "DESCRIBE <votre_entité>"}
    et un header Authorization : Bearer <token>.
    """
    # Vérifie si le token est valide
    if not check_token():
        return jsonify({"error": "Accès non autorisé. Token invalide ou manquant."}), 401

    try:
        # Récupère la requête SPARQL DESCRIBE depuis le JSON de la requête
        data = request.get_json()
        describe_query = data.get('query')

        if not describe_query:
            return jsonify({"error": "Aucune requête SPARQL DESCRIBE fournie"}), 400

        # Exécute la requête SPARQL DESCRIBE sur le graphe
        results = graph.query(describe_query)

        # Sérialise les résultats en JSON-LD
        json_ld_result = graph.serialize(format='json-ld')

        # Sauvegarde la requête dans le fichier de log
        with open('updates_log.txt', 'a', encoding='utf-8') as log_file:
            log_file.write(describe_query + '\n')

        return jsonify(json.loads(json_ld_result))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/construct', methods=['POST'])
def sparql_construct():
    """
    Point d'entrée pour exécuter une requête SPARQL CONSTRUCT sur le graphe RDF.
    La requête doit être envoyée en POST avec un JSON : {"query": "CONSTRUCT { ... } WHERE { ... }"}
    et un header Authorization : Bearer <token>.
    """
    # Vérifie si le token est valide
    if not check_token():
        return jsonify({"error": "Accès non autorisé. Token invalide ou manquant."}), 401

    try:
        # Récupère la requête SPARQL CONSTRUCT depuis le JSON de la requête
        data = request.get_json()
        construct_query = data.get('query')

        if not construct_query:
            return jsonify({"error": "Aucune requête SPARQL CONSTRUCT fournie"}), 400

        # Exécute la requête SPARQL CONSTRUCT sur le graphe
        construct_graph = graph.query(construct_query)

        # Sérialise les résultats en JSON-LD
        json_ld_result = construct_graph.serialize(format='json-ld')

        # Sauvegarde la requête dans le fichier de log
        with open('updates_log.txt', 'a', encoding='utf-8') as log_file:
            log_file.write(construct_query + '\n')

        return jsonify(json.loads(json_ld_result))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False)
