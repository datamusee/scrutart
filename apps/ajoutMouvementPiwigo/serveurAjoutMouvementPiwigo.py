"""
Synchroniseur Piwigo-Wikidata pour les mouvements artistiques
Traite les images de la catégorie 80 et les associe aux mouvements (catégorie 853)
Version avec chargement progressif par lots - adapté pour mouvements multiples
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
SAVE_FILE = "piwigo_wikidata_movements.json"
VERSION_NUMBER = 1

# Configuration du traitement par lots
BATCH_SIZE = 100
SAVE_EVERY_N_IMAGES = 10

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Regex pour extraire le QID Wikidata
QID_REGEX = r'lément Wikidata[^<]*<a[^>]+href=["\']([^"\']*wikidata\.org/(?:wiki|entity)/(Q\d+))["\'][^>]*>([^<]*)</a>'


class ProcessState:
    def __init__(self):
        self.running = False
        self.paused = False
        self.waiting_for_validation = False  # NOUVEAU
        self.validation_received = False  # NOUVEAU
        self.validated_movements = []  # NOUVEAU
        self.apply_to_creator_works = False  # NOUVEAU: appliquer à toutes les œuvres du créateur
        self.current_creator_qid = None  # NOUVEAU: QID du créateur de l'œuvre courante
        self.current_image = None
        self.current_categories = []
        self.found_movements = []
        self.target_categories = []
        self.stats = {
            'processed': 0,
            'with_movements': 0,
            'categories_created': 0,
            'errors': 0,
            'auto_skipped': 0,
            'auto_applied_from_creator': 0  # NOUVEAU
        }
        self.lock = Lock()
        self.pwg_id = None

        # Mémorisation pour reprise
        self.processed_images: Dict[str, Dict] = {}
        self.movement_mapping: Dict[str, Dict] = {}
        self.creator_movements_cache: Dict[str, List[str]] = {}  # NOUVEAU: {creator_qid: [movement_qids]}
        self.total_images = 0
        self.current_batch = 0
        self.version = VERSION_NUMBER
        self.images_since_last_save = 0
        self.load_progress()

    def load_progress(self):
        """Charge la progression sauvegardée"""
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.processed_images = data.get('processed_images', {})
                self.movement_mapping = data.get('movement_mapping', {})
                self.creator_movements_cache = data.get('creator_movements_cache', {})  # NOUVEAU
                self.stats = data.get('stats', self.stats)
                self.current_batch = data.get('current_batch', 0)
                logger.info(f"Progression chargée: {len(self.processed_images)} images")
                logger.info(f"Cache créateurs: {len(self.creator_movements_cache)} créateurs")
            except Exception as e:
                logger.error(f"Erreur chargement progression: {e}")

    def save_progress(self):
        """Sauvegarde la progression"""
        try:
            data = {
                'version': VERSION_NUMBER,
                'processed_images': self.processed_images,
                'movement_mapping': self.movement_mapping,
                'creator_movements_cache': self.creator_movements_cache,  # NOUVEAU
                'stats': self.stats,
                'current_batch': self.current_batch,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde progression: {e}")

    def mark_image_processed(self, image_id: int, qid: str = 'unknown', movements: List[str] = None):
        """Marque une image comme traitée avec ses mouvements"""
        with self.lock:
            self.processed_images[str(image_id)] = {
                'qid': qid,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'movements': movements if movements else []  # Liste de QIDs de mouvements
            }
            self.images_since_last_save += 1

            if self.images_since_last_save >= SAVE_EVERY_N_IMAGES:
                self.save_progress()
                self.images_since_last_save = 0
                logger.info(f"Sauvegarde périodique effectuée")

    def force_save(self):
        """Force une sauvegarde immédiate"""
        with self.lock:
            self.save_progress()
            self.images_since_last_save = 0

    def is_image_processed(self, image_id: int) -> bool:
        """Vérifie si une image a déjà été traitée"""
        return str(image_id) in self.processed_images

    def update_movement_mapping(self, movement_name: str, piwigo_id: int, qid: str):
        """Met à jour le mapping d'un mouvement"""
        self.movement_mapping[movement_name.lower()] = {
            'piwigo_id': piwigo_id,
            'qid': qid,
            'type': 'mouvement'
        }


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
            text = response.text
            json_start = text.find('{')
            if json_start > 0:
                text = text[json_start:]

            result = json.loads(text)
            if result['stat'] == 'ok':
                self.pwg_id = self.session.cookies.get('pwg_id')
                self.pwg_token = self._get_token()
                logger.info("Connexion Piwigo réussie")
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur connexion Piwigo: {e}")
            return False

    def _get_token(self) -> Optional[str]:
        """Récupère le token pwg"""
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
        """Récupère un lot d'images"""
        try:
            response = self.session.post(self.url, data={
                'method': 'pwg.categories.getImages',
                'cat_id': cat_id,
                'recursive': str(recursive).lower(),
                'per_page': per_page,
                'page': page
            })
            text = response.text
            json_start = text.find('{')
            if json_start > 0:
                text = text[json_start:]

            result = json.loads(text)
            if result['stat'] == 'ok':
                images = result['result']['images']
                has_more = len(images) >= per_page
                logger.info(f"Lot {page}: {len(images)} images récupérées")
                return images, has_more
            return [], False
        except Exception as e:
            logger.error(f"Erreur récupération lot {page}: {e}")
            return [], False

    def get_total_images_count(self, cat_id: int, recursive: bool = True) -> int:
        """Récupère le nombre total d'images"""
        try:
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
                total = result['result']['paging'].get('total_count', 0)
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
        if name[0] == 'Q':
            return None  # Pas de vrai nom
        try:
            response = self.session.post(self.url, data={
                'method': 'pwg.categories.add',
                'name': name,
                'status': 'private',
                'parent': parent_id,
                'pwg_token': self.pwg_token
            })
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

    REQUEST_DELAY = 1.0
    _last_request_time = 0
    _lock = Lock()

    HEADERS = {
        'User-Agent': 'PiwigoWikidataSync/1.0 (https://galeries.grains-de-culture.fr; contact@example.com) Python/requests'
    }

    @staticmethod
    def get_creator(qid: str) -> Optional[str]:
        """Récupère le créateur (P170) d'une œuvre"""
        try:
            WikidataAPI._wait_before_request()

            url = "https://www.wikidata.org/w/api.php"
            params = {
                'action': 'wbgetclaims',
                'entity': qid,
                'property': 'P170',
                'format': 'json'
            }
            response = requests.get(url, params=params, headers=WikidataAPI.HEADERS)
            data = response.json()

            if 'claims' in data and 'P170' in data['claims']:
                creator_claim = data['claims']['P170'][0]
                try:
                    creator_qid = creator_claim['mainsnak']['datavalue']['value']['id']
                    return creator_qid
                except (KeyError, TypeError):
                    pass

            return None
        except Exception as e:
            logger.error(f"Erreur récupération créateur pour {qid}: {e}")
            return None

    @staticmethod
    def _wait_before_request():
        """Respecte le délai minimum entre requêtes"""
        with WikidataAPI._lock:
            elapsed = time.time() - WikidataAPI._last_request_time
            if elapsed < WikidataAPI.REQUEST_DELAY:
                time.sleep(WikidataAPI.REQUEST_DELAY - elapsed)
            WikidataAPI._last_request_time = time.time()

    @staticmethod
    def get_movements(qid: str) -> List[Dict]:
        """
        Récupère les mouvements (P135) d'une entité Wikidata
        Cherche d'abord sur l'œuvre, sinon sur son créateur (P170)
        """
        try:
            WikidataAPI._wait_before_request()

            url = "https://www.wikidata.org/w/api.php"

            # Tentative 1: Chercher P135 directement sur l'œuvre
            params = {
                'action': 'wbgetclaims',
                'entity': qid,
                'property': 'P135',
                'format': 'json'
            }
            response = requests.get(url, params=params, headers=WikidataAPI.HEADERS)
            data = response.json()

            movements = []
            if 'claims' in data and 'P135' in data['claims']:
                for claim in data['claims']['P135']:
                    try:
                        movement_qid = claim['mainsnak']['datavalue']['value']['id']
                        label = WikidataAPI.get_label(movement_qid, 'fr')
                        if not label or label == movement_qid:
                            label = WikidataAPI.get_label(movement_qid, 'en')
                        movements.append({
                            'qid': movement_qid,
                            'label': label
                        })
                    except (KeyError, TypeError):
                        continue

            # Si aucun mouvement trouvé, chercher via le créateur
            if not movements:
                logger.info(f"Aucun P135 direct sur {qid}, recherche via créateur (P170)")
                WikidataAPI._wait_before_request()

                # Récupérer le créateur (P170)
                params_creator = {
                    'action': 'wbgetclaims',
                    'entity': qid,
                    'property': 'P170',
                    'format': 'json'
                }
                response_creator = requests.get(url, params=params_creator, headers=WikidataAPI.HEADERS)
                data_creator = response_creator.json()

                if 'claims' in data_creator and 'P170' in data_creator['claims']:
                    # Prendre le premier créateur
                    creator_claim = data_creator['claims']['P170'][0]
                    try:
                        creator_qid = creator_claim['mainsnak']['datavalue']['value']['id']
                        logger.info(f"Créateur trouvé: {creator_qid}")

                        # Chercher P135 sur le créateur
                        WikidataAPI._wait_before_request()
                        params_creator_movements = {
                            'action': 'wbgetclaims',
                            'entity': creator_qid,
                            'property': 'P135',
                            'format': 'json'
                        }
                        response_movements = requests.get(url, params=params_creator_movements, headers=WikidataAPI.HEADERS)
                        data_movements = response_movements.json()

                        if 'claims' in data_movements and 'P135' in data_movements['claims']:
                            for claim in data_movements['claims']['P135']:
                                try:
                                    movement_qid = claim['mainsnak']['datavalue']['value']['id']
                                    label = WikidataAPI.get_label(movement_qid, 'fr')
                                    if not label or label == movement_qid:
                                        label = WikidataAPI.get_label(movement_qid, 'en')
                                    movements.append({
                                        'qid': movement_qid,
                                        'label': label
                                    })
                                    logger.info(f"Mouvement du créateur: {label} ({movement_qid})")
                                except (KeyError, TypeError):
                                    continue
                    except (KeyError, TypeError):
                        pass

            return movements
        except Exception as e:
            logger.error(f"Erreur récupération mouvements pour {qid}: {e}")
            return []

    @staticmethod
    def get_label(qid: str, lang: str = 'fr') -> str:
        """Récupère le label d'une entité"""
        try:
            WikidataAPI._wait_before_request()

            url = "https://www.wikidata.org/w/api.php"
            languages = lang if lang == 'en' else f"{lang}|en"

            params = {
                'action': 'wbgetentities',
                'ids': qid,
                'props': 'labels',
                'languages': languages,
                'format': 'json'
            }
            response = requests.get(url, params=params, headers=WikidataAPI.HEADERS)
            data = response.json()

            if 'entities' in data and qid in data['entities']:
                entity = data['entities'][qid]

                if 'labels' in entity:
                    labels = entity['labels']

                    if lang in labels:
                        return labels[lang]['value']

                    if 'en' in labels:
                        return labels['en']['value']

                    if labels:
                        first_lang = next(iter(labels))
                        return labels[first_lang]['value']

            return qid

        except Exception as e:
            logger.error(f"Erreur récupération label pour {qid}: {e}")
            return qid


