"""
Synchroniseur Piwigo-Wikidata pour les collections d'artistes
Traite les images de la catégorie 80 et les associe aux collections (catégorie '854')
Version avec chargement progressif par lots
"""

import re
import requests
from flask import Flask, render_template_string, jsonify, request
from threading import Thread, Lock
import time
import json
import os
from typing import Optional, Dict, List, Set
import logging
from CPiwigoManager import CPiwigoManager, CategoryType

pimag = CPiwigoManager()

# Configuration Piwigo
PIWIGO_URL = "https://galeries.grains-de-culture.fr"
PIWIGO_USERNAME = pimag.login
PIWIGO_PASSWORD = pimag.password
PIWIGO_API = f"{PIWIGO_URL}/ws.php?format=json"

# Fichiers de sauvegarde
SAVE_FILE = "piwigo_wikidata_progress.json"

# Configuration du traitement par lots
BATCH_SIZE = 100  # Nombre d'images à charger et traiter par lot

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regex pour extraire le QID Wikidata
QID_REGEX = r'lément Wikidata[^<]*<a[^>]+href=["\']([^"\']*wikidata\.org/(?:wiki|entity)/(Q\d+))["\'][^>]*>([^<]*)</a>'


# État global du traitement
class ProcessState:
    def __init__(self):
        self.running = False
        self.paused = False
        self.current_image = None
        self.current_categories = []
        self.found_collection = None
        self.target_category = None
        self.stats = {
            'processed': 0,
            'with_collection': 0,
            'categories_created': 0,
            'errors': 0
        }
        self.lock = Lock()
        self.pwg_id = None

        # Mémorisation pour reprise
        self.processed_images: Set[int] = set()
        self.collection_mapping: Dict[str, int] = {}
        self.total_images = 0  # Total estimé (sera mis à jour)
        self.current_batch = 0  # Page/lot actuel
        self.load_progress()

    def load_progress(self):
        """Charge la progression sauvegardée"""
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_images = set(data.get('processed_images', []))
                    self.collection_mapping = data.get('collection_mapping', {})
                    self.stats = data.get('stats', self.stats)
                    self.current_batch = data.get('current_batch', 0)
                    logger.info(f"Progression chargée: {len(self.processed_images)} images déjà traitées, lot {self.current_batch}")
            except Exception as e:
                logger.error(f"Erreur chargement progression: {e}")

    def save_progress(self):
        """Sauvegarde la progression"""
        try:
            data = {
                'processed_images': list(self.processed_images),
                'collection_mapping': self.collection_mapping,
                'stats': self.stats,
                'current_batch': self.current_batch
            }
            with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde progression: {e}")

    def mark_image_processed(self, image_id: int):
        """Marque une image comme traitée et sauvegarde"""
        with self.lock:
            self.processed_images.add(image_id)
            self.save_progress()

    def is_image_processed(self, image_id: int) -> bool:
        """Vérifie si une image a déjà été traitée"""
        return image_id in self.processed_images


state = ProcessState()


