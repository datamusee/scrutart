import re
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import requests
import threading
import time
from datetime import datetime, timedelta
import secrets
import json
from functools import wraps
import os
from dotenv import load_dotenv
from src.piwigoTools.CPiwigoManager import CPiwigoManager, CategoryType
from src.generationWordpress.generationListeImagesPourArtiste import genereListeImages

# DIAGNOSTIC - Ajoutez ce code temporairement
print("🔍 DIAGNOSTIC DES VARIABLES D'ENVIRONNEMENT")
print("=" * 50)

# Vérifier si le fichier .env existe
env_file_path = os.path.join(os.getcwd(), '.env')
print(f"📁 Répertoire de travail : {os.getcwd()}")
print(f"📄 Fichier .env existe : {os.path.exists(env_file_path)}")

if os.path.exists(env_file_path):
    with open(env_file_path, 'r') as f:
        content = f.read()
        print(f"📝 Contenu du fichier .env :")
        for line in content.split('\n'):
            if line.strip() and not line.startswith('#'):
                key = line.split('=')[0] if '=' in line else line
                print(f"   {key}=***")

# Charger les variables d'environnement
print("\n🔧 Chargement du fichier .env...")
load_result = load_dotenv()
print(f"✅ Fichier .env chargé : {load_result}")

# Vérifier les variables après chargement
print(f"\n📋 Variables après chargement :")
print(f"   SECRET_KEY: {'***DÉFINI***' if os.environ.get('SECRET_KEY') else '❌ NON DÉFINI'}")
print(f"   GOOGLE_CLIENT_ID: {os.environ.get('GOOGLE_CLIENT_ID', '❌ NON DÉFINI')}")
print(f"   GOOGLE_CLIENT_SECRET: {'***DÉFINI***' if os.environ.get('GOOGLE_CLIENT_SECRET') else '❌ NON DÉFINI'}")
print("=" * 50)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-change-this')

# Configuration OAuth Google
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

# Plus de diagnostic
print(f"\n🔑 Configuration Flask :")
print(f"   app.secret_key: {'***CONFIGURÉ***' if app.secret_key != 'default-secret-key-change-this' else '❌ DÉFAUT'}")
print(f"   GOOGLE_CLIENT_ID configuré: {'OUI' if app.config['GOOGLE_CLIENT_ID'] else 'NON'}")
print(f"   GOOGLE_CLIENT_SECRET configuré: {'OUI' if app.config['GOOGLE_CLIENT_SECRET'] else 'NON'}")
print("=" * 50)

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

# Configuration OAuth Google
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

# Configuration OAuth manuelle (sans Authlib pour éviter les problèmes)
GOOGLE_DISCOVERY_URL = "https://accounts.google.com"
GOOGLE_CLIENT_ID = app.config['GOOGLE_CLIENT_ID']
GOOGLE_CLIENT_SECRET = app.config['GOOGLE_CLIENT_SECRET']

# Dictionnaires pour stocker les données
tasks = {}
api_tokens = {}
users = {}

# Génération d'un token API par défaut (à supprimer en production)
default_token = secrets.token_urlsafe(32)
api_tokens[default_token] = {
    'user': 'admin',
    'created_at': datetime.now(),
    'expires_at': datetime.now() + timedelta(days=30)
}
print(f"Token API par défaut: {default_token}")

def getCategoriesDict(pwg):
    existingCategories = {}
    res = pwg.piwigo_get_categories()
    if res and ("stat" in res) and (res["stat"] == "ok") and (
            "result" in res):
        for cat in res["result"]:
            label = cat[
                "name"].strip().lower()  # strip ' ' de début et de fin, et minuscules pour variations écriture noms propres
            existingCategories[label] = cat
            if "sub_categories" in cat:
                for subcat in cat["sub_categories"]:
                    label = subcat[
                        "name"].strip().lower()  # strip ' ' de début et de fin, et minuscules pour variations écriture noms propres
                    existingCategories[label] = subcat
    return existingCategories

