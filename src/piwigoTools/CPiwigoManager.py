import time
import re
import datetime
import logging
import requests
from typing import Dict, List, Optional, Tuple, Any
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

def setup_advanced_logging(log_level: str = "INFO", log_file: str = "logs/piwigo_manager.log"):
    """Configuration avancée du logging avec rotation et formatage structuré"""
    from logging.handlers import RotatingFileHandler
    import sys

    logger = logging.getLogger('CPiwigoManager')
    logger.setLevel(getattr(logging, log_level.upper()))

    # Formateur structuré avec métadonnées
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s | Extra: %(extra)s',
        defaults={'extra': '{}'}
    )

    # Handler console avec couleurs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Handler fichier avec rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


try:
    from src.piwigoTools.piwigoConfigPrivee import configPiwigo as cp
except ImportError as e:
    logging.error(f"Erreur d'importation de la configuration Piwigo : {e}")
    cp = {}


class CategoryType(Enum):
    """Types de catégories Piwigo supportées"""
    GENRES = "GENRES"
    CREATORS = "CREATORS"
    MOVEMENTS = "MOVEMENTS"
    EXHIBITIONS = "EXHIBITIONS"
    INSTITUTIONS = "INSTITUTIONS"
    TEST = "TEST"


@dataclass
class PiwigoConfig:
    """Configuration centralisée pour Piwigo"""
    api_url: str = "https://galleries.grains-de-culture.fr/ws.php"
    user_agent: str = 'Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)'
    base_url: str = "https://galeries.grains-de-culture.fr"
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 30


class PiwigoError(Exception):
    """Exception personnalisée pour les erreurs Piwigo"""
    pass