class PiwigoAPI:
    """Gestion de l'API Piwigo"""

    def __init__(self, url: str, username: str, password: str):
        self.url = url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.pwg_id = None
        self.pwg_token = None

    def login(self) -> bool:
        """Connexion à Piwigo"""
        try:
            response = self.session.post(self.url, data={
                'method': 'pwg.session.login',
                'username': self.username,
                'password': self.password
            })
            # Nettoie les warnings PHP avant le JSON
            text = response.text
            json_start = text.find('{')
            if json_start > 0:
                text = text[json_start:]

            result = json.loads(text)
            if result['stat'] == 'ok':
                self.pwg_id = self.session.cookies.get('pwg_id')
                # Récupère le token
                self.pwg_token = self._get_token()
                logger.info("Connexion Piwigo réussie")
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur connexion Piwigo: {e}")
            return False

    def _get_token(self) -> Optional[str]:
        """Récupère le token pwg pour les opérations protégées"""
        try:
            response = self.session.post(self.url, data={
                'method': 'pwg.session.getStatus'
            })
            text = response.text
            json_start = text.find('{')
            if json_start > 0:
                text = text[json_start:]

            result = json.loads(text)
            if result['stat'] == 'ok' and 'pwg_token' in result['result']:
                return result['result']['pwg_token']
            return None
        except Exception as e:
            logger.error(f"Erreur récupération token: {e}")
            return None

    def get_category_images_batch(self, cat_id: int, page: int, per_page: int, recursive: bool = True) -> tuple[List[Dict], bool]:
        """
        Récupère un lot d'images d'une catégorie
        Retourne (liste_images, has_more)
        """
        try:
            response = self.session.post(self.url, data={
                'method': 'pwg.categories.getImages',
                'cat_id': cat_id,
                'recursive': str(recursive).lower(),
                'per_page': per_page,
                'page': page
            })
            # Nettoie les warnings PHP avant le JSON
            text = response.text
            json_start = text.find('{')
            if json_start > 0:
                text = text[json_start:]

            result = json.loads(text)
            if result['stat'] == 'ok':
                images = result['result']['images']
                # Il y a plus d'images si on a reçu le nombre demandé
                has_more = len(images) >= per_page
                logger.info(f"Lot {page}: {len(images)} images récupérées")
                return images, has_more
            return [], False
        except Exception as e:
            logger.error(f"Erreur récupération lot {page}: {e}")
            return [], False

    def get_total_images_count(self, cat_id: int, recursive: bool = True) -> int:
        """
        Récupère le nombre total d'images dans une catégorie
        """
        try:
            # Fait une requête avec per_page=1 juste pour obtenir le total
            response = self.session.post(self.url, data={
                'method': 'pwg.categories.getImages',
                'cat_id': cat_id,
                'recursive': str(recursive).lower(),
                'per_page': 1,
                'page': 0
            })
            text = response.text
            json_start = text.find('{')
            if json_start > 0:
                text = text[json_start:]

            result = json.loads(text)
            if result['stat'] == 'ok' and 'paging' in result['result']:
                total = result['result']['paging'].get('count', 0)
                logger.info(f"Total d'images dans la catégorie {cat_id}: {total}")
                return total
            return 0
        except Exception as e:
            logger.error(f"Erreur récupération total images: {e}")
            return 0

    def get_image_info(self, image_id: int) -> Optional[Dict]:
        """Récupère les infos détaillées d'une image"""
        try:
            response = self.session.post(self.url, data={
                'method': 'pwg.images.getInfo',
                'image_id': image_id
            })
            # Nettoie les warnings PHP avant le JSON
            text = response.text
            json_start = text.find('{')
            if json_start > 0:
                text = text[json_start:]

            result = json.loads(text)
            if result['stat'] == 'ok':
                return result['result']
            return None
        except Exception as e:
            logger.error(f"Erreur infos image {image_id}: {e}")
            return None

    def get_categories(self) -> List[Dict]:
        """Récupère toutes les catégories"""
        try:
            response = self.session.post(self.url, data={
                'method': 'pwg.categories.getList',
                'recursive': 'true'
            })
            # Nettoie les warnings PHP avant le JSON
            text = response.text
            json_start = text.find('{')
            if json_start > 0:
                text = text[json_start:]

            result = json.loads(text)
            if result['stat'] == 'ok':
                return result['result']['categories']
            return []
        except Exception as e:
            logger.error(f"Erreur récupération catégories: {e}")
            return []

    def create_category(self, name: str, parent_id: int) -> Optional[int]:
        """Crée une nouvelle catégorie"""
        if name[0]=='Q': return None  # on n'a pas trouvé de vrai nom pour la collection
        try:
            response = self.session.post(self.url, data={
                'method': 'pwg.categories.add',
                'name': name,
                'status':'private',
                'parent': parent_id,
                'pwg_token': self.pwg_token
            })
            # Nettoie les warnings PHP avant le JSON
            text = response.text
            json_start = text.find('{')
            if json_start > 0:
                text = text[json_start:]

            result = json.loads(text)
            if result['stat'] == 'ok':
                logger.info(f"Catégorie créée: {name} (ID: {result['result']['id']})")
                return result['result']['id']
            return None
        except Exception as e:
            logger.error(f"Erreur création catégorie {name}: {e}")
            return None

    def add_image_to_category(self, image_id: int, cat_id: int) -> bool:
        """Ajoute une image à une catégorie"""
        try:
            response = self.session.post(self.url, data={
                'method': 'pwg.images.setCategory',
                'category_id': cat_id,
                'image_id': image_id,
                'pwg_token': self.pwg_token
            })
            # Nettoie les warnings PHP avant le JSON
            text = response.text
            json_start = text.find('{')
            if json_start > 0:
                text = text[json_start:]

            result = json.loads(text)
            return result['stat'] == 'ok'
        except Exception as e:
            logger.error(f"Erreur ajout image {image_id} à catégorie {cat_id}: {e}")
            return False