def buildPage(qid, label, uri, task_id):
    """
    Fonction qui construit le contenu de la page basé sur l'entité Wikidata
    Simule un traitement long
    """
    try:
        print(f"\n🔨 Début buildPage pour task_id: {task_id}")
        pwg = CPiwigoManager()

        # Mise à jour du statut
        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 10
        print(f"📊 Progress: 10% - task_id: {task_id}")

        # trouver ou créer la galerie correspondante
        existingCategories = getCategoriesDict(pwg)
        galeryName = f"""Galerie {label}"""
        if "galeries d'artistes / "+galeryName.strip().lower() in existingCategories:
            catdesc = existingCategories["galeries d'artistes / "+galeryName.strip().lower()]
            catid = catdesc["id"]
            print("----------> ", galeryName, catid)
        else:
            print(f"""Création de la catégorie {galeryName}""")
            rep = pwg.piwigo_create_category(galeryName, CategoryType.CREATORS)
            if rep and (rep.status_code==200):
                newcat = rep.json()
                catid = newcat["result"]["id"] if "result" in newcat else None

        tasks[task_id]['progress'] = 50
        print(f"📊 Progress: 50% - task_id: {task_id}")

        to_process = f"""
                {{
                    "categoryName": "{label}",
                    "qid": "{qid}",
                    "piwigoCategory": "{catid}",
                    "listimagespath": "D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/{catid}/listeImages_{qid}_{label.replace(" ", "").replace("-", "")}.json"
                }}
        """
        # Simulation d'un traitement long
        tasks[task_id]['progress'] = 80

        # Exemple de logique - remplacez par votre propre implémentation
        page_content = to_process + f"""

########################
# Page générée pour {label}

**Identifiant Wikidata :** {qid}
**URI :** {uri}
**Date de génération :** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Catégorie trouvée ou créée pour l'artiste :** {catid}
## Informations sur l'entité

Cette page a été générée automatiquement pour l'entité Wikidata {qid}.
L'artiste "{label}" peut être consulté directement sur Wikidata à l'adresse suivante :
{uri}

## Actions possibles

- Consulter la page Wikidata
- Extraire des informations supplémentaires
- Générer un rapport détaillé

---
Contenu généré par l'application Flask Wikidata Artist Search
        """

        time.sleep(2)
        tasks[task_id]['progress'] = 100
        print(f"📊 Progress: 100% - task_id: {task_id}")

        # Mise à jour avec le résultat final
        tasks[task_id].update({
            'status': 'completed',
            'page_content': page_content,
            'completed_at': datetime.now().isoformat()
        })

        print(f"✅ buildPage terminé pour task_id: {task_id}")

    except Exception as e:
        print(f"❌ Erreur dans buildPage pour task_id {task_id}: {e}")
        tasks[task_id].update({
            'status': 'error',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        })

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"\n🔒 VÉRIFICATION login_required pour {f.__name__}")
        print(f"'user' dans session : {'user' in session}")
        if 'user' in session:
            print(f"Utilisateur connecté : {session['user'].get('name', 'N/A')}")
        else:
            print("❌ Aucun utilisateur en session")

        if 'user' not in session:
            print(f"🔄 Redirection vers login depuis {f.__name__}")
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function

@app.route('/test')
def test():
    """Route de test sans authentification"""
    return f"""
    <h1>Test de session</h1>
    <p>Session: {dict(session)}</p>
    <p>'user' dans session: {'user' in session}</p>
    <p><a href="/force_logout">Forcer déconnexion</a></p>
    <p><a href="/login">Aller vers login</a></p>
    <p><a href="/">Retour accueil</a></p>
    """

@app.route('/logout')
def logout():
    print(f"\n🚪 DÉCONNEXION")
    print(f"Utilisateur avant déconnexion: {session.get('user', {}).get('name', 'N/A')}")

    # Méthode 1 : Supprimer les clés spécifiques
    session.pop('user', None)
    session.pop('oauth_state', None)

    # Méthode 2 (plus radical) : Tout vider
    # session.clear()

    print(f"Session après déconnexion: {dict(session)}")

    flash('Déconnexion réussie !', 'info')
    return redirect(url_for('login'))  # Rediriger vers login a