def extract_qid_from_description(description: str) -> Optional[str]:
    """Extrait le QID Wikidata de la description"""
    if description:
        match = re.search(QID_REGEX, description)
        if match:
            return match.group(2)
    return None


def build_movement_mapping(piwigo: PiwigoAPI) -> Dict[str, Dict]:
    """Construit la table de correspondance mouvements -> catégories"""
    categories = piwigo.get_categories()
    piwigo_movements = {}

    for cat in categories:
        if '853' in cat.get('uppercats'):  # CHANGEMENT: 853 au lieu de 854
            piwigo_movements[cat['name'].lower()] = {
                'piwigo_id': int(cat['id']),
                'qid': None,
                'type': 'mouvement'
            }

    logger.info(f"Catégories Piwigo trouvées: {len(piwigo_movements)}")

    if state.movement_mapping:
        logger.info(f"Table sauvegardée: {len(state.movement_mapping)} entrées")

        missing_in_file = []
        for mov_name, mov_info in piwigo_movements.items():
            if mov_name not in state.movement_mapping:
                missing_in_file.append(mov_name)
                state.movement_mapping[mov_name] = mov_info

        if missing_in_file:
            logger.info(f"⚠️  {len(missing_in_file)} catégories absentes du fichier:")
            for mov_name in missing_in_file:
                logger.info(f"   + {mov_name}")
            state.force_save()

        return state.movement_mapping
    else:
        state.movement_mapping = piwigo_movements
        state.force_save()
        logger.info(f"Table de correspondance construite: {len(piwigo_movements)} mouvements")
        return piwigo_movements