class WikidataAPI:
    """Gestion de l'API Wikidata"""

    # Délai minimum entre requêtes (en secondes)
    REQUEST_DELAY = 1.0
    _last_request_time = 0
    _lock = Lock()

    # Headers requis par Wikidata
    HEADERS = {
        'User-Agent': 'PiwigoWikidataSync/1.0 (https://galeries.grains-de-culture.fr; contact@example.com) Python/requests'
    }

    @staticmethod
    def _wait_before_request():
        """Respecte le délai minimum entre requêtes"""
        with WikidataAPI._lock:
            elapsed = time.time() - WikidataAPI._last_request_time
            if elapsed < WikidataAPI.REQUEST_DELAY:
                time.sleep(WikidataAPI.REQUEST_DELAY - elapsed)
            WikidataAPI._last_request_time = time.time()

    @staticmethod
    def get_collection(qid: str) -> Optional[Dict]:
        """Récupère la collection (P195) d'une entité Wikidata"""
        try:
            WikidataAPI._wait_before_request()

            url = "https://www.wikidata.org/w/api.php"
            params = {
                'action': 'wbgetclaims',
                'entity': qid,
                'property': 'P195',
                'format': 'json'
            }
            response = requests.get(url, params=params, headers=WikidataAPI.HEADERS)
            data = response.json()

            if 'claims' in data and 'P195' in data['claims']:
                # Récupère le premier claim
                claim = data['claims']['P195'][0]
                collection_qid = claim['mainsnak']['datavalue']['value']['id']

                # Récupère le label français
                label = WikidataAPI.get_label(collection_qid, 'fr')
                return {
                    'qid': collection_qid,
                    'label': label
                }
            return None
        except Exception as e:
            logger.error(f"Erreur récupération collection pour {qid}: {e}")
            return None

    @staticmethod
    def get_label(qid: str, lang: str = 'fr') -> str:
        """Récupère le label d'une entité dans une langue donnée"""
        try:
            WikidataAPI._wait_before_request()

            url = "https://www.wikidata.org/w/api.php"
            params = {
                'action': 'wbgetentities',
                'ids': qid,
                'props': 'labels',
                'languages': lang,
                'format': 'json'
            }
            response = requests.get(url, params=params, headers=WikidataAPI.HEADERS)
            data = response.json()

            if 'entities' in data and qid in data['entities']:
                entity = data['entities'][qid]
                if 'labels' in entity and lang in entity['labels']:
                    return entity['labels'][lang]['value']
            return qid
        except Exception as e:
            logger.error(f"Erreur récupération label pour {qid}: {e}")
            return qid