def api_token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            token = request.args.get('token')

        if not token:
            return jsonify({'error': 'Token requis'}), 401

        # Nettoyer le token (supprimer "Bearer " si présent)
        if token.startswith('Bearer '):
            token = token[7:]

        if token not in api_tokens:
            return jsonify({'error': 'Token invalide'}), 401

        # Vérifier l'expiration
        if datetime.now() > api_tokens[token]['expires_at']:
            return jsonify({'error': 'Token expiré'}), 401

        return f(*args, **kwargs)

    return decorated_function


def get_google_provider_cfg():
    """
    Configuration Google OAuth manuelle - évite les problèmes de réseau
    Ces endpoints sont stables et documentés par Google
    """
    print("🔧 Utilisation de la configuration Google manuelle")

    # Configuration OAuth 2.0 officielle de Google
    # Source: https://developers.google.com/identity/protocols/oauth2/openid-connect
    google_config = {
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
        "issuer": "https://accounts.google.com",
        "jwks_uri": "https://www.googleapis.com/oauth2/v3/certs",
        "revocation_endpoint": "https://oauth2.googleapis.com/revoke"
    }

    return google_config


@app.route('/api/task/<task_id>')
def get_task_status(task_id):
    """API pour récupérer le statut d'une tâche - accessible avec token OU session"""

    # Vérifier si l'utilisateur est authentifié via session (depuis l'interface web)
    if 'user' in session:
        print(f"✅ Accès à la tâche {task_id} via session utilisateur")
        if task_id not in tasks:
            return jsonify({'error': 'Tâche non trouvée'}), 404
        return jsonify(tasks[task_id])

    # Sinon, vérifier le token API (pour les appels externes)
    token = request.headers.get('Authorization')
    if not token:
        token = request.args.get('token')

    if not token:
        return jsonify({'error': 'Authentification requise'}), 401

    if token.startswith('Bearer '):
        token = token[7:]

    if token not in api_tokens:
        return jsonify({'error': 'Token invalide'}), 401

    if datetime.now() > api_tokens[token]['expires_at']:
        return jsonify({'error': 'Token expiré'}), 401

    if task_id not in tasks:
        return jsonify({'error': 'Tâche non trouvée'}), 404

    return jsonify(tasks[task_id])


# Routes API protégées par token

