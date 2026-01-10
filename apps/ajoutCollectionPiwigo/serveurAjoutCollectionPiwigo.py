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
VERSION_NUMBER = 2

# Configuration du traitement par lots
BATCH_SIZE = 100  # Nombre d'images à charger et traiter par lot
SAVE_EVERY_N_IMAGES = 10  # Sauvegarder tous les N images traitées

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
        self.processed_images: Dict[str, Dict] = {}  # v2: dict au lieu de set
        self.collection_mapping: Dict[str, Dict] = {}  # v2: dict avec piwigo_id et qid
        self.total_images = 0
        self.current_batch = 0
        self.version = VERSION_NUMBER
        self.images_since_last_save = 0  # Compteur pour sauvegarde périodique
        self.load_progress()

    def load_progress(self):
        """Charge la progression sauvegardée avec migration automatique"""
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                file_version = data.get('version', 1)

                if file_version == VERSION_NUMBER:
                    # Version actuelle, chargement direct
                    self.processed_images = data.get('processed_images', {})
                    self.collection_mapping = data.get('collection_mapping', {})
                    self.stats = data.get('stats', self.stats)
                    self.current_batch = data.get('current_batch', 0)
                    logger.info(f"Progression v{VERSION_NUMBER} chargée: {len(self.processed_images)} images")

                    # Récupération des QID manquants pour les collections
                    self._fetch_missing_collection_qids()
                else:
                    # Migration depuis v1
                    logger.info(f"Migration du fichier de v{file_version} vers v{VERSION_NUMBER}")
                    self._migrate_from_v1(data)
                    logger.info(f"Migration terminée: {len(self.processed_images)} images migrées")
            except Exception as e:
                logger.error(f"Erreur chargement progression: {e}")

    def _fetch_missing_collection_qids(self):
        """Récupère les QID manquants pour les collections depuis Wikidata"""
        collections_to_update = []

        # Identifier les collections sans QID
        for coll_name, coll_info in self.collection_mapping.items():
            if not coll_info.get('qid'):
                collections_to_update.append((coll_name, coll_info))

        if not collections_to_update:
            logger.info("Toutes les collections ont déjà un QID")
            return

        logger.info(f"Récupération des QID pour {len(collections_to_update)} collections...")
        updated_count = 0

        for coll_name, coll_info in collections_to_update:
            # Rechercher le QID via le nom de la collection
            # On cherche d'abord dans les images traitées si une image a cette collection
            qid_found = None

            for img_id, img_info in self.processed_images.items():
                if img_info.get('collection', '').lower() == coll_name:
                    # On a une image de cette collection, utiliser son QID pour chercher
                    artwork_qid = img_info.get('qid')
                    if artwork_qid and artwork_qid not in ['unknown', 'none', 'error']:
                        # Récupérer la collection de cette œuvre
                        collection = WikidataAPI.get_collection(artwork_qid)
                        if collection and collection['label'].lower() == coll_name:
                            qid_found = collection['qid']
                            break

            if qid_found:
                self.collection_mapping[coll_name]['qid'] = qid_found
                updated_count += 1
                logger.info(f"QID trouvé pour '{coll_name}': {qid_found}")

        if updated_count > 0:
            logger.info(f"{updated_count} QID de collections récupérés")
            self.save_progress()
            logger.info("Fichier de progression mis à jour avec les QID des collections")

    def _migrate_from_v1(self, old_data):
        """Migre les données de la version 1 vers la version 2"""
        # Migration de processed_images: list/set -> dict
        old_processed = old_data.get('processed_images', [])

        if isinstance(old_processed, list):
            # Ancienne version v1: simple liste d'IDs
            # On ne peut pas récupérer les QID/collections, on marque comme migrées
            for img_id in old_processed:
                self.processed_images[str(img_id)] = {
                    'qid': 'unknown',
                    'date': 'migrated_v1',
                    'collection': 'unknown'
                }
            logger.info(f"Migration v1: {len(old_processed)} images marquées comme traitées")
        elif isinstance(old_processed, set):
            # Si c'était un set
            for img_id in old_processed:
                self.processed_images[str(img_id)] = {
                    'qid': 'unknown',
                    'date': 'migrated_v1',
                    'collection': 'unknown'
                }
            logger.info(f"Migration v1 (set): {len(old_processed)} images marquées comme traitées")
        elif isinstance(old_processed, dict):
            # Déjà en format dict, mais vérifier la structure
            for img_id, value in old_processed.items():
                if isinstance(value, dict) and 'qid' in value:
                    # Déjà au bon format
                    self.processed_images[str(img_id)] = value
                else:
                    # Format incomplet
                    self.processed_images[str(img_id)] = {
                        'qid': 'unknown',
                        'date': 'migrated_v1',
                        'collection': 'unknown'
                    }
            logger.info(f"Migration v1 (dict): {len(old_processed)} images")

        # Migration de collection_mapping: simple value -> dict avec piwigo_id et qid
        old_mapping = old_data.get('collection_mapping', {})
        for coll_name, value in old_mapping.items():
            if isinstance(value, dict):
                # Vérifier si déjà au bon format
                if 'piwigo_id' in value and 'qid' in value:
                    self.collection_mapping[coll_name] = value
                elif 'piwigo_id' in value:
                    # A piwigo_id mais pas qid
                    self.collection_mapping[coll_name] = {
                        'piwigo_id': value['piwigo_id'],
                        'qid': value.get('qid')  # None si absent
                    }
                else:
                    # Dict mais structure inconnue
                    self.collection_mapping[coll_name] = {
                        'piwigo_id': None,
                        'qid': None
                    }
            elif isinstance(value, int):
                # Ancien format v1: juste l'ID piwigo
                self.collection_mapping[coll_name] = {
                    'piwigo_id': value,
                    'qid': None
                }
            else:
                # Autre format
                self.collection_mapping[coll_name] = {
                    'piwigo_id': None,
                    'qid': None
                }

        logger.info(f"Migration v1: {len(old_mapping)} collections mappées")

        # Migration des stats
        self.stats = old_data.get('stats', self.stats)
        self.current_batch = old_data.get('current_batch', 0)

        # Sauvegarde immédiate du format migré
        self.save_progress()
        logger.info("Migration v1->v2 terminée et sauvegardée")

    def save_progress(self):
        """Sauvegarde la progression au format v2"""
        try:
            data = {
                'version': VERSION_NUMBER,
                'processed_images': self.processed_images,
                'collection_mapping': self.collection_mapping,
                'stats': self.stats,
                'current_batch': self.current_batch,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde progression: {e}")

    def mark_image_processed(self, image_id: int, qid: str = 'unknown', collection: str = 'unknown'):
        """Marque une image comme traitée avec ses métadonnées"""
        with self.lock:
            self.processed_images[str(image_id)] = {
                'qid': qid,
                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'collection': collection
            }
            self.images_since_last_save += 1

            # Sauvegarde tous les N images
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

    def update_collection_mapping(self, collection_name: str, piwigo_id: int, qid: str):
        """Met à jour le mapping d'une collection avec piwigo_id ET qid"""
        # ATTENTION: Cette méthode est appelée depuis process_single_image qui a déjà le lock
        # On ne doit PAS reprendre le lock ici
        self.collection_mapping[collection_name.lower()] = {
            'piwigo_id': piwigo_id,
            'qid': qid
        }
        # Pas de sauvegarde ici, sera fait par mark_image_processed


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


def build_collection_mapping(piwigo: PiwigoAPI) -> Dict[str, Dict]:
    """Construit la table de correspondance collections -> catégories (avec piwigo_id et qid)"""
    # Récupération de toutes les catégories Piwigo sous la catégorie 854
    categories = piwigo.get_categories()
    piwigo_collections = {}

    for cat in categories:
        if '854' in cat.get('uppercats'):  # Sous-catégories de 854
            piwigo_collections[cat['name'].lower()] = {
                'piwigo_id': int(cat['id']),
                'qid': None
            }

    logger.info(f"Catégories Piwigo trouvées: {len(piwigo_collections)}")

    # Si on a une table sauvegardée, la fusionner avec les catégories Piwigo
    if state.collection_mapping:
        logger.info(f"Table sauvegardée: {len(state.collection_mapping)} entrées")

        # Vérifier les catégories manquantes dans le fichier de traces
        missing_in_file = []
        for coll_name, coll_info in piwigo_collections.items():
            if coll_name not in state.collection_mapping:
                missing_in_file.append(coll_name)
                # Ajouter la catégorie manquante
                state.collection_mapping[coll_name] = coll_info

        if missing_in_file:
            logger.info(f"⚠️  {len(missing_in_file)} catégories Piwigo absentes du fichier de traces, ajout en cours:")
            for coll_name in missing_in_file:
                logger.info(f"   + {coll_name}")
            state.force_save()

        # Vérifier les catégories du fichier qui n'existent plus dans Piwigo
        extra_in_file = []
        for coll_name in state.collection_mapping:
            if coll_name not in piwigo_collections:
                extra_in_file.append(coll_name)

        if extra_in_file:
            logger.info(f"ℹ️  {len(extra_in_file)} catégories du fichier n'existent plus dans Piwigo:")
            for coll_name in extra_in_file:
                logger.info(f"   - {coll_name}")

        # Mettre à jour les piwigo_id au cas où ils auraient changé
        updated_count = 0
        for coll_name, piwigo_info in piwigo_collections.items():
            if coll_name in state.collection_mapping:
                if state.collection_mapping[coll_name]['piwigo_id'] != piwigo_info['piwigo_id']:
                    old_id = state.collection_mapping[coll_name]['piwigo_id']
                    state.collection_mapping[coll_name]['piwigo_id'] = piwigo_info['piwigo_id']
                    updated_count += 1
                    logger.info(f"   ID mis à jour pour '{coll_name}': {old_id} -> {piwigo_info['piwigo_id']}")

        if updated_count > 0:
            logger.info(f"🔄 {updated_count} ID de catégories mis à jour")
            state.force_save()

        return state.collection_mapping
    else:
        # Pas de sauvegarde, utiliser les catégories Piwigo
        state.collection_mapping = piwigo_collections
        state.force_save()
        logger.info(f"Table de correspondance construite: {len(piwigo_collections)} catégories de collection")
        return piwigo_collections


def process_single_image(piwigo: PiwigoAPI, img: Dict, collection_mapping: Dict[str, Dict]) -> None:
    """Traite une seule image"""
    # Récupération des infos détaillées
    img_info = piwigo.get_image_info(img['id'])
    if not img_info:
        state.mark_image_processed(img['id'], 'error', 'error')
        state.stats['errors'] += 1
        logger.warning(f"Impossible de récupérer les infos de l'image {img['id']}, passage à la suivante")
        return

    # Vérifier si l'image est déjà dans une sous-catégorie de 854 (collections)
    categories = img_info.get('categories', [])
    for cat in categories:
        if '854' in cat.get('uppercats'):  # Sous-catégories de 854
            logger.info(f"Image {img['id']} déjà dans la sous-catégorie '{cat['name']}' de 854, passage à la suivante")
            state.mark_image_processed(img['id'], 'already_in_collection', cat['name'])
            state.stats['processed'] += 1
            return

    with state.lock:
        state.current_image = img_info
        state.current_categories = [cat['name'] for cat in categories]
        state.found_collection = None
        state.target_category = None

    # Extraction du QID
    description = img_info.get('comment', '')
    qid = extract_qid_from_description(description)

    if not qid:
        state.mark_image_processed(img['id'], 'none', 'none')
        state.stats['processed'] += 1
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
                cat_info = collection_mapping[collection_label_lower]
                state.target_category = {
                    'id': cat_info['piwigo_id'],
                    'name': collection['label'],
                    'exists': True
                }
                # Met à jour le QID dans le mapping si pas encore fait
                if not cat_info.get('qid'):
                    state.update_collection_mapping(collection['label'], cat_info['piwigo_id'], collection['qid'])
                # Pause pour permettre validation
                time.sleep(10)
            else:
                state.target_category = {
                    'id': None,
                    'name': collection['label'],
                    'exists': False
                }

        logger.info(f"Image {img['id']}: Collection '{collection['label']}' ({collection['qid']}) trouvée")

        # Pause pour permettre validation
        # time.sleep(10)

        if not state.running:
            return

        # Création de la catégorie si nécessaire
        if not state.target_category['exists']:
            cat_id = piwigo.create_category(collection['label'], 854)
            if cat_id:
                # Mise à jour du mapping local ET de l'état global
                collection_mapping[collection_label_lower] = {
                    'piwigo_id': cat_id,
                    'qid': collection['qid']
                }
                with state.lock:
                    state.update_collection_mapping(collection['label'], cat_id, collection['qid'])
                    state.target_category['id'] = cat_id
                    state.stats['categories_created'] += 1
                logger.info(f"Catégorie '{collection['label']}' créée (ID: {cat_id})")

        # Ajout de l'image à la catégorie
        if state.target_category['id']:
            success = piwigo.add_image_to_category(img['id'], state.target_category['id'])
            if success:
                logger.info(f"Image {img['id']} ajoutée à la catégorie {state.target_category['id']}")
                state.mark_image_processed(img['id'], qid, collection['label'])
            else:
                logger.error(f"Échec ajout image {img['id']} à la catégorie {state.target_category['id']}")
                state.stats['errors'] += 1
                state.mark_image_processed(img['id'], qid, f"error:{collection['label']}")
    else:
        logger.info(f"Image {img['id']}: Aucune collection trouvée dans Wikidata pour {qid}")
        state.mark_image_processed(img['id'], qid, 'no_collection')

    # Marque l'image comme traitée
    state.stats['processed'] += 1


def process_images():
    """Traitement principal des images avec chargement progressif par lots"""
    piwigo = PiwigoAPI(PIWIGO_API, PIWIGO_USERNAME, PIWIGO_PASSWORD)

    if not piwigo.login():
        logger.error("Échec de connexion à Piwigo")
        return

    state.pwg_id = piwigo.pwg_id

    # Construction de la table de correspondance (ou chargement depuis la sauvegarde)
    # Cette fonction vérifie aussi la cohérence avec Piwigo
    collection_mapping = build_collection_mapping(piwigo)

    # Récupération du nombre total d'images pour l'affichage
    total_images = piwigo.get_total_images_count(80, recursive=True)
    state.total_images = total_images

    # Mise à jour du compteur d'images déjà traitées depuis le fichier
    already_processed = len(state.processed_images)

    # Mettre à jour les stats pour refléter le nombre réel d'images traitées
    with state.lock:
        # Le nombre dans stats.processed représente la session actuelle
        # On repart de 0 pour cette session
        state.stats['processed'] = 0

    logger.info(f"📊 État au démarrage:")
    logger.info(f"   Total d'images dans Piwigo (cat 80): {total_images}")
    logger.info(f"   Images déjà traitées (fichier): {already_processed}")
    logger.info(f"   Images restantes: {total_images - already_processed}")
    logger.info(f"   Collections mappées: {len(collection_mapping)}")

    # Traitement par lots
    page = state.current_batch
    has_more = True

    while has_more and state.running:
        # Chargement d'un lot d'images
        logger.info(f"=== Chargement du lot {page} ({BATCH_SIZE} images max) ===")
        images, has_more = piwigo.get_category_images_batch(80, page, BATCH_SIZE, recursive=True)

        if not images:
            logger.info("Aucune image retournée par Piwigo, fin du traitement")
            break

        logger.info(f"Lot {page} chargé: {len(images)} images")

        # Compteur d'images effectivement traitées dans ce lot (pas seulement skippées)
        processed_in_batch = 0

        # Traitement de chaque image du lot
        for img in images:
            if not state.running:
                break

            # Skip si déjà traitée (dans le fichier de traces)
            if state.is_image_processed(img['id']):
                logger.info(f"Image {img['id']} déjà dans le fichier de traces, passage à la suivante")
                continue

            # Pause si demandée
            while state.paused and state.running:
                time.sleep(0.5)

            if not state.running:
                break

            # Traitement de l'image
            process_single_image(piwigo, img, collection_mapping)
            processed_in_batch += 1

            logger.info(f"Image {img['id']} traitée ({state.stats['processed']}/{total_images})")

        # Log du lot terminé
        if processed_in_batch > 0:
            logger.info(f"Lot {page}: {processed_in_batch} images traitées effectivement")
        else:
            logger.info(f"Lot {page}: toutes les images étaient déjà traitées")

        # Passage au lot suivant
        page += 1
        state.current_batch = page
        state.force_save()  # Sauvegarde à chaque changement de lot

        if not state.running:
            break

        # Continue tant que Piwigo retourne des images (has_more)
        if has_more:
            logger.info(f"Lot {page-1} terminé, passage au lot suivant...")
        else:
            logger.info("Tous les lots ont été récupérés de Piwigo")

    # Sauvegarde finale
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
    <title>Synchronisation Piwigo-Wikidata</title>
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
        .main-content {
            flex: 1;
            min-width: 600px;
        }
        .sidebar {
            width: 380px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 26px;
        }
        h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 18px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 8px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .controls { 
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        button { 
            padding: 12px 24px;
            font-size: 15px;
            cursor: pointer;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        button:first-child {
            background: linear-gradient(135deg, #4caf50, #45a049);
            color: white;
        }
        button:nth-child(2) {
            background: linear-gradient(135deg, #ff9800, #f57c00);
            color: white;
        }
        button:nth-child(3) {
            background: linear-gradient(135deg, #f44336, #d32f2f);
            color: white;
        }
        .status { 
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            font-weight: 600;
            font-size: 14px;
        }
        .running { background: #4caf50; color: white; }
        .paused { background: #ff9800; color: white; }
        .stopped { background: #f44336; color: white; }
        
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-number {
            font-size: 32px;
            font-weight: bold;
            display: block;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 13px;
            opacity: 0.9;
        }
        .batch-info {
            background: #e3f2fd;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 15px;
            color: #1976d2;
            font-weight: 600;
        }
        .image-container {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
        }
        .image-container img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-bottom: 15px;
        }
        .info {
            margin: 10px 0;
            padding: 8px;
            background: white;
            border-radius: 5px;
        }
        .label {
            font-weight: bold;
            color: #667eea;
        }
        .collection {
            background: #e8f5e9;
            padding: 12px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 4px solid #4caf50;
        }
        .category {
            background: #fff3e0;
            padding: 12px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 4px solid #ff9800;
        }
        .qid-link, .piwigo-link {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            background: #e8eaf6;
            display: inline-block;
            margin-left: 5px;
        }
        .qid-link:hover, .piwigo-link:hover {
            background: #c5cae9;
            text-decoration: underline;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 13px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        th {
            background: #f5f5f5;
            color: #667eea;
            font-weight: 600;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .version-info {
            font-size: 11px;
            color: #999;
            text-align: center;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 8px;
        }
        .recent-images {
            max-height: 400px;
            overflow-y: auto;
        }
        .recent-images::-webkit-scrollbar {
            width: 8px;
        }
        .recent-images::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        .recent-images::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="main-content">
            <div class="card">
                <h1>🔗 Synchronisation Piwigo-Wikidata</h1>
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
                                <th>Collection</th>
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
                    <span class="stat-number" id="with_collection">0</span>
                    <span class="stat-label">Avec collection</span>
                </div>
                
                <div class="stat-box" style="margin-bottom: 15px; background: linear-gradient(135deg, #9c27b0, #7b1fa2);">
                    <span class="stat-number" id="categories_created">0</span>
                    <span class="stat-label">Catégories créées</span>
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
                    Version {{ version }} (format JSON v{{ version }})<br>
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
                    document.getElementById('with_collection').textContent = data.stats.with_collection;
                    document.getElementById('categories_created').textContent = data.stats.categories_created;
                    document.getElementById('errors').textContent = data.stats.errors;
                    
                    if (data.total_images > 0) {
                        // const percent = ((data.already_processed + data.stats.processed) / data.total_images * 100).toFixed(1);
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

                        if (data.found_collection) {
                            const qidLink = `https://www.wikidata.org/wiki/${data.found_collection.qid}`;
                            html += '<div class="collection">';
                            html += `<span class="label">Collection trouvée:</span> ${data.found_collection.label}`;
                            html += ` <a href="${qidLink}" target="_blank" class="qid-link">${data.found_collection.qid}</a>`;
                            html += '</div>';
                        }

                        if (data.target_category) {
                            html += '<div class="category">';
                            html += `<span class="label">Catégorie cible:</span> ${data.target_category.name}`;
                            html += data.target_category.exists ? ' ✓ (existe)' : ' ⊕ (à créer)';
                            html += '</div>';
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
                            tbody += `<tr>
                                <td><a href="${piwigoLink}" target="_blank" class="piwigo-link">#${img.id}</a></td>
                                <td>${qidLink}</td>
                                <td>${img.collection || 'N/A'}</td>
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
                'collection': info.get('collection', 'unknown'),
                'date': info.get('date', '')[:19]  # Format raccourci
            })
        recent_images.reverse()  # Plus récentes en premier

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
            'current_batch': state.current_batch,
            'recent_images': recent_images,
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
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
    print("="*60)
    print("🚀 Serveur de synchronisation Piwigo-Wikidata")
    print("="*60)
    print(f"📍 URL: http://localhost:5000")
    print(f"📦 Traitement par lots de {BATCH_SIZE} images")
    print(f"💾 Sauvegarde tous les {SAVE_EVERY_N_IMAGES} images")
    print(f"📄 Format de sauvegarde: Version {VERSION_NUMBER}")
    print(f"💾 Fichier de progression: {SAVE_FILE}")

    if os.path.exists(SAVE_FILE):
        print(f"✅ Fichier de progression existant détecté")

        # Nombre d'images traitées (mis à jour depuis le fichier)
        images_count = len(state.processed_images)
        print(f"   📊 {images_count} images déjà traitées")

        # Nombre de collections
        collections_count = len(state.collection_mapping)
        print(f"   📚 {collections_count} collections mappées")

        # Compter les collections avec QID
        collections_with_qid = sum(1 for c in state.collection_mapping.values() if c.get('qid'))
        print(f"   🔗 {collections_with_qid} collections avec QID Wikidata")
        print(f"   ⏱️  Lot de reprise: {state.current_batch}")

        # Analyser les types d'images traitées
        qid_types = {}
        for img_info in state.processed_images.values():
            qid = img_info.get('qid', 'unknown')
            if qid.startswith('Q') and qid[1:].isdigit():
                qid_type = 'with_qid'
            elif qid == 'already_in_collection':
                qid_type = 'already_in_collection'
            elif qid in ['none', 'unknown', 'error']:
                qid_type = qid
            else:
                qid_type = 'other'
            qid_types[qid_type] = qid_types.get(qid_type, 0) + 1

        if qid_types:
            print(f"   📈 Répartition:")
            for qid_type, count in sorted(qid_types.items(), key=lambda x: x[1], reverse=True):
                print(f"      - {qid_type}: {count}")
    else:
        print(f"ℹ️  Aucun fichier de progression (premier démarrage)")

    print("="*60)
    print("💡 Le serveur va vérifier la cohérence avec Piwigo au démarrage")
    print("="*60)

    app.run(debug=False, port=5000)