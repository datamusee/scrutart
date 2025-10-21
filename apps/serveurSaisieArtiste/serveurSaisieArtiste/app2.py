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
from CPiwigoManager import CPiwigoManager, CategoryType
from generationListeImagesPourArtiste import genereListeImages

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

# Modèle par défaut pour l'annonce d'exposition
DEFAULT_EXPOSITION_PROMPT = """En tant que critique d'art professionnel, créez une annonce d'exposition captivante basée sur les informations suivantes :

Page de description : {description_url}
Liens additionnels : {additional_links}

L'annonce doit inclure :
1. Un titre accrocheur
2. Une introduction engageante sur l'artiste ou le thème
3. Les informations pratiques (dates, lieu, horaires)
4. Une description des œuvres présentées
5. Un appel à l'action pour inciter les visiteurs

Ton : professionnel mais accessible, enthousiaste sans être exagéré.
Longueur : 300-500 mots.
"""

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


# Filtre Jinja2 pour convertir les retours à la ligne en <br>
@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convertit les retours à la ligne en <br>"""
    if text:
        return text.replace('\n', '<br>\n')
    return text


# ============================================================================
# FONCTIONS PERSONNALISABLES (À COMPLÉTER PAR L'UTILISATEUR)
# ============================================================================

def upload_images_to_gallery(images_list, json_structure):
    """
    FONCTION À COMPLÉTER : Upload des images vers la galerie

    Args:
        images_list: Liste des images générées
        json_structure: Structure JSON de l'étape précédente

    Returns:
        dict: Résultat de l'upload avec statut et détails
    """
    # TODO: Implémenter votre logique d'upload ici
    # Exemple : appel API vers votre galerie, upload FTP, etc.

    print(f"📤 Upload de {len(images_list.get('images', []))} images vers la galerie...")
    time.sleep(2)  # Simulation

    return {
        'status': 'success',
        'uploaded_count': len(images_list.get('images', [])),
        'gallery_url': f"https://example.com/gallery/{json_structure.get('qid', '')}",
        'message': 'Images uploadées avec succès (fonction à implémenter)'
    }


def build_wordpress_post(json_structure):
    """
    FONCTION À COMPLÉTER : Construction d'un billet de blog WordPress

    Args:
        json_structure: Structure JSON contenant les informations de l'artiste

    Returns:
        dict: Données du post WordPress (titre, contenu, catégories, etc.)
    """
    # TODO: Implémenter votre logique de génération de post WordPress
    # Peut inclure : appel à l'API WordPress, génération de contenu HTML, etc.

    print(f"📝 Construction du billet WordPress pour {json_structure.get('label', '')}...")
    time.sleep(2)  # Simulation

    # Exemple de structure retournée
    return {
        'status': 'success',
        'post_id': None,  # À remplir après publication
        'title': f"Découverte de l'artiste {json_structure.get('label', '')}",
        'content': f"""
        <h2>À propos de {json_structure.get('label', '')}</h2>
        <p>Wikidata ID : {json_structure.get('qid', '')}</p>
        <p>Catégorie : {json_structure.get('categoryName', '')}</p>
        <!-- TODO: Ajouter votre contenu personnalisé -->
        """,
        'categories': ['Art', 'Artistes'],
        'tags': [json_structure.get('label', ''), json_structure.get('qid', '')],
        'message': 'Structure WordPress générée (fonction à implémenter)'
    }


def build_exposition_announcement(description_url, additional_links, prompt_template):
    """
    FONCTION À COMPLÉTER : Construction d'une annonce d'exposition

    Args:
        description_url: URL de la page de description de l'exposition
        additional_links: Liste d'URLs additionnelles fournies par l'utilisateur
        prompt_template: Template de prompt pour générer l'annonce

    Returns:
        dict: Contenu de l'annonce d'exposition
    """
    # TODO: Implémenter votre logique de génération d'annonce
    # Peut inclure : scraping des URLs, appel à une IA générative, etc.

    print(f"📢 Construction de l'annonce d'exposition depuis {description_url}...")
    time.sleep(2)  # Simulation

    # Remplir le template avec les données
    filled_prompt = prompt_template.format(
        description_url=description_url,
        additional_links=', '.join(additional_links) if additional_links else 'Aucun'
    )

    return {
        'status': 'success',
        'announcement_text': f"""
        [Annonce générée automatiquement - À compléter]

        Basé sur : {description_url}
        Liens additionnels : {len(additional_links) if additional_links else 0}

        Prompt utilisé :
        {filled_prompt}

        TODO: Implémenter la génération réelle de l'annonce
        """,
        'prompt_used': filled_prompt,
        'sources': {
            'description_url': description_url,
            'additional_links': additional_links
        },
        'message': 'Annonce générée (fonction à implémenter)'
    }


# ============================================================================

def getCategoriesDict(pwg):
    existingCategories = {}
    res = pwg.piwigo_get_categories()
    if res and ("stat" in res) and (res["stat"] == "ok") and (
            "result" in res):
        for cat in res["result"]:
            label = cat[
                "name"].strip().lower()
            existingCategories[label] = cat
            if "sub_categories" in cat:
                for subcat in cat["sub_categories"]:
                    label = subcat[
                        "name"].strip().lower()
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

        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 10
        print(f"📊 Progress: 10% - task_id: {task_id}")

        existingCategories = getCategoriesDict(pwg)
        galeryName = f"""Galerie {label}"""
        if "galeries d'artistes / " + galeryName.strip().lower() in existingCategories:
            catdesc = existingCategories["galeries d'artistes / " + galeryName.strip().lower()]
            catid = catdesc["id"]
            print("----------> ", galeryName, catid)
        else:
            print(f"""Création de la catégorie {galeryName}""")
            rep = pwg.piwigo_create_category(label, CategoryType.CREATORS)
            if rep and (rep.status_code == 200):
                newcat = rep.json()
                catid = newcat["result"]["id"] if "result" in newcat else None

        tasks[task_id]['progress'] = 50
        print(f"📊 Progress: 50% - task_id: {task_id}")

        to_process = {
            "categoryName": label,
            "qid": qid,
            "piwigoCategory": catid,
            "listimagespath": f"D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/{catid}/listeImages_{qid}_{label.replace(' ', '').replace('-', '')}.json"
        }

        tasks[task_id]['progress'] = 80

        page_content = json.dumps(to_process, indent=2) + f"""