class CPiwigoManager:
    """Gestionnaire pour l'API Piwigo avec gestion d'erreurs robuste et logging amélioré"""

    def __init__(self, url: str = "https://galeries.grains-de-culture.fr", login: str = None,
                 password: str = None, log_level: str = "INFO"):
        self.config = PiwigoConfig()
        self.config.base_url = url
        self.config.api_url = url+"/ws.php"
        self.session: Optional[requests.Session] = None
        self.token: Optional[str] = None

        self.logger = setup_advanced_logging(log_level)

        # Récupération sécurisée des credentials
        self.login = login if login else cp.get("login", None)
        self.password = password if password else cp.get("pass", None)

        if not self.login or not self.password:
            logging.warning("Identifiants Piwigo non configurés ou manquants")

        # Configuration du logger
        self._setup_logging()

        # Dictionnaires de configuration des catégories
        self._setup_category_configs()

    def _setup_logging(self) -> None:
        """Configure le système de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('piwigo_manager.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _setup_category_configs(self) -> None:
        """Configure les paramètres des catégories"""
        self.gallery_naming = {
            CategoryType.GENRES: lambda name: f"Galerie de {name}s",
            CategoryType.CREATORS: lambda name: f"Galerie {name}",
            CategoryType.MOVEMENTS: lambda name: f"{name}",
            CategoryType.EXHIBITIONS: lambda name: f"{name}",
            CategoryType.INSTITUTIONS: lambda name: f"{name}",
            CategoryType.TEST: lambda name: f"{name}"
        }

        self.gallery_parents = {
            CategoryType.GENRES: 81,
            CategoryType.CREATORS: 80,
            CategoryType.EXHIBITIONS: 956,
            CategoryType.MOVEMENTS: 853,
            CategoryType.INSTITUTIONS: 854,
            CategoryType.TEST: 7
        }

    @contextmanager
    def _handle_request_errors(self, operation: str):
        """Context manager pour gérer les erreurs de requête"""
        try:
            yield
        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout lors de l'opération : {operation}")
            raise PiwigoError(f"Timeout lors de {operation}")
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Erreur de connexion lors de l'opération : {operation}")
            raise PiwigoError(f"Erreur de connexion lors de {operation}")
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Erreur HTTP {e.response.status_code} lors de {operation}: {e}")
            raise PiwigoError(f"Erreur HTTP lors de {operation}: {e}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur de requête lors de {operation}: {e}")
            raise PiwigoError(f"Erreur de requête lors de {operation}: {e}")

    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Effectue une requête avec retry automatique"""
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                with self._handle_request_errors(f"{method} {url}"):
                    kwargs.setdefault('timeout', self.config.timeout)
                    kwargs.setdefault('headers', {}).update({'User-Agent': self.config.user_agent})

                    if method.upper() == 'GET':
                        response = self.session.get(url, **kwargs)
                    elif method.upper() == 'POST':
                        response = self.session.post(url, **kwargs)
                    elif method.upper() == 'HEAD':
                        response = self.session.head(url, **kwargs)
                    else:
                        raise ValueError(f"Méthode HTTP non supportée: {method}")

                    response.raise_for_status()
                    return response

            except (PiwigoError, requests.exceptions.RequestException) as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)  # Backoff exponentiel
                    self.logger.warning(f"Tentative {attempt + 1} échouée, retry dans {wait_time}s : {e}")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Toutes les tentatives ont échoué pour {method} {url}")

        raise last_exception

    def select_best_image(self, image_urls: List[str]) -> Optional[str]:
        """Choisit la meilleure image basée sur la taille (Content-Length)"""
        if not image_urls:
            self.logger.warning("Liste d'URLs d'images vide")
            return None

        best_url = None
        best_size = 0

        self.logger.info(f"Sélection de la meilleure image parmi {len(image_urls)} options")

        for url in image_urls:
            try:
                if not self.session:
                    self.session = requests.Session()

                response = self._make_request_with_retry('HEAD', url, allow_redirects=True)
                size = int(response.headers.get("Content-Length", 0))

                self.logger.debug(f"Image {url}: {size} bytes")

                if size > best_size:
                    best_size = size
                    best_url = url

            except Exception as e:
                self.logger.warning(f"Impossible de vérifier la taille de {url}: {e}")
                continue

        selected_url = best_url or (image_urls[0] if image_urls else None)
        if selected_url:
            self.logger.info(f"Image sélectionnée: {selected_url} ({best_size} bytes)")
        else:
            self.logger.error("Aucune image valide trouvée")

        return selected_url

    def build_description(self, image_url: str, creator_url: str, creator_label: str,
                          wikidata_uri: str, lang: str = "fr") -> str:
        """Construit la description d'une image avec validation des paramètres"""
        try:
            # Validation des paramètres
            if not image_url or not wikidata_uri:
                raise ValueError("URL d'image et URI Wikidata requis")

            qid = wikidata_uri.replace("http://www.wikidata.org/entity/", "")
            creator_label = creator_label or "Créateur inconnu" if lang == "fr" else "Unknown creator"

            templates = {
                "fr": (
                    f"Créateur: <a href='{creator_url}'>{creator_label}</a>"
                    f"<div>Source Wikimedia Commons <a href='{image_url}'>{image_url}</a></div>"
                    f"<div>Élément Wikidata <a href='{wikidata_uri}'>{qid}</a></div>"
                ),
                "en": (
                    f"Creator: <a href='{creator_url}'>{creator_label}</a>"
                    f"<div>Source: Wikimedia Commons <a href='{image_url}'>{image_url}</a></div>"
                    f"<div>Wikidata item <a href='{wikidata_uri}'>{qid}</a></div>"
                )
            }

            description = templates.get(lang, templates["fr"])
            self.logger.debug(f"Description construite pour la langue {lang}")
            return description

        except Exception as e:
            self.logger.error(f"Erreur lors de la construction de la description: {e}")
            return f"Description non disponible (erreur: {str(e)})"

    def piwigo_login(self) -> bool:
        """Connexion à Piwigo avec validation des credentials"""
        if not self.login or not self.password:
            self.logger.error("Identifiants Piwigo manquants")
            raise PiwigoError("Identifiants Piwigo non configurés")

        if not self.session:
            self.session = requests.Session()

        payload = {
            "format": "json",
            "method": "pwg.session.login",
            "username": self.login,
            "password": self.password,
        }

        try:
            self.logger.info("Tentative de connexion à Piwigo...")
            response = self._make_request_with_retry('POST', self.config.api_url, data=payload)
            response.raise_for_status()
            if "stat" in response.text and "ok" in response.text:
                self.logger.info("Connexion à Piwigo réussie")
                return True
            else:
                self.logger.error(f"Erreur lors de la connexion à Piwigo (login/password?)")
                return False
        except Exception as e:
            self.logger.error(f"Erreur lors de la connexion à Piwigo: {e}")
            raise PiwigoError(f"Impossible de se connecter à Piwigo: {e}")

    def piwigo_open_session(self) -> None:
        """Ouvre une session Piwigo et récupère le token"""
        if not self.session:
            if not self.piwigo_login():
                raise PiwigoError("Échec de la connexion à Piwigo")

            try:
                # Récupération du token
                response = self._make_request_with_retry(
                    'GET',
                    f"{self.config.api_url}?format=json&method=pwg.session.getStatus"
                )

                result = response.json()
                if result.get("stat") == "ok":
                    self.token = result.get("result", {}).get("pwg_token")
                    self.logger.info(
                        f"Session Piwigo ouverte, token obtenu: {self.token[:10]}..." if self.token else "pas de token")
                else:
                    self.logger.warning("Token Piwigo non récupéré")

            except Exception as e:
                self.logger.error(f"Erreur lors de la récupération du token: {e}")

    def piwigo_ensure_category_exists(self, category_name: str) -> int:
        """S'assure qu'une catégorie existe, la crée si nécessaire"""
        if not category_name.strip():
            raise ValueError("Le nom de catégorie ne peut pas être vide")

        try:
            self.piwigo_open_session()

            # Vérification de l'existence de la catégorie
            response = self._make_request_with_retry(
                'GET',
                f"{self.config.api_url}?format=json&method=pwg.categories.getList"
            )

            result = response.json()
            if result.get("stat") != "ok":
                raise PiwigoError(f"Erreur API lors de la récupération des catégories: {result}")

            categories = result.get("result", {}).get("categories", [])

            # Recherche de la catégorie existante
            for cat in categories:
                if cat.get("name") == category_name:
                    category_id = int(cat.get("id"))
                    self.logger.info(f"Catégorie '{category_name}' trouvée avec l'ID {category_id}")
                    return category_id

            # Création de la catégorie si elle n'existe pas
            self.logger.info(f"Création de la catégorie '{category_name}'...")
            payload = {
                "method": "pwg.categories.add",
                "name": category_name,
                "format": "json"
            }

            response = self._make_request_with_retry('POST', self.config.api_url, data=payload)
            result = response.json()

            if result.get("stat") == "ok":
                new_id = int(result["result"]["id"])
                self.logger.info(f"Catégorie '{category_name}' créée avec l'ID {new_id}")
                return new_id
            else:
                error_msg = result.get("message", "Erreur inconnue")
                raise PiwigoError(f"Impossible de créer la catégorie: {error_msg}")

        except Exception as e:
            self.logger.error(f"Erreur lors de la gestion de la catégorie '{category_name}': {e}")
            raise

    def select_image_to_post(self, artwork_description: Dict[str, Any]) -> Tuple[str, bytes]:
        """Sélectionne et télécharge l'image à poster"""
        if not isinstance(artwork_description, dict):
            raise ValueError("artwork_description doit être un dictionnaire")

        image_urls = artwork_description.get("images", [])
        if not image_urls:
            raise ValueError("Aucune URL d'image trouvée dans artwork_description")

        best_image_url = self.select_best_image(image_urls)
        if not best_image_url:
            raise PiwigoError("Impossible de sélectionner une image valide")

        try:
            self.logger.info(f"Téléchargement de l'image: {best_image_url}")
            if not self.session:
                self.session = requests.Session()

            response = self._make_request_with_retry('GET', best_image_url)
            image_data = response.content

            if not image_data:
                raise PiwigoError("Données d'image vides")

            self.logger.info(f"Image téléchargée: {len(image_data)} bytes")
            return best_image_url, image_data

        except Exception as e:
            self.logger.error(f"Erreur lors du téléchargement de l'image: {e}")
            raise

    def piwigo_post_image(self, artwork_description: Dict[str, Any],
                          category_name: str = "Galerie de tests",
                          lang: str = "fr") -> Optional[requests.Response]:
        """Poste une image sur Piwigo avec gestion d'erreurs complète"""
        try:
            self.logger.info(f"Début de l'envoi d'image vers la catégorie '{category_name}'")

            # Validation des paramètres
            if not isinstance(artwork_description, dict):
                raise ValueError("artwork_description doit être un dictionnaire")

            best_image_url, image_data = self.select_image_to_post(artwork_description)
            self.piwigo_open_session()

            # Gestion de la catégorie
            category_id = self.piwigo_ensure_category_exists(category_name)

            # Extraction des métadonnées avec valeurs par défaut
            titre = artwork_description.get(f"titre_{lang}") or artwork_description.get("titre_fr") or "Sans titre"
            uri = artwork_description.get("uri", "")
            creator_url = artwork_description.get("createur", "#")
            creator_label = artwork_description.get("createurLabel", "Créateur inconnu")

            description = self.build_description(best_image_url, creator_url, creator_label, uri, lang)

            # Préparation de la requête
            payload = {
                "method": "pwg.images.addSimple",
                "category": category_id,
                "name": titre,
                "comment": description,
                "tags": category_name,
            }

            # Détermination du type MIME
            content_type = 'image/jpeg'
            if best_image_url.lower().endswith('.png'):
                content_type = 'image/png'
            elif best_image_url.lower().endswith('.gif'):
                content_type = 'image/gif'

            files = {
                'image': (
                    best_image_url.split("/")[-1],
                    image_data,
                    content_type
                )
            }

            self.logger.info(f"Envoi de l'image '{titre}' ({len(image_data)} bytes)...")

            response = self._make_request_with_retry(
                'POST',
                f"{self.config.api_url}?format=json",
                data=payload,
                files=files
            )

            result = response.json()
            if result.get("stat") == "ok":
                image_id = result.get("result", {}).get("image_id")
                self.logger.info(f"Image '{titre}' envoyée avec succès (ID: {image_id})")
                return response
            else:
                error_msg = result.get("message", "Erreur inconnue")
                self.logger.error(f"Erreur lors de l'envoi de l'image: {error_msg}")
                return None

        except Exception as e:
            self.logger.error(f"Erreur lors de l'envoi de l'image: {e}")
            return None

    def piwigo_image_set_category(self, image_id: int, category_id: int) -> Optional[requests.Response]:
        """Associe une image à une catégorie"""
        if not image_id or not category_id:
            raise ValueError("image_id et category_id requis")

        try:
            self.piwigo_open_session()

            payload = {
                "method": "pwg.images.setCategory",
                "category_id": category_id,
                "action": "associate",
                "image_id": image_id,
                "pwg_token": self.token
            }

            response = self._make_request_with_retry(
                'POST',
                f"{self.config.api_url}?format=json&method=pwg.images.setCategory",
                data=payload
            )

            result = response.json()
            if result.get("stat") == "ok":
                self.logger.info(f"Image {image_id} associée à la catégorie {category_id}")
                return response
            else:
                error_msg = result.get("message", "Erreur inconnue")
                self.logger.error(f"Erreur lors de l'association: {error_msg}")
                return None

        except Exception as e:
            self.logger.error(f"Erreur lors de l'association image-catégorie: {e}")
            return None

    def piwigo_image_get_categories(self, image_id: int) -> Optional[List[str]]:
        """Récupère les catégories d'une image"""
        if not image_id:
            self.logger.error("ID d'image manquant")
            return None

        try:
            self.piwigo_open_session()

            response = self._make_request_with_retry(
                'GET',
                f"{self.config.api_url}?format=json&method=pwg.images.getInfo&image_id={image_id}"
            )

            result = response.json()
            if result.get("stat") == "ok":
                data = result.get("result", {})
                categories = data.get("categories", [])
                category_ids = [str(cat["id"]) for cat in categories]

                self.logger.info(f"Image {image_id} associée aux catégories: {category_ids}")
                return category_ids
            else:
                error_msg = result.get("message", "Erreur inconnue")
                self.logger.error(f"Erreur lors de la récupération des catégories: {error_msg}")
                return None

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des catégories de l'image {image_id}: {e}")
            return None

    def piwigo_get_categories(self) -> Optional[Dict[str, Any]]:
        """Récupère la liste complète des catégories"""
        try:
            self.piwigo_open_session()

            url = (f"{self.config.api_url}?format=json&method=pwg.categories.getList&recursive=true&fullname=true&tree_output=true")

            response = self._make_request_with_retry('GET', url)
            result = response.json()

            if result.get("stat") == "ok":
                self.logger.info("Liste des catégories récupérée avec succès")
                return result
            else:
                error_msg = result.get("message", "Erreur inconnue")
                self.logger.error(f"Erreur lors de la récupération des catégories: {error_msg}")
                return None

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération de la liste des catégories: {e}")
            return None

    def piwigo_create_category(self, category_name: str, category_type: CategoryType) -> Optional[requests.Response]:
        """Crée une nouvelle catégorie avec type spécifié"""
        if not category_name.strip():
            raise ValueError("Le nom de catégorie ne peut pas être vide")

        try:
            if not self.session:
                self.session = requests.Session()

            if not self.piwigo_login():
                raise PiwigoError("Impossible de se connecter à Piwigo")

            # Configuration du nom et du parent selon le type
            gallery_name = self.gallery_naming[category_type](category_name)
            parent_id = self.gallery_parents.get(category_type, 856)  # 856 = En attente

            payload = {
                "status": "private",
                "name": gallery_name,
                "parent": parent_id,
                "method": "pwg.categories.add",
            }

            self.logger.info(f"Création de la catégorie '{gallery_name}' (type: {category_type.value})")

            response = self._make_request_with_retry(
                'POST',
                f"{self.config.api_url}?format=json&method=pwg.categories.add",
                data=payload
            )

            result = response.json()
            if result.get("stat") == "ok":
                category_id = result["result"]["id"]
                self.logger.info(f"Catégorie '{gallery_name}' créée avec l'ID {category_id}")
                return response
            else:
                error_msg = result.get("message", "Erreur inconnue")
                self.logger.error(f"Erreur lors de la création de la catégorie: {error_msg}")
                return None

        except Exception as e:
            self.logger.error(f"Erreur lors de la création de la catégorie '{category_name}': {e}")
            return None

    def build_gallery_comment(self, category_type: str, name: str,
                              scrutart_page: str = "https://scrutart.grains-de-culture.fr/") -> str:
        """Construit le commentaire d'une galerie selon son type"""
        try:
            templates = {
                "GALERY_GENRE": {
                    "fr": f"<p>Une analyse de la présence du genre '{name}' dans Wikidata se trouve dans <a href='{scrutart_page}'>ScrutArt</a>.</p>",
                    "en": f"<p>An analysis of genre presence '{name}' in Wikidata can be found in <a href='{scrutart_page}'>ScrutArt</a>.</p>",
                },
                "GALERY_MOVEMENT": {
                    "fr": f"Cette galerie présente des peintures du mouvement '{name}'. Ces images, libres de droit, ont été sélectionnées à partir de données de Wikidata et d'images de Wikimedia Commons. Une analyse de la présence du genre '{name}' dans Wikidata se trouve dans <a href='{scrutart_page}'>ScrutArt</a>.",
                    "en": "",
                },
                "GALERY_CREATOR": {
                    "fr": f"<p>Une analyse de la présence des oeuvres de '{name}' dans Wikidata se trouve dans <a href='{scrutart_page}'>ScrutArt</a>.</p>",
                    "en": f"<p>An analysis of the presence of works created by '{name}' in Wikidata can be found in <a href='{scrutart_page}'>ScrutArt</a>.</p>",
                }
            }

            css_style = """
            [lang=all]
                <style> 
                .banniere-analyse {
                    display: flex; align-items: center; gap: 0.5em; background: #f8f8f8; 
                    border-left: 3px solid #cccccc; padding: 1em; margin: 0em 0; 
                    border-radius: 10px; font-family: sans-serif; flex-wrap: wrap;
                } 
                .banniere-analyse-icon { font-size: 4em; color: #007acc; } 
                .banniere-analyse-text { flex: 1; min-width: 200px; } 
                .banniere-analyse-text a { color: #007acc; text-decoration: underline; } 
                @media (max-width: 600px) {   
                    .banniere-analyse { flex-direction: column; align-items: flex-start; } 
                }
                </style>
                <div class='banniere-analyse'>   
                <div class='banniere-analyse-text'>
            [/lang]
            """

            template = templates.get(category_type, {})
            if not template:
                self.logger.warning(f"Type de catégorie non reconnu: {category_type}")
                return ""

            content = css_style
            for lang, text in template.items():
                if text.strip():  # Only add non-empty content
                    content += f"[lang={lang}]{text}[/lang]"

            content += "[lang=all]</div></div>[/lang]"

            self.logger.debug(f"Commentaire de galerie construit pour {category_type}")
            return content

        except Exception as e:
            self.logger.error(f"Erreur lors de la construction du commentaire de galerie: {e}")
            return ""

    def piwigo_comment_category(self, category_id: int, comment: str) -> Tuple[Optional[requests.Response], str]:
        """Ajoute un commentaire à une catégorie"""
        if not category_id or not comment.strip():
            raise ValueError("category_id et comment requis")

        try:
            self.piwigo_open_session()

            payload = {
                "method": "pwg.categories.setInfo",
                "comment": comment,
                "category_id": category_id,
                "pwg_token": self.token
            }

            response = self._make_request_with_retry(
                'POST',
                f"{self.config.api_url}?format=json&method=pwg.categories.setInfo",
                data=payload
            )

            result = response.json()
            if result.get("stat") == "ok":
                self.logger.info(f"Commentaire ajouté à la catégorie {category_id}")
                return response, comment
            else:
                error_msg = result.get("message", "Erreur inconnue")
                self.logger.error(f"Erreur lors de l'ajout du commentaire: {error_msg}")
                return None, f"Erreur d'envoi de description: {error_msg}"

        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout du commentaire à la catégorie {category_id}: {e}")
            return None, f"Erreur d'exception: {str(e)}"

    @staticmethod
    def get_image_id(response_text: str) -> Optional[str]:
        """Extrait l'ID d'image depuis une réponse"""
        try:
            regex = r"image_id[\\]?\": ?[\"']?(\d+)"
            match = re.search(regex, response_text)
            return match.group(1) if match else None
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction de l'ID d'image: {e}")
            return None

    @staticmethod
    def get_category_id(response_text: str) -> Optional[str]:
        """Extrait l'ID de catégorie depuis une réponse"""
        try:
            regex = r"category\\?/(\d+)"
            match = re.search(regex, response_text)
            return match.group(1) if match else None
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction de l'ID de catégorie: {e}")
            return None

    def close_session(self) -> None:
        """Ferme proprement la session Piwigo"""
        if self.session:
            try:
                # Tentative de déconnexion propre
                payload = {
                    "method": "pwg.session.logout",
                    "format": "json"
                }
                self._make_request_with_retry('POST', self.config.api_url, data=payload)
                self.logger.info("Session Piwigo fermée proprement")
            except Exception as e:
                self.logger.warning(f"Erreur lors de la fermeture de session: {e}")
            finally:
                self.session.close()
                self.session = None
                self.token = None

    def __enter__(self):
        """Support du context manager"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Nettoyage automatique à la sortie du context manager"""
        self.close_session()

    def health_check(self) -> Dict[str, Any]:
        """Vérifie l'état de santé de la connexion Piwigo"""
        health_status = {
            "status": "unknown",
            "api_accessible": False,
            "authentication": False,
            "token_available": False,
            "timestamp": datetime.datetime.now().isoformat()
        }

        try:
            # Test de connectivité API
            if not self.session:
                self.session = requests.Session()

            response = self._make_request_with_retry(
                'GET',
                f"{self.config.api_url}?format=json&method=pwg.session.getStatus"
            )
            health_status["api_accessible"] = True

            # Test d'authentification
            if self.piwigo_login():
                health_status["authentication"] = True

                # Vérification du token
                self.piwigo_open_session()
                if self.token:
                    health_status["token_available"] = True
                    health_status["status"] = "healthy"
                else:
                    health_status["status"] = "degraded"
            else:
                health_status["status"] = "authentication_failed"

        except Exception as e:
            health_status["status"] = "error"
            health_status["error"] = str(e)
            self.logger.error(f"Health check failed: {e}")

        return health_status

    def get_statistics(self) -> Dict[str, Any]:
        """Récupère des statistiques sur la galerie Piwigo"""
        try:
            self.piwigo_open_session()

            # Récupération des informations générales
            response = self._make_request_with_retry(
                'GET',
                f"{self.config.api_url}?format=json&method=pwg.session.getStatus"
            )

            result = response.json()
            if result.get("stat") == "ok":
                stats = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "session_info": result.get("result", {}),
                    "categories_count": None,
                    "images_count": None
                }

                # Tentative de récupération du nombre de catégories
                try:
                    categories_response = self.piwigo_get_categories()
                    if categories_response:
                        categories = categories_response.get("result", {}).get("categories", [])
                        stats["categories_count"] = len(categories)
                except Exception as e:
                    self.logger.warning(f"Impossible de récupérer le nombre de catégories: {e}")

                return stats
            else:
                raise PiwigoError(f"Erreur API: {result}")

        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            return {"error": str(e), "timestamp": datetime.datetime.now().isoformat()}

    def bulk_upload_images(self, artworks: List[Dict[str, Any]],
                           category_name: str = "Galerie de tests",
                           lang: str = "fr",
                           max_concurrent: int = 3) -> Dict[str, Any]:
        """Upload en lot d'images avec limitation de concurrence"""
        if not artworks:
            raise ValueError("Liste d'artworks vide")

        results = {
            "total": len(artworks),
            "success": 0,
            "failed": 0,
            "errors": [],
            "successful_uploads": []
        }

        self.logger.info(f"Début de l'upload en lot de {len(artworks)} images")

        for i, artwork in enumerate(artworks, 1):
            try:
                self.logger.info(f"Traitement de l'artwork {i}/{len(artworks)}")

                response = self.piwigo_post_image(artwork, category_name, lang)

                if response:
                    results["success"] += 1
                    results["successful_uploads"].append({
                        "index": i,
                        "title": artwork.get(f"titre_{lang}", "Sans titre"),
                        "response_status": response.status_code
                    })
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "index": i,
                        "title": artwork.get(f"titre_{lang}", "Sans titre"),
                        "error": "Réponse nulle de l'API"
                    })

                # Pause entre les uploads pour éviter la surcharge
                if i < len(artworks):
                    time.sleep(0.5)

            except Exception as e:
                results["failed"] += 1
                error_info = {
                    "index": i,
                    "title": artwork.get(f"titre_{lang}", "Sans titre"),
                    "error": str(e)
                }
                results["errors"].append(error_info)
                self.logger.error(f"Erreur upload artwork {i}: {e}")

        self.logger.info(f"Upload en lot terminé: {results['success']} succès, {results['failed']} échecs")
        return results