def process_single_image(piwigo: PiwigoAPI, img: Dict, movement_mapping: Dict[str, Dict]) -> None:
    """Traite une seule image - avec validation humaine si mouvements trouvés"""
    img_info = piwigo.get_image_info(img['id'])
    if not img_info:
        state.mark_image_processed(img['id'], 'error', [])
        state.stats['errors'] += 1
        return

    description = img_info.get('comment', '')
    qid = extract_qid_from_description(description)

    # Vérifier si déjà dans une sous-catégorie de 853
    categories = img_info.get('categories', [])
    already_in_movement = False
    for cat in categories:
        if '853' in cat.get('uppercats'):
            logger.info(f"Image {img['id']} déjà dans '{cat['name']}', skip automatique")
            state.mark_image_processed(img['id'], qid, [cat.get('name', 'unknown')])
            state.stats['processed'] += 1
            state.stats['with_movements'] += 1
            state.stats['auto_skipped'] += 1
            already_in_movement = True
            break

    if already_in_movement:
        return

    with state.lock:
        state.current_image = img_info
        state.current_categories = [cat['name'] for cat in categories]
        state.found_movements = []
        state.target_categories = []

    if not qid:
        logger.info(f"Image {img['id']} sans QID, skip automatique")
        state.mark_image_processed(img['id'], 'none', [])
        state.stats['processed'] += 1
        state.stats['auto_skipped'] += 1
        return

    # Récupérer les mouvements
    movements = WikidataAPI.get_movements(qid)

    if not movements:
        logger.info(f"Image {img['id']}: Aucun mouvement trouvé, skip automatique")
        state.mark_image_processed(img['id'], qid, [])
        state.stats['processed'] += 1
        state.stats['auto_skipped'] += 1
        return

    # Mouvements trouvés → PAUSE POUR VALIDATION
    state.stats['with_movements'] += 1
    movement_qids = []

    with state.lock:
        state.found_movements = movements
        state.target_categories = []
        state.waiting_for_validation = True
        state.validation_received = False
        state.validated_movements = []

    for movement in movements:
        movement_label_lower = movement['label'].lower()
        movement_qids.append(movement['qid'])

        if movement_label_lower in movement_mapping:
            mov_info = movement_mapping[movement_label_lower]
            with state.lock:
                state.target_categories.append({
                    'id': mov_info['piwigo_id'],
                    'name': movement['label'],
                    'qid': movement['qid'],
                    'exists': True
                })
            if True:
                state.update_movement_mapping(movement['label'], mov_info['piwigo_id'], movement['qid'])
        else:
            with state.lock:
                state.target_categories.append({
                    'id': None,
                    'name': movement['label'],
                    'qid': movement['qid'],
                    'exists': False
                })

    logger.info(f"Image {img['id']}: {len(movements)} mouvement(s) trouvé(s) - EN ATTENTE DE VALIDATION")

    # ATTENTE DE VALIDATION
    while state.waiting_for_validation and state.running:
        time.sleep(0.5)

    if not state.running:
        return

    # Si validation reçue avec mouvements sélectionnés
    if state.validation_received and state.validated_movements:
        logger.info(f"Validation reçue: {len(state.validated_movements)} mouvement(s) sélectionné(s)")

        # Ne traiter que les mouvements validés
        validated_qids = []
        for validated_mov in state.validated_movements:
            # Trouver la catégorie correspondante
            target = None
            for cat in state.target_categories:
                if cat['qid'] == validated_mov['qid']:
                    target = cat
                    break

            if not target:
                continue

            validated_qids.append(validated_mov['qid'])

            # Créer la catégorie si nécessaire
            if not target['exists']:
                cat_id = piwigo.create_category(target['name'], 853)
                if cat_id:
                    movement_mapping[target['name'].lower()] = {
                        'piwigo_id': cat_id,
                        'qid': target['qid'],
                        'type': 'mouvement'
                    }
                    with state.lock:
                        state.update_movement_mapping(target['name'], cat_id, target['qid'])
                        target['id'] = cat_id
                        state.stats['categories_created'] += 1

            # Associer l'image
            if target['id']:
                success = piwigo.add_image_to_category(img['id'], target['id'])
                if success:
                    logger.info(f"Image {img['id']} → catégorie {target['id']} ({target['name']})")
                else:
                    logger.error(f"Échec ajout image {img['id']} → {target['id']}")

        state.mark_image_processed(img['id'], qid, validated_qids)
    else:
        # Bouton "Passer" cliqué ou aucun mouvement sélectionné
        logger.info(f"Image {img['id']} passée sans association")
        state.mark_image_processed(img['id'], qid, [])

    state.stats['processed'] += 1