def build_image_list(page_content, qid, label, task_id):
    """
    Fonction qui génère une liste d'images basée sur le contenu de la page
    """
    sparqlTemplate = """
        select distinct ?uri ?createur ?createurLabel ?image ?titre_fr 
        where {
          values ?createur { wd:__QID__ } # QID du créateur
          values ?classRel { wdt:P31 wdt:P106 } # type ou occupation
          values ?class { wd:Q1028181 } # artiste peintre
          values ?rel { wdt:P170 } # créateur
          {
            # récupération du label associé au QID
            SELECT ?createur ?createurLabel 
            WHERE {
              values ?createur { wd:__QID__ }
              SERVICE wikibase:label { bd:serviceParam wikibase:language "fr, en, [AUTO_LANGUAGE],mul". }
            }
          }
          ?uri wdt:P31 wd:Q3305213;    # peinture
               ?rel ?createur;    # créé par le créateur indiqué par le QID
               wdt:P18 ?image. # a une image
           ?createur ?classRel ?class   # créateur est ou a pour occupation artiste peintre
          {
            SELECT ?uri ?uriLabel WHERE { # on récupère le label (titre)  associé à la peinture
              ?uri wdt:P31 wd:Q3305213;    
                 ?rel ?createur;    
                 wdt:P18 ?image.
              SERVICE wikibase:label { bd:serviceParam wikibase:language "fr, en, [AUTO_LANGUAGE],mul". }
            }
          }
          bind( ?uriLabel as ?titre_fr)
        }
    """

    try:
        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 10

        time.sleep(1)  # Simulation
        tasks[task_id]['progress'] = 30
        pattern = r"\{[\s\S]*?\}"
        match = re.search(pattern, page_content)
        creator = json.loads(match.group(0)) if match else {}
        res = genereListeImages(creator, sparqlTemplate)
        images_data = {}
        images_data["sparql"] = res["sparql"]
        images_data["images"] = []
        for imdesc in res["liste"]:
            images_data["images"].append(
                {
                    'uri': imdesc["uri"],
                    'createur': imdesc["createur"],
                    'createurLabel': imdesc["createurLabel"],
                    'url': imdesc["image"],
                    'image': imdesc["image"],
                    'categories': imdesc["categories"],
                    'titre_fr': imdesc["titre_fr"],
                    'description': imdesc["titre_fr"],
                    'source': 'Wikimedia Commons',
                    'license': ""
            }
            )
        # Simulation d'une recherche d'images via l'API Wikidata
        # En réalité, vous feriez une vraie requête SPARQL ou API
        #images_data = {
        #    'qid': qid,
        #    'label': label,
        #    'images': [
        #        {
        #            'url': f'https://commons.wikimedia.org/wiki/File:Example_{qid}_1.jpg',
        #            'description': f'Portrait de {label}',
        #            'source': 'Wikimedia Commons',
        #            'license': 'CC BY-SA 4.0'
        #        },...
        #    ],
        #    'total_found': 2,
        #    'search_timestamp': datetime.now().isoformat()
        #}
        images_data["qid"] = qid
        images_data["label"] = label
        images_data["total_found"] = len(res["liste"])
        images_data["search_timestamp"] = datetime.now().isoformat()

        time.sleep(2)  # Simulation de traitement
        tasks[task_id]['progress'] = 80

        # Génération du texte de résultat
        text_result = f"""
LISTE D'IMAGES POUR {label} ({qid})
{'=' * 50}

Images trouvées : {images_data['total_found']}
Recherche effectuée le : {images_data['search_timestamp']}

DÉTAILS DES IMAGES :
"""

        for i, img in enumerate(images_data['images'], 1):
            text_result += f"""
{i}. {img['description']}
   URL : {img['url']}
   Source : {img['source']}
   Licence : {img['license']}
"""

        text_result += f"""
{'=' * 50}
Fin de la liste d'images pour {label}
        """

        time.sleep(1)
        tasks[task_id]['progress'] = 100

        # Mise à jour avec le résultat final
        tasks[task_id].update({
            'status': 'completed',
            'text_result': text_result.strip(),
            'json_result': images_data,
            'completed_at': datetime.now().isoformat()
        })

    except Exception as e:
        tasks[task_id].update({
            'status': 'error',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        })

@app.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('index'))

    # Vérifier si les credentials Google sont configurés
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash('Configuration OAuth Google manquante. Connexion en mode démonstration.', 'warning')
        # Mode démonstration - créer un utilisateur fictif
        session['user'] = {
            'id': 'demo_user',
            'email': 'demo@example.com',
            'name': 'Utilisateur Démo',
            'picture': None
        }
        return redirect(url_for('index'))

    # Récupérer la configuration Google
    google_cfg = get_google_provider_cfg()
    if not google_cfg:
        flash('Impossible de se connecter à Google. Connexion en mode démonstration.', 'error')
        session['user'] = {
            'id': 'demo_user',
            'email': 'demo@example.com',
            'name': 'Utilisateur Démo',
            'picture': None
        }
        return redirect(url_for('index'))

    # URL d'autorisation Google
    authorization_endpoint = google_cfg["authorization_endpoint"]

    # Paramètres pour l'URL d'autorisation
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': url_for('auth', _external=True),
        'scope': 'openid email profile',
        'response_type': 'code',
        'state': secrets.token_urlsafe(32)
    }

    # Stocker le state en session pour vérification
    session['oauth_state'] = params['state']

    # Construire l'URL d'autorisation
    import urllib.parse

    auth_url = f"{authorization_endpoint}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)