def extract_qid_from_description(description: str) -> Optional[str]:
    """Extrait le QID Wikidata de la description"""
    if description:
        match = re.search(QID_REGEX, description)
        if match:
            return match.group(2)  # Le QID est dans le groupe 2
    return None


def build_collection_mapping(piwigo: PiwigoAPI) -> Dict[str, int]:
    """Construit la table de correspondance collections -> catégories"""
    # Utilise la table sauvegardée si elle existe déjà
    if state.collection_mapping:
        logger.info(f"Utilisation de la table de correspondance sauvegardée: {len(state.collection_mapping)} entrées")
        return state.collection_mapping

    mapping = {}
    categories = piwigo.get_categories()

    for cat in categories:
        if cat.get('id_uppercat') == '854':  # Sous-catégories de 854
            mapping[cat['name'].lower()] = cat['id']

    state.collection_mapping = mapping
    state.save_progress()
    logger.info(f"Table de correspondance construite: {len(mapping)} catégories de collection")
    return mapping


def process_single_image(piwigo: PiwigoAPI, img: Dict, collection_mapping: Dict[str, int]) -> None:
    """Traite une seule image"""
    # Récupération des infos détaillées
    img_info = piwigo.get_image_info(img['id'])
    if not img_info:
        state.mark_image_processed(img['id'])
        state.stats['errors'] += 1
        state.save_progress()
        logger.warning(f"Impossible de récupérer les infos de l'image {img['id']}, passage à la suivante")
        return

    with state.lock:
        state.current_image = img_info
        state.current_categories = [cat['name'] for cat in img_info.get('categories', [])]
        state.found_collection = None
        state.target_category = None

    # Extraction du QID
    description = img_info.get('comment', '')
    qid = extract_qid_from_description(description)

    if not qid:
        state.mark_image_processed(img['id'])
        state.stats['processed'] += 1
        state.save_progress()
        logger.info(f"Image {img['id']} sans QID Wikidata, passage à la suivante")
        return

    # Récupération de la collection
    collection = WikidataAPI.get_collection(qid)

    if collection:
        state.stats['with_collection'] += 1
        collection_label_lower = collection['label'].lower()

        with state.lock:
            state.found_collection = collection

            # Recherche de la catégorie correspondante
            if collection_label_lower in collection_mapping:
                state.target_category = {
                    'id': collection_mapping[collection_label_lower],
                    'name': collection['label'],
                    'exists': True
                }
            else:
                state.target_category = {
                    'id': None,
                    'name': collection['label'],
                    'exists': False
                }

        logger.info(f"Image {img['id']}: Collection '{collection['label']}' trouvée")

        # Pause pour permettre validation
        time.sleep(10)

        if not state.running:
            return

        # Création de la catégorie si nécessaire
        if not state.target_category['exists']:
            cat_id = piwigo.create_category(collection['label'], 854)
            if cat_id:
                collection_mapping[collection_label_lower] = cat_id
                state.collection_mapping = collection_mapping
                state.target_category['id'] = cat_id
                state.stats['categories_created'] += 1
                state.save_progress()
                logger.info(f"Catégorie '{collection['label']}' créée (ID: {cat_id})")

        # Ajout de l'image à la catégorie
        if state.target_category['id']:
            success = piwigo.add_image_to_category(img['id'], state.target_category['id'])
            if success:
                logger.info(f"Image {img['id']} ajoutée à la catégorie {state.target_category['id']}")
            else:
                logger.error(f"Échec ajout image {img['id']} à la catégorie {state.target_category['id']}")
                state.stats['errors'] += 1
    else:
        logger.info(f"Image {img['id']}: Aucune collection trouvée dans Wikidata")

    # Marque l'image comme traitée
    state.mark_image_processed(img['id'])
    state.stats['processed'] += 1
    state.save_progress()