########################
# Page générée pour {label}

**Identifiant Wikidata :** {qid}
**URI :** {uri}
**Date de génération :** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Catégorie trouvée ou créée pour l'artiste :** {catid}
        """

        time.sleep(2)
        tasks[task_id]['progress'] = 100
        print(f"📊 Progress: 100% - task_id: {task_id}")

        tasks[task_id].update({
            'status': 'completed',
            'page_content': page_content,
            'json_structure': to_process,
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

    session.pop('user', None)
    session.pop('oauth_state', None)

    print(f"Session après déconnexion: {dict(session)}")

    flash('Déconnexion réussie !', 'info')
    return redirect(url_for('login'))


def api_token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            token = request.args.get('token')

        if not token:
            return jsonify({'error': 'Token requis'}), 401

        if token.startswith('Bearer '):
            token = token[7:]

        if token not in api_tokens:
            return jsonify({'error': 'Token invalide'}), 401

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

    if 'user' in session:
        print(f"✅ Accès à la tâche {task_id} via session utilisateur")
        if task_id not in tasks:
            return jsonify({'error': 'Tâche non trouvée'}), 404
        return jsonify(tasks[task_id])

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


def build_image_list(page_content, qid, label, task_id):
    """
    Fonction qui génère une liste d'images basée sur le contenu de la page
    """
    sparqlTemplate = """
        select distinct ?uri ?createur ?createurLabel ?image ?titre_fr 
        where {
          values ?createur { wd:__QID__ }
          values ?classRel { wdt:P31 wdt:P106 }
          values ?class { wd:Q1028181 }
          values ?rel { wdt:P170 }
          {
            SELECT ?createur ?createurLabel 
            WHERE {
              values ?createur { wd:__QID__ }
              SERVICE wikibase:label { bd:serviceParam wikibase:language "fr, en, [AUTO_LANGUAGE],mul". }
            }
          }
          ?uri wdt:P31 wd:Q3305213;
               ?rel ?createur;
               wdt:P18 ?image.
           ?createur ?classRel ?class
          {
            SELECT ?uri ?uriLabel WHERE {
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

        time.sleep(1)
        tasks[task_id]['progress'] = 30
        pattern = r"\{[\s\S]*?\}"
        match = re.search(pattern, page_content)
        creator = json.loads(match.group(0)) if match else {}
        res = genereListeImages(creator, sparqlTemplate)
        images_data = {}
        images_data["sparql"] = res["sparql"]
        images_data["images"] = []
        for imdesc in res["liste"]:
            images_data["images"].append({
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
            })

        images_data["qid"] = qid
        images_data["label"] = label
        images_data["total_found"] = len(res["liste"])
        images_data["search_timestamp"] = datetime.now().isoformat()

        time.sleep(2)
        tasks[task_id]['progress'] = 80

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


def process_gallery_upload(images_list, json_structure, task_id):
    """
    Processus d'upload des images vers la galerie
    """
    try:
        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 20

        # Appel de la fonction personnalisable
        result = upload_images_to_gallery(images_list, json_structure)

        tasks[task_id]['progress'] = 100
        tasks[task_id].update({
            'status': 'completed',
            'upload_result': result,
            'completed_at': datetime.now().isoformat()
        })

    except Exception as e:
        tasks[task_id].update({
            'status': 'error',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        })


def process_wordpress_post(json_structure, task_id):
    """
    Processus de construction du post WordPress
    """
    try:
        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 20

        # Appel de la fonction personnalisable
        result = build_wordpress_post(json_structure)

        tasks[task_id]['progress'] = 100
        tasks[task_id].update({
            'status': 'completed',
            'wordpress_result': result,
            'completed_at': datetime.now().isoformat()
        })

    except Exception as e:
        tasks[task_id].update({
            'status': 'error',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        })


def process_exposition_announcement(description_url, additional_links, prompt_template, task_id):
    """
    Processus de construction de l'annonce d'exposition
    """
    try:
        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 20

        # Appel de la fonction personnalisable
        result = build_exposition_announcement(description_url, additional_links, prompt_template)

        tasks[task_id]['progress'] = 100
        tasks[task_id].update({
            'status': 'completed',
            'exposition_result': result,
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

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        flash('Configuration OAuth Google manquante. Connexion en mode démonstration.', 'warning')
        session['user'] = {
            'id': 'demo_user',
            'email': 'demo@example.com',
            'name': 'Utilisateur Démo',
            'picture': None
        }
        return redirect(url_for('index'))

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

    authorization_endpoint = google_cfg["authorization_endpoint"]

    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': url_for('auth', _external=True),
        'scope': 'openid email profile',
        'response_type': 'code',
        'state': secrets.token_urlsafe(32)
    }

    session['oauth_state'] = params['state']

    import urllib.parse
    auth_url = f"{authorization_endpoint}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)


@app.route('/auth')
def auth():
    code = request.args.get('code')
    state = request.args.get('state')

    if not code:
        flash('Autorisation refusée', 'error')
        return redirect(url_for('index'))

    if state != session.get('oauth_state'):
        flash('Erreur de sécurité lors de la connexion', 'error')
        return redirect(url_for('index'))

    google_cfg = get_google_provider_cfg()
    if not google_cfg:
        flash('Erreur de connexion Google', 'error')
        return redirect(url_for('index'))

    token_endpoint = google_cfg["token_endpoint"]
    userinfo_endpoint = google_cfg["userinfo_endpoint"]

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

        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_endpoint, headers=headers, timeout=10)
        userinfo_response.raise_for_status()
        user_info = userinfo_response.json()

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


@app.route('/validate', methods=['POST'])
def validate():
    """Route pour valider une entité sélectionnée"""
    qid = request.form.get('qid')
    label = request.form.get('label')
    uri = request.form.get('uri')

    if not qid:
        return jsonify({'error': 'QID manquant'}), 400

    return render_template('validated.html',
                           qid=qid,
                           label=label,
                           uri=uri)


@app.route('/profile')
@login_required
def profile():
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

    task_id = f"{qid}_{int(time.time())}"
    print(f"📝 Task ID généré: {task_id}")

    tasks[task_id] = {
        'status': 'pending',
        'qid': qid,
        'label': label,
        'uri': uri,
        'created_at': datetime.now().isoformat(),
        'progress': 0
    }

    print(f"✅ Tâche initialisée: {tasks[task_id]}")

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
def index():
    print("\n🔍 DIAGNOSTIC SESSION dans index()")
    print("=" * 50)
    print(f"Session complète : {dict(session)}")
    print(f"'user' dans session : {'user' in session}")

    if 'user' not in session:
        print("❌ Pas d'utilisateur - redirection vers login")
        return redirect(url_for('login'))
    else:
        print(f"✅ Utilisateur trouvé : {session['user']}")
    print("=" * 50)

    return render_template('index.html')


@app.route('/force_logout')
def force_logout():
    """Force la déconnexion complète et vide toute la session"""
    print(f"\n🚪 DÉCONNEXION FORCÉE")
    print(f"Session avant: {dict(session)}")

    session.clear()

    print(f"Session après: {dict(session)}")

    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('login'))


@app.route('/debug/tasks')
@login_required
def debug_tasks():
    """Route de debug pour voir toutes les tâches"""
    return jsonify({
        'total_tasks': len(tasks),
        'tasks': {k: v for k, v in tasks.items()}
    })


@app.route('/search', methods=['POST'])
def search():
    """Route pour effectuer la recherche d'artiste"""
    artist_name = request.form.get('artist_name', '').strip()

    if not artist_name:
        return render_template('index.html', error="Veuillez entrer un nom d'artiste")

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

    task_id = f"images_{qid}_{int(time.time())}"

    tasks[task_id] = {
        'status': 'pending',
        'type': 'images',
        'qid': qid,
        'label': label,
        'page_content': page_content,
        'created_at': datetime.now().isoformat(),
        'progress': 0
    }

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


# ============================================================================
# NOUVELLES ROUTES POUR LES ÉTAPES SUPPLÉMENTAIRES
# ============================================================================

@app.route('/upload-to-gallery', methods=['POST'])
@login_required
def upload_to_gallery():
    """Route pour uploader les images vers la galerie"""
    images_json = request.form.get('images_json')
    json_structure = request.form.get('json_structure')

    if not all([images_json, json_structure]):
        return jsonify({'error': 'Données manquantes'}), 400

    try:
        images_list = json.loads(images_json)
        json_struct = json.loads(json_structure)
    except json.JSONDecodeError:
        return jsonify({'error': 'Format JSON invalide'}), 400

    task_id = f"gallery_{json_struct.get('qid', 'unknown')}_{int(time.time())}"

    tasks[task_id] = {
        'status': 'pending',
        'type': 'gallery_upload',
        'images_count': len(images_list.get('images', [])),
        'created_at': datetime.now().isoformat(),
        'progress': 0
    }

    thread = threading.Thread(target=process_gallery_upload, args=(images_list, json_struct, task_id))
    thread.daemon = True
    thread.start()

    return render_template('processing_generic.html',
                           task_id=task_id,
                           task_type='Upload vers la galerie',
                           description=f"Upload de {len(images_list.get('images', []))} images")


@app.route('/create-wordpress-post', methods=['POST'])
@login_required
def create_wordpress_post():
    """Route pour créer un post WordPress"""
    json_structure = request.form.get('json_structure')

    if not json_structure:
        return jsonify({'error': 'Structure JSON manquante'}), 400

    try:
        json_struct = json.loads(json_structure)
    except json.JSONDecodeError:
        return jsonify({'error': 'Format JSON invalide'}), 400

    task_id = f"wordpress_{json_struct.get('qid', 'unknown')}_{int(time.time())}"

    tasks[task_id] = {
        'status': 'pending',
        'type': 'wordpress_post',
        'artist_name': json_struct.get('categoryName', 'N/A'),
        'created_at': datetime.now().isoformat(),
        'progress': 0
    }

    thread = threading.Thread(target=process_wordpress_post, args=(json_struct, task_id))
    thread.daemon = True
    thread.start()

    return render_template('processing_generic.html',
                           task_id=task_id,
                           task_type='Création post WordPress',
                           description=f"Génération du post pour {json_struct.get('categoryName', 'N/A')}")


@app.route('/create-exposition-announcement', methods=['POST'])
@login_required
def create_exposition_announcement():
    """Route pour créer une annonce d'exposition"""
    description_url = request.form.get('description_url')
    additional_links = request.form.get('additional_links', '')
    prompt_template = request.form.get('prompt_template', DEFAULT_EXPOSITION_PROMPT)

    if not description_url:
        return jsonify({'error': 'URL de description manquante'}), 400

    # Parser les liens additionnels (séparés par des virgules ou retours à la ligne)
    links_list = [link.strip() for link in re.split(r'[,\n]', additional_links) if link.strip()]

    task_id = f"exposition_{int(time.time())}"

    tasks[task_id] = {
        'status': 'pending',
        'type': 'exposition_announcement',
        'description_url': description_url,
        'additional_links_count': len(links_list),
        'created_at': datetime.now().isoformat(),
        'progress': 0
    }

    thread = threading.Thread(target=process_exposition_announcement,
                              args=(description_url, links_list, prompt_template, task_id))
    thread.daemon = True
    thread.start()

    return render_template('processing_generic.html',
                           task_id=task_id,
                           task_type='Annonce d\'exposition',
                           description=f"Génération basée sur {description_url}")


@app.route('/menu')
@login_required
def menu():
    """Menu principal pour accéder à toutes les étapes"""
    return render_template('menu.html')


@app.route('/step-gallery-upload')
@login_required
def step_gallery_upload():
    """Interface pour l'upload vers la galerie"""
    return render_template('step_gallery_upload.html')


@app.route('/step-wordpress')
@login_required
def step_wordpress():
    """Interface pour la création de post WordPress"""
    return render_template('step_wordpress.html')


@app.route('/step-exposition')
@login_required
def step_exposition():
    """Interface pour la création d'annonce d'exposition"""
    return render_template('step_exposition.html',
                           default_prompt=DEFAULT_EXPOSITION_PROMPT)


@app.route('/task-result/<task_id>')
@login_required
def show_task_result(task_id):
    """Affiche le résultat d'une tâche générique"""
    if task_id not in tasks:
        return render_template('index.html', error="Tâche non trouvée")

    task = tasks[task_id]

    if task['status'] != 'completed':
        task_type = task.get('type', 'Traitement')
        return render_template('processing_generic.html',
                               task_id=task_id,
                               task_type=task_type,
                               description='En cours de traitement...')

    # Rendu selon le type de tâche
    if task.get('type') == 'gallery_upload':
        return render_template('result_gallery_upload.html', result=task)
    elif task.get('type') == 'wordpress_post':
        return render_template('result_wordpress.html', result=task)
    elif task.get('type') == 'exposition_announcement':
        return render_template('result_exposition.html', result=task)
    else:
        return render_template('result_generic.html', result=task)


# ============================================================================
# ROUTES API
# ============================================================================

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


@app.route('/api/exposition-prompt', methods=['GET', 'PUT'])
@login_required
def manage_exposition_prompt():
    """Récupère ou modifie le template de prompt pour les expositions"""
    global DEFAULT_EXPOSITION_PROMPT

    if request.method == 'GET':
        return jsonify({'prompt_template': DEFAULT_EXPOSITION_PROMPT})

    elif request.method == 'PUT':
        data = request.get_json()
        new_prompt = data.get('prompt_template')

        if not new_prompt:
            return jsonify({'error': 'Template manquant'}), 400

        DEFAULT_EXPOSITION_PROMPT = new_prompt
        return jsonify({
            'status': 'success',
            'message': 'Template mis à jour',
            'prompt_template': DEFAULT_EXPOSITION_PROMPT
        })


if __name__ == '__main__':
    app.run(debug=False)