@app.route('/auth')
def auth():
    # Vérifier le code d'autorisation
    code = request.args.get('code')
    state = request.args.get('state')

    if not code:
        flash('Autorisation refusée', 'error')
        return redirect(url_for('index'))

    # Vérifier le state (protection CSRF)
    if state != session.get('oauth_state'):
        flash('Erreur de sécurité lors de la connexion', 'error')
        return redirect(url_for('index'))

    # Échanger le code contre un token
    google_cfg = get_google_provider_cfg()
    if not google_cfg:
        flash('Erreur de connexion Google', 'error')
        return redirect(url_for('index'))

    token_endpoint = google_cfg["token_endpoint"]
    userinfo_endpoint = google_cfg["userinfo_endpoint"]

    # Demander le token d'accès
    token_data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': url_for('auth', _external=True),
    }

    try:
        token_response = requests.post(token_endpoint, data=token_data, timeout=10)
        token_response.raise_for_status()
        token_json = token_response.json()

        access_token = token_json.get('access_token')
        if not access_token:
            flash('Erreur lors de l\'obtention du token', 'error')
            return redirect(url_for('index'))

        # Récupérer les informations utilisateur
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_endpoint, headers=headers, timeout=10)
        userinfo_response.raise_for_status()
        user_info = userinfo_response.json()

        # Stocker les informations utilisateur en session
        session['user'] = {
            'id': user_info.get('sub'),
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'picture': user_info.get('picture')
        }

        users[user_info.get('sub')] = session['user']
        flash('Connexion réussie !', 'success')

    except requests.RequestException as e:
        flash(f'Erreur lors de la connexion: {str(e)}', 'error')
        return redirect(url_for('index'))

    return redirect(url_for('index'))

def logout():
    session.pop('user', None)
    session.pop('oauth_state', None)
    flash('Déconnexion réussie !', 'info')
    return redirect(url_for('index'))


@app.route('/validate', methods=['POST'])
def validate():
    """Route pour valider une entité sélectionnée"""
    qid = request.form.get('qid')
    label = request.form.get('label')
    uri = request.form.get('uri')

    if not qid:
        return jsonify({'error': 'QID manquant'}), 400

    # Stocker la validation (ici on retourne juste les infos)
    return render_template('validated.html',
                           qid=qid,
                           label=label,
                           uri=uri)

@app.route('/profile')
@login_required
def profile():
    # Générer un token API pour l'utilisateur
    user_id = session['user']['id']
    user_token = secrets.token_urlsafe(32)
    api_tokens[user_token] = {
        'user': user_id,
        'created_at': datetime.now(),
        'expires_at': datetime.now() + timedelta(days=30)
    }

    return render_template('profile.html',
                           user=session['user'],
                           api_token=user_token)


@app.route('/traiterUri', methods=['POST'])
@login_required
def traiter_uri():
    """Route pour traiter l'URI sélectionnée de façon asynchrone"""
    uri = request.form.get('uri')
    qid = request.form.get('qid')
    label = request.form.get('label')

    print(f"\n🚀 Début traiterUri - QID: {qid}, Label: {label}")

    if not uri:
        return jsonify({'error': 'URI manquant'}), 400

    # Génération d'un ID unique pour la tâche
    task_id = f"{qid}_{int(time.time())}"
    print(f"📝 Task ID généré: {task_id}")

    # Initialisation de la tâche
    tasks[task_id] = {
        'status': 'pending',
        'qid': qid,
        'label': label,
        'uri': uri,
        'created_at': datetime.now().isoformat(),
        'progress': 0
    }

    print(f"✅ Tâche initialisée: {tasks[task_id]}")

    # Lancement du traitement en arrière-plan
    thread = threading.Thread(target=buildPage, args=(qid, label, uri, task_id))
    thread.daemon = True
    thread.start()
    print(f"🧵 Thread lancé pour task_id: {task_id}")

    return render_template('processing.html',
                           task_id=task_id,
                           qid=qid,
                           label=label,
                           uri=uri)
@app.route('/result/<task_id>')
def show_result(task_id):
    """Affiche le résultat final d'une tâche"""
    if task_id not in tasks:
        return render_template('index.html', error="Tâche non trouvée")

    task = tasks[task_id]

    if task['status'] != 'completed':
        return render_template('processing.html',
                               task_id=task_id,
                               qid=task['qid'],
                               label=task['label'],
                               uri=task['uri'])

    return render_template('processed.html', result=task)