def process_images():
    """Traitement principal des images avec chargement progressif par lots"""
    piwigo = PiwigoAPI(PIWIGO_API, PIWIGO_USERNAME, PIWIGO_PASSWORD)

    if not piwigo.login():
        logger.error("Échec de connexion à Piwigo")
        return

    state.pwg_id = piwigo.pwg_id

    # Construction de la table de correspondance (ou chargement depuis la sauvegarde)
    collection_mapping = build_collection_mapping(piwigo)

    # Récupération du nombre total d'images pour l'affichage
    total_images = piwigo.get_total_images_count(80, recursive=True)
    state.total_images = total_images
    already_processed = len(state.processed_images)

    logger.info(f"Total: {total_images} images, Déjà traitées: {already_processed}, Restantes: {total_images - already_processed}")

    # Traitement par lots
    page = state.current_batch
    has_more = True

    while has_more and state.running:
        # Chargement d'un lot d'images
        logger.info(f"=== Chargement du lot {page} ({BATCH_SIZE} images max) ===")
        images, has_more = piwigo.get_category_images_batch(80, page, BATCH_SIZE, recursive=True)

        if not images:
            logger.info("Aucune image à traiter dans ce lot, fin du traitement")
            break

        logger.info(f"Lot {page} chargé: {len(images)} images")

        # Traitement de chaque image du lot
        for img in images:
            if not state.running:
                break

            # Skip si déjà traitée
            if state.is_image_processed(img['id']):
                logger.info(f"Image {img['id']} déjà traitée, passage à la suivante")
                continue

            # Pause si demandée
            while state.paused and state.running:
                time.sleep(0.5)

            if not state.running:
                break

            # Traitement de l'image
            process_single_image(piwigo, img, collection_mapping)

            logger.info(f"Image {img['id']} traitée ({state.stats['processed']}/{total_images})")

        # Passage au lot suivant
        page += 1
        state.current_batch = page
        state.save_progress()

        if not state.running:
            break

        if has_more:
            logger.info(f"Lot {page-1} terminé, passage au lot suivant...")
        else:
            logger.info("Tous les lots ont été traités")

    with state.lock:
        state.running = False
        state.current_image = None

    logger.info("Traitement terminé")


