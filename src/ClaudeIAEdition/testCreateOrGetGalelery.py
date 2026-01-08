import requests
import json
from typing import Dict, List, Optional, Any, Union
from difflib import SequenceMatcher
import logging


# Configuration issue de votre documentation
class ScrutartConfig:
    """Configuration basée sur la documentation Scrutart"""
    # À adapter selon votre config privée
    PIWIGO_URL = "https://galeries.grains-de-culture.fr"
    PIWIGO_USERNAME = "API"  # À remplacer par votre config
    PIWIGO_PASSWORD = "Apipiwigo202102!!"  # À remplacer par votre config

    # Chemin pour les logs/traces
    LOG_FILE = "piwigo_operations.log"

    # Templates de nommage (mentionnés dans votre doc)
    IMAGE_LIST_TEMPLATE = "listeImages_{qid}_{name}.json"


class ScrutartPiwigoManager:
    """
    Gestionnaire Piwigo adapté à l'architecture Scrutart
    Basé sur la documentation technique Scrutart
    """

    def __init__(self, config: ScrutartConfig):
        self.config = config
        self.session = requests.Session()
        self.pwg_token = None
        self.logged_in = False

        # Configuration du logging
        logging.basicConfig(
            filename=config.LOG_FILE,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def login(self) -> bool:
        """
        Connexion à Piwigo
        Utilise les méthodes standard de l'API Piwigo
        """
        params = {
            'method': 'pwg.session.login',
            'username': self.config.PIWIGO_USERNAME,
            'password': self.config.PIWIGO_PASSWORD,
            'format': 'json'
        }

        try:
            response = self._call_api(params)
            if response and response.get('stat') == 'ok':
                self.pwg_token = response.get('result', {}).get('pwg_token')
                self.logged_in = True
                self.logger.info("Connexion Piwigo réussie")
                return True
            else:
                self.logger.error(f"Échec de connexion Piwigo: {response}")
                return False
        except Exception as e:
            self.logger.error(f"Erreur lors de la connexion: {e}")
            return False

    def get_all_categories(self) -> List[Dict]:
        """
        Récupérer toutes les galeries/catégories
        Correspond à la méthode pwg.categories.getList de votre doc
        """
        params = {
            'method': 'pwg.categories.getList',
            'format': 'json',
            'recursive': 'true',
            'fullname': 'true'
        }

        if self.pwg_token:
            params['pwg_token'] = self.pwg_token

        try:
            response = self._call_api(params)
            categories = response.get('result', {}).get('categories', []) if response else []
            self.logger.info(f"Récupération de {len(categories)} catégories")
            return categories
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des catégories: {e}")
            return []

    def find_gallery_by_title(self, title: str, similarity_threshold: float = 0.8) -> Dict[str, Any]:
        """
        Chercher une galerie par titre selon la logique Scrutart
        Gère les correspondances exactes et similaires
        """
        categories = self.get_all_categories()
        title_lower = title.lower().strip()

        exact_matches = []
        similar_matches = []

        for category in categories:
            category_title = category['name'].lower().strip()

            # Correspondance exacte
            if category_title == title_lower:
                exact_matches.append(category)
                continue

            # Correspondance par similarité
            similarity = SequenceMatcher(None, title_lower, category_title).ratio()
            if similarity >= similarity_threshold:
                similar_matches.append({
                    'category': category,
                    'similarity': similarity
                })

            # Correspondance par contenu
            elif (title_lower in category_title or
                  category_title in title_lower):
                similar_matches.append({
                    'category': category,
                    'similarity': 0.7
                })

        # Trier par similarité
        similar_matches.sort(key=lambda x: x['similarity'], reverse=True)

        if exact_matches:
            return {
                'found': True,
                'exact_match': True,
                'category': exact_matches[0],
                'all_exact': exact_matches
            }
        elif similar_matches:
            return {
                'found': True,
                'exact_match': False,
                'similar_match': True,
                'category': similar_matches[0]['category'],
                'similarity': similar_matches[0]['similarity'],
                'all_similar': similar_matches
            }
        else:
            return {
                'found': False,
                'exact_match': False,
                'similar_match': False
            }

    def create_gallery(self, name: str, parent_id: Optional[int] = None,
                       comment: str = '', visible: bool = True,
                       status: str = 'public', qid: Optional[str] = None) -> Dict[str, Any]:
        """
        Créer une nouvelle galerie selon les standards Scrutart
        Intègre la logique de détection des doublons

        Args:
            name: Nom de la galerie (ex: "Claude Monet")
            parent_id: ID de la galerie parente
            comment: Description avec possibilité multilingue
            visible: Galerie visible
            status: 'public' ou 'private'
            qid: QID Wikidata associé (pour traçabilité Scrutart)
        """
        # Vérifier les doublons selon votre logique
        existing_gallery = self.find_gallery_by_title(name)
        if existing_gallery['found']:
            self.logger.warning(f"Galerie similaire trouvée: {existing_gallery['category']['name']}")
            return {
                'success': False,
                'error': 'Une galerie avec un nom similaire existe déjà',
                'existing_gallery': existing_gallery['category'],
                'similarity': existing_gallery.get('similarity', 1.0)
            }

        # Préparer le commentaire selon le format Scrutart
        if qid and not comment:
            # Générer un commentaire automatique avec lien vers analyse Scrutart
            comment = self._generate_scrutart_comment(name, qid)

        params = {
            'method': 'pwg.categories.add',
            'name': name,
            'format': 'json'
        }

        if parent_id is not None:
            params['parent'] = str(parent_id)

        if comment:
            params['comment'] = comment

        if not visible:
            params['visible'] = 'false'

        if status != 'public':
            params['status'] = status

        if self.pwg_token:
            params['pwg_token'] = self.pwg_token

        try:
            response = self._call_api(params)

            if response and response.get('stat') == 'ok':
                category_id = int(response['result']['id'])

                # Log pour traçabilité Scrutart
                self.logger.info(f"Galerie créée: {name} (ID: {category_id}, QID: {qid})")

                return {
                    'success': True,
                    'category_id': category_id,
                    'info': response['result'].get('info', 'Galerie créée avec succès'),
                    'qid': qid,
                    'name': name
                }
            else:
                error_msg = response.get('message', 'Erreur lors de la création') if response else 'Erreur de connexion'
                self.logger.error(f"Échec création galerie {name}: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
        except Exception as e:
            self.logger.error(f"Exception lors de la création: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def create_or_get_gallery_for_entity(self, qid: str, entity_name: str,
                                         entity_type: str = "painter",
                                         force_create_if_similar: bool = False) -> Dict[str, Any]:
        """
        Créer ou récupérer une galerie pour une entité Scrutart
        Suit la logique documentée pour les créateurs

        Args:
            qid: QID Wikidata (ex: "Q296" pour Claude Monet)
            entity_name: Nom de l'entité (ex: "Claude Monet")
            entity_type: Type d'entité ("painter", "movement", "genre")
            force_create_if_similar: Forcer la création même si similaire
        """
        existing_gallery = self.find_gallery_by_title(entity_name)

        # Logique de gestion des doublons selon Scrutart
        if existing_gallery['found'] and existing_gallery['exact_match']:
            category_id = int(existing_gallery['category']['id'])
            self.logger.info(f"Galerie existante réutilisée pour {entity_name} (QID: {qid})")

            return {
                'success': True,
                'created': False,
                'category_id': category_id,
                'message': 'Galerie existante utilisée',
                'existing_gallery': existing_gallery['category'],
                'qid': qid,
                'entity_type': entity_type
            }

        if (existing_gallery['found'] and
                existing_gallery['similar_match'] and
                not force_create_if_similar):
            return {
                'success': False,
                'created': False,
                'error': f"Galerie similaire existante : {existing_gallery['category']['name']}",
                'similar_gallery': existing_gallery['category'],
                'similarity': existing_gallery.get('similarity', 0.8),
                'suggestion': 'Utilisez force_create_if_similar=True pour créer quand même',
                'qid': qid
            }

        # Créer la galerie avec commentaire Scrutart
        result = self.create_gallery(
            name=entity_name,
            comment=self._generate_scrutart_comment(entity_name, qid, entity_type),
            qid=qid
        )

        if result['success']:
            result['created'] = True
            result['entity_type'] = entity_type
            result['message'] = 'Nouvelle galerie créée pour entité Scrutart'

            if existing_gallery['found']:
                result['warning'] = f"Créée malgré galerie similaire : {existing_gallery['category']['name']}"

        return result

    def generate_creator_list_entry(self, qid: str, entity_name: str,
                                    category_id: int, entity_type: str = "painter") -> Dict[str, Any]:
        """
        Générer une entrée pour la liste des créateurs selon le format Scrutart
        Format compatible avec buildAlbumsTypedList.py et envoiImagePiwigo.py
        """
        # Template de nom de fichier selon la doc
        safe_name = entity_name.replace(" ", "").replace("-", "")
        list_images_path = f"data/fr/listeImages_{qid}_{safe_name}.json"

        entry = {
            "type": entity_type,
            "qid": qid,
            "categoryName": entity_name,
            "piwigoCategory": category_id,
            "listimagespath": list_images_path
        }

        self.logger.info(f"Entrée créateur générée: {qid} -> {entity_name} (ID: {category_id})")
        return entry

    def _generate_scrutart_comment(self, entity_name: str, qid: str,
                                   entity_type: str = "painter") -> str:
        """
        Générer un commentaire multilingue selon le format Scrutart
        Basé sur l'exemple de l'Annexe 7 de votre documentation
        """
        # Slug pour l'URL d'analyse
        analysis_slug = f"analyse-{entity_name.lower().replace(' ', '-').replace('é', 'e').replace('è', 'e')}"

        comment = f"""[lang=all]<style>
.banniere-analyse {{
    display: flex;
    align-items: center;
    gap: 1em;
    background: #f0f8ff;
    border-left: 5px solid #007acc;
    padding: 1em;
    margin: 1.5em 0;
    border-radius: 10px;
    font-family: sans-serif;
    flex-wrap: wrap;
}}
.banniere-analyse-icon {{
    font-size: 2em;
    color: #007acc;
}}
.banniere-analyse-text {{
    flex: 1;
    min-width: 200px;
}}
.banniere-analyse-text a {{
    color: #007acc;
    text-decoration: underline;
}}
@media (max-width: 600px) {{
    .banniere-analyse {{
        flex-direction: column;
        align-items: flex-start;
    }}
}}
</style>[/lang]
[lang=fr]<div class="banniere-analyse">
<div class="banniere-analyse-icon">📘</div>
<div class="banniere-analyse-text">
Une analyse des œuvres de {entity_name} peut être vue dans la page 
<a href="index.php?/page/{analysis_slug}">Analyse des œuvres de {entity_name}</a>.
<br><small>QID Wikidata: <a href="https://www.wikidata.org/entity/{qid}" target="_blank">{qid}</a></small>
</div>
</div>[/lang]
[lang=en]<div class="banniere-analyse">
<div class="banniere-analyse-icon">📘</div>
<div class="banniere-analyse-text">
An analysis of {entity_name}'s work can be found on the 
<a href="index.php?/page/{analysis_slug}">Analysis of {entity_name}'s Works</a> page.
<br><small>Wikidata QID: <a href="https://www.wikidata.org/entity/{qid}" target="_blank">{qid}</a></small>
</div>
</div>[/lang]"""

        return comment

    def _call_api(self, params: Dict[str, str]) -> Optional[Dict]:
        """
        Appel générique à l'API Piwigo avec gestion d'erreurs
        """
        url = f"{self.config.PIWIGO_URL}/ws.php"

        try:
            response = self.session.post(url, data=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erreur requête API Piwigo: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur décodage JSON Piwigo: {e}")
            return None


# Exemple d'utilisation selon votre workflow Scrutart
def main_scrutart_workflow():
    """
    Exemple d'utilisation dans le contexte Scrutart
    """
    config = ScrutartConfig()
    piwigo = ScrutartPiwigoManager(config)

    try:
        # Connexion
        if not piwigo.login():
            print("❌ Échec de connexion à Piwigo")
            return

        print("✅ Connexion Piwigo réussie")

        # Exemple: Créer une galerie pour Claude Monet (Q296)
        result = piwigo.create_or_get_gallery_for_entity(
            qid="Q296",
            entity_name="Claude Monet",
            entity_type="painter"
        )

        if result['success']:
            category_id = result['category_id']
            if result['created']:
                print(f"✅ Galerie créée pour Claude Monet: ID {category_id}")
            else:
                print(f"ℹ️ Galerie existante utilisée: ID {category_id}")

            # Générer l'entrée pour la liste des créateurs
            creator_entry = piwigo.generate_creator_list_entry(
                qid="Q296",
                entity_name="Claude Monet",
                category_id=category_id,
                entity_type="painter"
            )

            print("📝 Entrée générée pour listeAlbumsCreateurs.json:")
            print(json.dumps(creator_entry, indent=2, ensure_ascii=False))

        else:
            print(f"❌ Erreur: {result['error']}")
            if 'similar_gallery' in result:
                print(f"   Galerie similaire: {result['similar_gallery']['name']}")

        # Exemple: Chercher une galerie existante
        search_result = piwigo.find_gallery_by_title("Monet")
        if search_result['found']:
            print(f"🔍 Galerie trouvée: {search_result['category']['name']} (ID: {search_result['category']['id']})")

    except Exception as e:
        print(f"❌ Erreur générale: {e}")


if __name__ == "__main__":
    main_scrutart_workflow()