def search_wikidata_entities(search_term, limit=5):
    """
    Recherche des entités sur Wikidata correspondant au terme de recherche
    """
    url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbsearchentities',
        'search': search_term,
        'language': 'fr',
        'format': 'json',
        'limit': limit,
        'type': 'item'
    }

    headers = {
        'User-Agent': 'Grains de Culture WikidataArtistSearch/1.0 (https://grains-de-culture.fr/) Python/Flask'
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get('search', []):
            entity = {
                'qid': item.get('id'),
                'label': item.get('label', ''),
                'description': item.get('description', ''),
                'uri': f"https://www.wikidata.org/entity/{item.get('id')}",
                'concepturi': item.get('concepturi', '')
            }
            results.append(entity)

        return results
    except requests.RequestException as e:
        print(f"Erreur lors de la recherche Wikidata: {e}")
        return []


@app.route('/')
# @login_required  # Commentez cette ligne temporairement
def index():
    print("\n🔍 DIAGNOSTIC SESSION dans index() - SANS login_required")
    print("=" * 50)
    print(f"Session complète : {dict(session)}")
    print(f"'user' dans session : {'user' in session}")

    # Affichage conditionnel selon la session
    if 'user' not in session:
        print("❌ Pas d'utilisateur - devrait rediriger vers login")
    else:
        print(f"✅ Utilisateur trouvé : {session['user']}")
    print("=" * 50)

    return render_template('index.html')

@app.route('/force_logout')
def force_logout():
    """Force la déconnexion complète et vide toute la session"""
    print(f"\n🚪 DÉCONNEXION FORCÉE")
    print(f"Session avant: {dict(session)}")

    # Vider complètement la session
    session.clear()

    print(f"Session après: {dict(session)}")

    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('login'))
    # return redirect(url_for('index'))

@app.route('/debug/tasks')
@login_required
def debug_tasks():
    """Route de debug pour voir toutes les tâches"""
    return jsonify({
        'total_tasks': len(tasks),
        'tasks': {k: v for k, v in tasks.items()}
    })

@app.route('/search', methods=['POST'])
#@login_required
def search():
    """Route pour effectuer la recherche d'artiste"""
    artist_name = request.form.get('artist_name', '').strip()

    if not artist_name:
        return render_template('index.html', error="Veuillez entrer un nom d'artiste")

    # Rechercher sur Wikidata
    entities = search_wikidata_entities(artist_name)

    if not entities:
        return render_template('index.html',
                               error=f"Aucun résultat trouvé pour '{artist_name}'",
                               search_term=artist_name)

    return render_template('results.html',
                           entities=entities,
                           search_term=artist_name)


@app.route('/build-images', methods=['POST'])
@login_required
def build_images():
    """Route pour lancer la génération de liste d'images"""
    page_content = request.form.get('page_content')
    qid = request.form.get('qid')
    label = request.form.get('label')

    if not all([page_content, qid, label]):
        return jsonify({'error': 'Données manquantes'}), 400

    # Génération d'un ID unique pour la tâche
    task_id = f"images_{qid}_{int(time.time())}"

    # Initialisation de la tâche
    tasks[task_id] = {
        'status': 'pending',
        'type': 'images',
        'qid': qid,
        'label': label,
        'page_content': page_content,
        'created_at': datetime.now().isoformat(),
        'progress': 0
    }

    # Lancement du traitement en arrière-plan
    thread = threading.Thread(target=build_image_list, args=(page_content, qid, label, task_id))
    thread.daemon = True
    thread.start()

    return render_template('processing_images.html',
                           task_id=task_id,
                           qid=qid,
                           label=label)


@app.route('/images-result/<task_id>')
@login_required
def show_images_result(task_id):
    """Affiche le résultat de la génération d'images"""
    if task_id not in tasks:
        return render_template('index.html', error="Tâche non trouvée")

    task = tasks[task_id]

    if task['status'] != 'completed':
        return render_template('processing_images.html',
                               task_id=task_id,
                               qid=task['qid'],
                               label=task['label'])

    return render_template('images_result.html', result=task)


@app.route('/api/images/<task_id>/json')
@api_token_required
def get_images_json(task_id):
    """Retourne le résultat JSON de la liste d'images"""
    if task_id not in tasks:
        return jsonify({'error': 'Tâche non trouvée'}), 404

    task = tasks[task_id]
    if task.get('type') != 'images':
        return jsonify({'error': 'Ce n\'est pas une tâche d\'images'}), 400

    if task['status'] != 'completed':
        return jsonify({'error': 'Tâche non terminée', 'status': task['status']}), 400

    return jsonify(task.get('json_result', {}))

if __name__ == '__main__':
    app.run(debug=False)