def main():
    """Fonction principale pour les tests et démonstrations"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Utilisation du context manager pour une gestion propre des ressources
        with CPiwigoManager() as pwg:
            # Health check
            health = pwg.health_check()
            logger.info(f"État de santé Piwigo: {health['status']}")

            if health["status"] != "healthy":
                logger.warning("Système Piwigo non optimal, arrêt du test")
                return

            # Test de création de commentaire de galerie
            comment = pwg.build_gallery_comment("GALERY_CREATOR", "Test Creator")
            if comment:
                logger.info("Commentaire de galerie généré avec succès")

            # Test de récupération des statistiques
            stats = pwg.get_statistics()
            logger.info(f"Statistiques récupérées: {stats.get('categories_count', 'N/A')} catégories")

            # Exemple d'artwork pour test
            test_artwork = {
                "images": [
                    "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1280px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg"],
                "titre_fr": "Test - La Nuit étoilée",
                "titre_en": "Test - The Starry Night",
                "uri": "http://www.wikidata.org/entity/Q45585",
                "createur": "http://www.wikidata.org/entity/Q5582",
                "createurLabel": "Vincent van Gogh"
            }

            # Test d'upload (commenté pour éviter les uploads accidentels)
            # response = pwg.piwigo_post_image(test_artwork, "Test Category")
            # if response:
            #     logger.info("Test d'upload réussi")

    except Exception as e:
        logger.error(f"Erreur dans le main: {e}")


if __name__ == "__main__":
    main()