def process_images():
    """Traitement principal"""
    piwigo = PiwigoAPI(PIWIGO_API, PIWIGO_USERNAME, PIWIGO_PASSWORD)

    if not piwigo.login():
        logger.error("Échec connexion Piwigo")
        return

    state.pwg_id = piwigo.pwg_id

    movement_mapping = build_movement_mapping(piwigo)

    total_images = piwigo.get_total_images_count(80, recursive=True)
    state.total_images = total_images

    already_processed = len(state.processed_images)

    with state.lock:
        state.stats['processed'] = 0

    logger.info(f"📊 État au démarrage:")
    logger.info(f"   Total: {total_images}")
    logger.info(f"   Déjà traitées: {already_processed}")
    logger.info(f"   Restantes: {total_images - already_processed}")
    logger.info(f"   Mouvements mappés: {len(movement_mapping)}")

    page = state.current_batch
    has_more = True

    while has_more and state.running:
        logger.info(f"=== Lot {page} ===")
        images, has_more = piwigo.get_category_images_batch(80, page, BATCH_SIZE, recursive=True)

        if not images:
            break

        for img in images:
            if not state.running:
                break

            if state.is_image_processed(img['id']):
                continue

            while state.paused and state.running:
                time.sleep(0.5)

            if not state.running:
                break

            process_single_image(piwigo, img, movement_mapping)

        page += 1
        state.current_batch = page
        state.force_save()

        if not state.running:
            break

    state.force_save()

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
    <title>Synchronisation Piwigo-Wikidata Mouvements</title>
    <meta charset="utf-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .piwigo-image {
            max-width: 30vw;
            max-height: 30vh;
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
            margin: auto;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            gap: 20px;
        }
        .main-content { flex: 1; min-width: 600px; }
        .sidebar { width: 380px; display: flex; flex-direction: column; gap: 20px; }
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 { color: #333; margin-bottom: 10px; font-size: 26px; }
        h2 { color: #667eea; margin-bottom: 15px; font-size: 18px; border-bottom: 2px solid #667eea; padding-bottom: 8px; }
        .subtitle { color: #666; margin-bottom: 20px; font-size: 14px; }
        .controls { margin-bottom: 20px; display: flex; gap: 10px; align-items: center; }
        button { 
            padding: 12px 24px; font-size: 15px; cursor: pointer; border: none;
            border-radius: 8px; font-weight: 600; transition: all 0.3s;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        button:first-child { background: linear-gradient(135deg, #4caf50, #45a049); color: white; }
        button:nth-child(2) { background: linear-gradient(135deg, #ff9800, #f57c00); color: white; }
        button:nth-child(3) { background: linear-gradient(135deg, #f44336, #d32f2f); color: white; }
        .status { padding: 8px 16px; border-radius: 20px; display: inline-block; font-weight: 600; font-size: 14px; }
        .running { background: #4caf50; color: white; }
        .paused { background: #ff9800; color: white; }
        .stopped { background: #f44336; color: white; }
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px; border-radius: 10px; text-align: center;
        }
        .stat-number { font-size: 32px; font-weight: bold; display: block; margin-bottom: 5px; }
        .stat-label { font-size: 13px; opacity: 0.9; }
        .batch-info { background: #e3f2fd; padding: 12px; border-radius: 8px; margin-bottom: 15px; color: #1976d2; font-weight: 600; }
        .image-container { background: #f8f9fa; padding: 20px; border-radius: 10px; }
        .image-container img { max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 15px; }
        .info { margin: 10px 0; padding: 8px; background: white; border-radius: 5px; }
        .label { font-weight: bold; color: #667eea; }
        .movement { background: #e8f5e9; padding: 12px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #4caf50; }
        .movement-list { margin: 10px 0; }
        .movement-item { background: #fff3e0; padding: 8px 12px; border-radius: 6px; margin: 5px 0; border-left: 3px solid #ff9800; }
        .category { background: #fff3e0; padding: 12px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #ff9800; }
        .qid-link, .piwigo-link {
            color: #667eea; text-decoration: none; font-weight: 600;
            padding: 2px 6px; border-radius: 4px; background: #e8eaf6;
            display: inline-block; margin-left: 5px;
        }
        .qid-link:hover, .piwigo-link:hover { background: #c5cae9; text-decoration: underline; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #e0e0e0; }
        th { background: #f5f5f5; color: #667eea; font-weight: 600; }
        tr:hover { background: #f8f9fa; }
        .version-info {
            font-size: 11px; color: #999; text-align: center;
            padding: 10px; background: #f5f5f5; border-radius: 8px;
        }
        .recent-images { max-height: 400px; overflow-y: auto; }
        .recent-images::-webkit-scrollbar { width: 8px; }
        .recent-images::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
        .recent-images::-webkit-scrollbar-thumb { background: #667eea; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="main-content">
            <div class="card">
                <h1>🎨 Synchronisation Piwigo-Wikidata Mouvements</h1>
                <p class="subtitle"><strong>Mode:</strong> Chargement progressif par lots de {{ batch_size }} images</p>

                <div class="controls">
                    <button onclick="start()">▶ Démarrer</button>
                    <button onclick="pause()">⏸ Pause</button>
                    <button onclick="stop()">⏹ Arrêter</button>
                    <span id="status" class="status stopped">Arrêté</span>
                </div>
            </div>
            
            <div class="card">
                <h2>🖼️ Image en cours de traitement</h2>
                <div id="current" class="image-container">
                    <div id="image-content">Aucune image en traitement</div>
                </div>
            </div>
            
            <div class="card">
                <h2>📋 Dernières images traitées</h2>
                <div class="recent-images">
                    <table id="recent-table">
                        <thead>
                            <tr>
                                <th>Image</th>
                                <th>QID Wikidata</th>
                                <th>Mouvements</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody id="recent-tbody">
                            <tr><td colspan="4" style="text-align: center; color: #999;">Aucune image traitée</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div class="sidebar">
            <div class="card">
                <h2>📊 Statistiques</h2>
                
                <div class="batch-info">
                    Lot actuel: <span id="current_batch">0</span>
                </div>
                
                <div class="stat-box" style="margin-bottom: 15px;">
                    <span class="stat-number" id="total_images">0</span>
                    <span class="stat-label">Images totales</span>
                </div>
                
                <div class="stat-box" style="margin-bottom: 15px; background: linear-gradient(135deg, #4caf50, #45a049);">
                    <span class="stat-number" id="already_processed">0</span>
                    <span class="stat-label">Déjà traitées</span>
                </div>
                
                <div class="stat-box" style="margin-bottom: 15px; background: linear-gradient(135deg, #2196f3, #1976d2);">
                    <span class="stat-number" id="processed">0</span>
                    <span class="stat-label">Session actuelle</span>
                </div>
                
                <div class="stat-box" style="margin-bottom: 15px; background: linear-gradient(135deg, #ff9800, #f57c00);">
                    <span class="stat-number" id="with_movements">0</span>
                    <span class="stat-label">Avec mouvements</span>
                </div>
                
                <div class="stat-box" style="margin-bottom: 15px; background: linear-gradient(135deg, #9c27b0, #7b1fa2);">
                    <span class="stat-number" id="categories_created">0</span>
                    <span class="stat-label">Catégories créées</span>
                </div>
                
                <div class="stat-box" style="margin-bottom: 15px; background: linear-gradient(135deg, #607d8b, #455a64);">
                    <span class="stat-number" id="auto_skipped">0</span>
                    <span class="stat-label">Passées automatiquement</span>
                </div>
                
                <div class="stat-box" style="margin-bottom: 15px; background: linear-gradient(135deg, #00bcd4, #0097a7);">
                    <span class="stat-number" id="auto_applied_from_creator">0</span>
                    <span class="stat-label">Appliquées depuis créateur</span>
                </div>
                
                <div class="stat-box" style="background: linear-gradient(135deg, #f44336, #d32f2f);">
                    <span class="stat-number" id="errors">0</span>
                    <span class="stat-label">Erreurs</span>
                </div>
                
                <div style="margin-top: 15px; padding: 12px; background: #e8f5e9; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #4caf50;">
                        <span id="progress">0%</span>
                    </div>
                    <div style="font-size: 12px; color: #2e7d32; margin-top: 5px;">
                        Progression totale
                    </div>
                </div>
                
                <div class="version-info">
                    Version {{ version }}<br>
                    Dernière MAJ: <span id="last_updated">-</span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const PIWIGO_URL = "{{ piwigo_url }}";
        
        function updateStatus() {
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('current_batch').textContent = data.current_batch;
                    document.getElementById('total_images').textContent = data.total_images;
                    document.getElementById('already_processed').textContent = data.already_processed;
                    document.getElementById('processed').textContent = data.stats.processed;
                    document.getElementById('with_movements').textContent = data.stats.with_movements;
                    document.getElementById('categories_created').textContent = data.stats.categories_created;
                    document.getElementById('auto_skipped').textContent = data.stats.auto_skipped;
                    document.getElementById('auto_applied_from_creator').textContent = data.stats.auto_applied_from_creator;
                    document.getElementById('errors').textContent = data.stats.errors;
                    
                    if (data.total_images > 0) {
                        const percent = ((data.already_processed) / data.total_images * 100).toFixed(1);
                        document.getElementById('progress').textContent = percent + '%';
                    }

                    const statusEl = document.getElementById('status');
                    if (data.running) {
                        if (data.paused) {
                            statusEl.textContent = '⏸ En pause';
                            statusEl.className = 'status paused';
                        } else {
                            statusEl.textContent = '▶ En cours';
                            statusEl.className = 'status running';
                        }
                    } else {
                        statusEl.textContent = '⏹ Arrêté';
                        statusEl.className = 'status stopped';
                    }

                    // Affichage de l'image en cours
                    if (data.current_image) {
                        const piwigoLink = `${PIWIGO_URL}/picture.php?/${data.current_image.id}`;
                        let html = `<a href="${piwigoLink}" target="_blank"><img src="${data.current_image.element_url}" class="piwigo-image"></a>`;
                        html += `<div class="info"><span class="label">ID:</span> <a href="${piwigoLink}" target="_blank" class="piwigo-link">${data.current_image.id}</a></div>`;
                        html += `<div class="info"><span class="label">Nom:</span> ${data.current_image.name}</div>`;
                        html += `<div class="info"><span class="label">Catégories:</span> ${data.current_categories.join(', ')}</div>`;

                        if (data.found_movements && data.found_movements.length > 0) {
                            html += '<div class="movement"><span class="label">Mouvements trouvés:</span><div class="movement-list">';
                            data.found_movements.forEach(mov => {
                                const qidLink = `https://www.wikidata.org/wiki/${mov.qid}`;
                                const checkboxId = `mov_${mov.qid}`;
                                html += `<div class="movement-item">
                                    <input type="checkbox" id="${checkboxId}" value="${mov.qid}" 
                                           data-label="${mov.label}" checked 
                                           ${data.waiting_for_validation ? '' : 'disabled'}
                                           style="margin-right: 8px;">
                                    <label for="${checkboxId}" style="cursor: pointer;">${mov.label}</label>
                                    <a href="${qidLink}" target="_blank" class="qid-link">${mov.qid}</a>
                                </div>`;
                            });
                            html += '</div>';
                            
                            // Boutons de validation
                            if (data.waiting_for_validation) {
                                html += '<div style="margin-top: 15px;">';
                                
                                // Case à cocher pour appliquer au créateur
                                if (data.current_creator_qid) {
                                    html += `<div style="background: #fff3e0; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 3px solid #ff9800;">
                                        <input type="checkbox" id="apply_to_creator" style="margin-right: 8px;">
                                        <label for="apply_to_creator" style="cursor: pointer; font-weight: 600;">
                                            🎨 Appliquer automatiquement à toutes les œuvres du créateur 
                                            <a href="https://www.wikidata.org/wiki/${data.current_creator_qid}" target="_blank" class="qid-link">${data.current_creator_qid}</a>
                                        </label>
                                        <div style="font-size: 12px; color: #666; margin-top: 5px; margin-left: 26px;">
                                            Les prochaines œuvres de ce créateur seront automatiquement associées aux mouvements sélectionnés, sans demande de validation.
                                        </div>
                                    </div>`;
                                }
                                
                                html += `<div style="display: flex; gap: 10px; justify-content: center;">
                                    <button onclick="skipImage()" style="background: linear-gradient(135deg, #757575, #616161); color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
                                        ⏭️ Passer
                                    </button>
                                    <button onclick="validateMovements()" style="background: linear-gradient(135deg, #4caf50, #45a049); color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">
                                        ✓ Vers Piwigo
                                    </button>
                                </div>`;
                                html += '</div>';
                            }
                            
                            html += '</div>';
                        }

                        if (data.target_categories && data.target_categories.length > 0) {
                            html += '<div class="category"><span class="label">Catégories cibles:</span><div class="movement-list">';
                            data.target_categories.forEach(cat => {
                                html += `<div class="movement-item">${cat.name} ${cat.exists ? '✓ (existe)' : '⊕ (à créer)'}</div>`;
                            });
                            html += '</div></div>';
                        }

                        document.getElementById('image-content').innerHTML = html;
                    } else {
                        document.getElementById('image-content').innerHTML = 'Aucune image en traitement';
                    }
                    
                    // Mise à jour des images récentes
                    if (data.recent_images && data.recent_images.length > 0) {
                        let tbody = '';
                        data.recent_images.forEach(img => {
                            const piwigoLink = `${PIWIGO_URL}/picture.php?/${img.id}`;
                            const qidLink = img.qid !== 'unknown' && img.qid !== 'none' && img.qid !== 'error' 
                                ? `<a href="https://www.wikidata.org/wiki/${img.qid}" target="_blank" class="qid-link">${img.qid}</a>`
                                : img.qid;
                            
                            let movementsText = 'N/A';
                            if (img.movements && img.movements.length > 0) {
                                movementsText = img.movements.join(', ');
                            }
                            
                            tbody += `<tr>
                                <td><a href="${piwigoLink}" target="_blank" class="piwigo-link">#${img.id}</a></td>
                                <td>${qidLink}</td>
                                <td>${movementsText}</td>
                                <td>${img.date || 'N/A'}</td>
                            </tr>`;
                        });
                        document.getElementById('recent-tbody').innerHTML = tbody;
                    }
                    
                    if (data.last_updated) {
                        document.getElementById('last_updated').textContent = data.last_updated;
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

        function validateMovements() {
            // Récupérer les mouvements cochés
            const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="mov_"]:checked');
            const movements = [];
            
            checkboxes.forEach(cb => {
                movements.push({
                    qid: cb.value,
                    label: cb.dataset.label
                });
            });
            
            if (movements.length === 0) {
                alert('Veuillez sélectionner au moins un mouvement');
                return;
            }
            
            // Vérifier si la case "Appliquer au créateur" est cochée
            const applyToCreatorCheckbox = document.getElementById('apply_to_creator');
            const applyToCreator = applyToCreatorCheckbox ? applyToCreatorCheckbox.checked : false;
            
            fetch('/validate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    movements: movements,
                    apply_to_creator: applyToCreator
                })
            });
        }

        function skipImage() {
            if (confirm('Passer cette image sans associer de mouvement ?')) {
                fetch('/skip', {method: 'POST'});
            }
        }

        setInterval(updateStatus, 1000);
        updateStatus();
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE,
                                 batch_size=BATCH_SIZE,
                                 version=VERSION_NUMBER,
                                 piwigo_url=PIWIGO_URL)


@app.route('/status')
def status():
    with state.lock:
        already_processed = len(state.processed_images)

        # Récupère les 10 dernières images traitées
        recent_images = []
        for img_id, info in list(state.processed_images.items())[-10:]:
            recent_images.append({
                'id': img_id,
                'qid': info.get('qid', 'unknown'),
                'movements': info.get('movements', []),
                'date': info.get('date', '')[:19]
            })
        recent_images.reverse()

        return jsonify({
            'running': state.running,
            'paused': state.paused,
            'waiting_for_validation': state.waiting_for_validation,
            'current_creator_qid': state.current_creator_qid,
            'current_image': state.current_image,
            'current_categories': state.current_categories,
            'found_movements': state.found_movements,
            'target_categories': state.target_categories,
            'stats': state.stats,
            'already_processed': already_processed,
            'total_images': state.total_images,
            'current_batch': state.current_batch,
            'recent_images': recent_images,
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
        })


@app.route('/validate', methods=['POST'])
def validate():
    """Reçoit la validation des mouvements sélectionnés"""
    data = request.json
    selected_movements = data.get('movements', [])
    apply_to_creator = data.get('apply_to_creator', False)

    with state.lock:
        state.validated_movements = selected_movements
        state.apply_to_creator_works = apply_to_creator
        state.validation_received = True
        state.waiting_for_validation = False

    logger.info(f"Validation reçue: {len(selected_movements)} mouvement(s), apply_to_creator={apply_to_creator}")
    return jsonify({'status': 'ok'})


@app.route('/skip', methods=['POST'])
def skip():
    """Passe l'image sans associer de mouvement"""
    with state.lock:
        state.validated_movements = []
        state.validation_received = False
        state.waiting_for_validation = False

    logger.info("Image passée sans association")
    return jsonify({'status': 'ok'})


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
    print("="*60)
    print("🚀 Serveur de synchronisation Piwigo-Wikidata Mouvements")
    print("="*60)
    print(f"📍 URL: http://localhost:5000")
    print(f"📦 Traitement par lots de {BATCH_SIZE} images")
    print(f"💾 Sauvegarde tous les {SAVE_EVERY_N_IMAGES} images")
    print(f"📄 Format de sauvegarde: Version {VERSION_NUMBER}")
    print(f"💾 Fichier de progression: {SAVE_FILE}")
    print(f"🎨 Catégorie source: 80 (images)")
    print(f"🏛️ Catégorie cible: 853 (mouvements)")

    if os.path.exists(SAVE_FILE):
        print(f"✅ Fichier de progression existant détecté")

        images_count = len(state.processed_images)
        print(f"   📊 {images_count} images déjà traitées")

        movements_count = len(state.movement_mapping)
        print(f"   📚 {movements_count} mouvements mappés")

        movements_with_qid = sum(1 for m in state.movement_mapping.values() if m.get('qid'))
        print(f"   🔗 {movements_with_qid} mouvements avec QID Wikidata")
        print(f"   ⏱️  Lot de reprise: {state.current_batch}")

        # Analyser les images traitées
        with_movements = sum(1 for img in state.processed_images.values()
                           if img.get('movements') and len(img.get('movements', [])) > 0)
        multi_movements = sum(1 for img in state.processed_images.values()
                            if img.get('movements') and len(img.get('movements', [])) > 1)

        print(f"   📈 {with_movements} images avec mouvements")
        print(f"   🔀 {multi_movements} images avec plusieurs mouvements")
    else:
        print(f"ℹ️  Aucun fichier de progression (premier démarrage)")

    print("="*60)
    print("💡 Différences avec les collections:")
    print("   • Une image peut avoir PLUSIEURS mouvements")
    print("   • Propriété P135 au lieu de P195")
    print("   • Catégorie 853 au lieu de 854")
    print("="*60)

    app.run(debug=False, port=5500)