# Application Flask
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Synchronisation Piwigo-Wikidata</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; padding: 20px; }
        .controls { margin-bottom: 20px; }
        button { padding: 10px 20px; margin-right: 10px; font-size: 16px; cursor: pointer; }
        .stats { background: #f0f0f0; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .image-container { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .image-container img { max-width: 400px; max-height: 400px; }
        .info { margin: 10px 0; }
        .label { font-weight: bold; }
        .collection { background: #e8f5e9; padding: 10px; border-radius: 3px; margin: 10px 0; }
        .category { background: #fff3e0; padding: 10px; border-radius: 3px; margin: 10px 0; }
        .status { padding: 5px 10px; border-radius: 3px; display: inline-block; }
        .running { background: #4caf50; color: white; }
        .paused { background: #ff9800; color: white; }
        .stopped { background: #f44336; color: white; }
        .batch-info { background: #e3f2fd; padding: 10px; border-radius: 3px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>Synchronisation Piwigo-Wikidata - Collections</h1>
    <p><strong>Mode de traitement:</strong> Chargement progressif par lots de 100 images</p>

    <div class="controls">
        <button onclick="start()">Démarrer</button>
        <button onclick="pause()">Pause</button>
        <button onclick="stop()">Arrêter</button>
        <span id="status" class="status stopped">Arrêté</span>
    </div>

    <div class="stats">
        <h3>Statistiques</h3>
        <div class="batch-info">Lot actuel: <span id="current_batch">0</span></div>
        <div>Images totales dans la catégorie: <span id="total_images">0</span></div>
        <div>Images déjà traitées au démarrage: <span id="already_processed">0</span></div>
        <div>Images traitées dans cette session: <span id="processed">0</span></div>
        <div>Avec collection: <span id="with_collection">0</span></div>
        <div>Catégories créées: <span id="categories_created">0</span></div>
        <div>Erreurs: <span id="errors">0</span></div>
        <div>Progression: <span id="progress">0%</span></div>
    </div>

    <div id="current" class="image-container">
        <h3>Image en cours</h3>
        <div id="image-content">Aucune image en traitement</div>
    </div>

    <script>
        function updateStatus() {
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('current_batch').textContent = data.current_batch;
                    document.getElementById('total_images').textContent = data.total_images;
                    document.getElementById('already_processed').textContent = data.already_processed;
                    document.getElementById('processed').textContent = data.stats.processed;
                    document.getElementById('with_collection').textContent = data.stats.with_collection;
                    document.getElementById('categories_created').textContent = data.stats.categories_created;
                    document.getElementById('errors').textContent = data.stats.errors;
                    
                    if (data.total_images > 0) {
                        const percent = ((data.already_processed + data.stats.processed) / data.total_images * 100).toFixed(1);
                        document.getElementById('progress').textContent = percent + '%';
                    }

                    const statusEl = document.getElementById('status');
                    if (data.running) {
                        if (data.paused) {
                            statusEl.textContent = 'En pause';
                            statusEl.className = 'status paused';
                        } else {
                            statusEl.textContent = 'En cours';
                            statusEl.className = 'status running';
                        }
                    } else {
                        statusEl.textContent = 'Arrêté';
                        statusEl.className = 'status stopped';
                    }

                    if (data.current_image) {
                        let html = '<img src="' + data.current_image.element_url + '">';
                        html += '<div class="info"><span class="label">ID:</span> ' + data.current_image.id + '</div>';
                        html += '<div class="info"><span class="label">Nom:</span> ' + data.current_image.name + '</div>';
                        html += '<div class="info"><span class="label">Catégories:</span> ' + data.current_categories.join(', ') + '</div>';

                        if (data.found_collection) {
                            html += '<div class="collection">';
                            html += '<span class="label">Collection trouvée:</span> ' + data.found_collection.label;
                            html += ' (' + data.found_collection.qid + ')';
                            html += '</div>';
                        }

                        if (data.target_category) {
                            html += '<div class="category">';
                            html += '<span class="label">Catégorie cible:</span> ' + data.target_category.name;
                            html += data.target_category.exists ? ' (existe)' : ' (à créer)';
                            html += '</div>';
                        }

                        document.getElementById('image-content').innerHTML = html;
                    } else {
                        document.getElementById('image-content').innerHTML = 'Aucune image en traitement';
                    }
                });
        }

        function start() {
            fetch('/start', {method: 'POST'});
        }

        function pause() {
            fetch('/pause', {method: 'POST'});
        }

        function stop() {
            fetch('/stop', {method: 'POST'});
        }

        setInterval(updateStatus, 1000);
        updateStatus();
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/status')
def status():
    with state.lock:
        already_processed = len(state.processed_images)

        return jsonify({
            'running': state.running,
            'paused': state.paused,
            'current_image': state.current_image,
            'current_categories': state.current_categories,
            'found_collection': state.found_collection,
            'target_category': state.target_category,
            'stats': state.stats,
            'already_processed': already_processed,
            'total_images': state.total_images,
            'current_batch': state.current_batch
        })


@app.route('/start', methods=['POST'])
def start():
    if not state.running:
        state.running = True
        state.paused = False
        Thread(target=process_images, daemon=True).start()
    elif state.paused:
        state.paused = False
    return jsonify({'status': 'ok'})


@app.route('/pause', methods=['POST'])
def pause():
    state.paused = not state.paused
    return jsonify({'status': 'ok'})


@app.route('/stop', methods=['POST'])
def stop():
    state.running = False
    state.paused = False
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("Serveur démarré sur http://localhost:5000")
    print("Configurez vos identifiants Piwigo dans le code avant de lancer")
    print(f"Traitement par lots de {BATCH_SIZE} images")
    app.run(debug=False, port=5000)