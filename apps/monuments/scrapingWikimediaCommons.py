import requests
import json
import time
import re
from typing import Dict, Optional, List, Set
from datetime import datetime
from collections import Counter
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WikimediaMonumentsScraper:
    def __init__(self, output_file: str = "monuments_france.jsonl"):
        self.output_file = output_file
        self.api_url = "https://commons.wikimedia.org/w/api.php"
        self.delay = 0.5  # Délai entre les requêtes (500ms)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MonumentsScraper/1.0 (Educational Purpose)'
        })

        # Patterns pour extraire les lieux
        self.location_patterns = [
            r'\b([A-Z][a-zéèêëàâäôöùûüçîï]+(?:-[A-Z][a-zéèêëàâäôöùûüçîï]+)*)\b',  # Noms propres
        ]

        # Mots-clés pour filtrer les faux positifs
        self.exclude_keywords = {
            'File', 'Category', 'Image', 'Photo', 'Photograph', 'View', 'Monument',
            'Church', 'Cathedral', 'Castle', 'Château', 'Église', 'Temple', 'Basilica',
            'Tower', 'Palace', 'Fort', 'Abbey', 'Abbaye', 'Chapel', 'Chapelle',
            'Museum', 'Musée', 'Bridge', 'Pont', 'Gate', 'Porte', 'Square', 'Place',
            'Street', 'Rue', 'Avenue', 'Boulevard', 'Historical', 'Historique',
            'Ancient', 'Ancien', 'Medieval', 'Roman', 'Gothic', 'Renaissance',
            'France', 'French', 'Français', 'Française', 'National', 'Royal',
            'Commons', 'Wikimedia', 'Wikipedia', 'JPG', 'JPEG', 'PNG', 'SVG'
        }

        # Prépositions et articles à ignorer
        self.stop_words = {
            'de', 'du', 'des', 'le', 'la', 'les', 'un', 'une', 'en', 'au', 'aux',
            'dans', 'sur', 'sous', 'pour', 'par', 'avec', 'sans', 'chez', 'vers',
            'in', 'of', 'the', 'at', 'on', 'from', 'to', 'by', 'with'
        }

    def extract_locations_from_text(self, text: str) -> Set[str]:
        """Extrait les noms de lieux depuis un texte."""
        if not text:
            return set()

        locations = set()

        # Nettoyage du texte
        text = re.sub(r'<[^<]+?>', '', text)  # Suppression des balises HTML
        text = re.sub(r'\([^)]*\)', '', text)  # Suppression des parenthèses

        # Extraction des noms propres
        words = re.findall(
            r'\b[A-ZÉÈÊËÀÂÄÔÖÙÛÜÇÎÏ][a-zéèêëàâäôöùûüçîï]+(?:-[A-ZÉÈÊËÀÂÄÔÖÙÛÜÇÎÏ][a-zéèêëàâäôöùûüçîï]+)*\b', text)

        for word in words:
            # Filtrage des mots-clés génériques
            if word in self.exclude_keywords:
                continue
            if word.lower() in self.stop_words:
                continue
            if len(word) < 3:  # Mots trop courts
                continue

            locations.add(word)

        return locations

    def extract_locations_from_categories(self, categories: List[str]) -> Set[str]:
        """Extrait les noms de lieux depuis les catégories."""
        locations = set()

        for category in categories:
            # Patterns spécifiques pour les catégories
            patterns = [
                r'in\s+([A-Z][a-zéèêëàâäôöùûüçîï]+(?:-[A-Z][a-zéèêëàâäôöùûüçîï]+)*)',
                r'de\s+([A-Z][a-zéèêëàâäôöùûüçîï]+(?:-[A-Z][a-zéèêëàâäôöùûüçîï]+)*)',
                r'à\s+([A-Z][a-zéèêëàâäôöùûüçîï]+(?:-[A-Z][a-zéèêëàâäôöùûüçîï]+)*)',
                r'of\s+([A-Z][a-zéèêëàâäôöùûüçîï]+(?:-[A-Z][a-zéèêëàâäôöùûüçîï]+)*)',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, category)
                for match in matches:
                    if match not in self.exclude_keywords and len(match) >= 3:
                        locations.add(match)

        return locations

    def extract_all_locations(self, page_data: Dict, filename: str,
                              monument_name: str, metadata: Dict) -> List[str]:
        """Extrait tous les noms de lieux possibles depuis toutes les sources."""
        all_locations = set()

        # Extraction depuis le nom du fichier
        all_locations.update(self.extract_locations_from_text(filename))

        # Extraction depuis le nom du monument
        all_locations.update(self.extract_locations_from_text(monument_name))

        # Extraction depuis ImageDescription
        image_desc = metadata.get('ImageDescription', '')
        all_locations.update(self.extract_locations_from_text(image_desc))

        # Extraction depuis ObjectName
        object_name = metadata.get('ObjectName', '')
        all_locations.update(self.extract_locations_from_text(object_name))

        # Extraction depuis les catégories
        categories = page_data.get('categories', [])
        cat_titles = [cat.get('title', '').replace('Category:', '') for cat in categories]
        all_locations.update(self.extract_locations_from_categories(cat_titles))

        # Tri par fréquence et pertinence (les lieux les plus probables en premier)
        # On peut améliorer avec un scoring basé sur la source
        location_scores = Counter()

        for loc in all_locations:
            score = 0
            # Plus de points si présent dans plusieurs sources
            if loc in filename:
                score += 3
            if loc in monument_name:
                score += 2
            if any(loc in cat for cat in cat_titles):
                score += 4  # Les catégories sont souvent plus fiables

            location_scores[loc] = score

        # Retourner les lieux triés par score
        sorted_locations = [loc for loc, score in location_scores.most_common()]

        return sorted_locations

    def search_monuments(self, category: str, limit: int = 100) -> List[str]:
        """Recherche les fichiers dans une catégorie donnée."""
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'categorymembers',
            'cmtitle': category,
            'cmtype': 'file',
            'cmlimit': min(limit, 500)
        }

        try:
            time.sleep(self.delay)
            response = self.session.get(self.api_url, params=params)
            response.raise_for_status()
            data = response.json()

            files = [member['title'] for member in data.get('query', {}).get('categorymembers', [])]
            logger.info(f"Trouvé {len(files)} fichiers dans {category}")
            return files

        except Exception as e:
            logger.error(f"Erreur lors de la recherche dans {category}: {e}")
            return []

    def search_by_keywords(self, keywords: str, limit: int = 100) -> List[str]:
        """Recherche des fichiers par mots-clés."""
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': keywords,
            'srnamespace': '6',  # Namespace pour les fichiers
            'srlimit': min(limit, 500),
            'srwhat': 'text'
        }

        try:
            time.sleep(self.delay)
            response = self.session.get(self.api_url, params=params)
            response.raise_for_status()
            data = response.json()

            files = [f"File:{result['title']}" if not result['title'].startswith('File:')
                     else result['title']
                     for result in data.get('query', {}).get('search', [])]
            logger.info(f"Trouvé {len(files)} fichiers pour '{keywords}'")
            return files

        except Exception as e:
            logger.error(f"Erreur lors de la recherche par mots-clés '{keywords}': {e}")
            return []

    def get_image_info(self, filename: str) -> Optional[Dict]:
        """Récupère les informations détaillées d'une image."""
        params = {
            'action': 'query',
            'format': 'json',
            'titles': filename,
            'prop': 'imageinfo|coordinates|categories',
            'iiprop': 'url|extmetadata|size',
            'colimit': 'max'
        }

        try:
            time.sleep(self.delay)
            response = self.session.get(self.api_url, params=params)
            response.raise_for_status()
            data = response.json()

            pages = data.get('query', {}).get('pages', {})
            if not pages:
                return None

            page = list(pages.values())[0]
            if 'missing' in page:
                return None

            return page

        except Exception as e:
            logger.error(f"Erreur lors de la récupération de {filename}: {e}")
            return None

    def extract_monument_data(self, page_data: Dict, filename: str) -> Optional[Dict]:
        """Extrait les données pertinentes d'un monument."""
        try:
            imageinfo = page_data.get('imageinfo', [{}])[0]
            extmetadata = imageinfo.get('extmetadata', {})

            # Extraction du nom du monument
            monument_name = (
                    extmetadata.get('ObjectName', {}).get('value') or
                    extmetadata.get('ImageDescription', {}).get('value') or
                    filename.replace('File:', '').split('.')[0]
            )

            # Nettoyage du nom (suppression des balises HTML)
            monument_name = re.sub('<[^<]+?>', '', str(monument_name))

            # Extraction de la ville/lieu
            location = None
            categories = page_data.get('categories', [])
            for cat in categories:
                cat_title = cat.get('title', '')
                # Recherche de patterns de villes
                if 'in ' in cat_title or 'de ' in cat_title:
                    location = cat_title.split('Category:')[-1]
                    break

            # Extraction des coordonnées GPS
            coordinates = page_data.get('coordinates', [])
            lat, lon = None, None
            if coordinates:
                lat = coordinates[0].get('lat')
                lon = coordinates[0].get('lon')

            # Extraction de toutes les métadonnées Wikimedia Commons
            metadata = {}
            for key, value in extmetadata.items():
                if isinstance(value, dict) and 'value' in value:
                    # Nettoyage des balises HTML dans les métadonnées
                    clean_value = re.sub('<[^<]+?>', '', str(value['value']))
                    metadata[key] = clean_value
                else:
                    metadata[key] = str(value) if value else None

            # Extraction des noms de lieux (entités nommées)
            extracted_places = self.extract_all_locations(
                page_data, filename, monument_name, metadata
            )

            # Structure de données à sauvegarder
            result = {
                'filename': filename,
                'monument_name': monument_name[:500],  # Limite de longueur
                'location': location,
                'latitude': lat,
                'longitude': lon,
                'image_url': imageinfo.get('url'),
                'width': imageinfo.get('width'),
                'height': imageinfo.get('height'),
                'timestamp': datetime.utcnow().isoformat(),
                'wikimedia_metadata': metadata,  # Toutes les métadonnées
                'categories': [cat.get('title', '').replace('Category:', '') for cat in categories],
                'extracted_places': extracted_places  # Liste de lieux extraits
            }

            # Vérifier qu'on a au moins des coordonnées ou un nom valide
            if (lat and lon) or (monument_name and len(monument_name) > 3):
                return result

            return None

        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des données: {e}")
            return None

    def save_to_jsonl(self, data: Dict):
        """Sauvegarde une entrée dans le fichier JSON Lines."""
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")

    def process_category(self, category: str, max_images: int = 100):
        """Traite une catégorie complète."""
        logger.info(f"Traitement de la catégorie: {category}")

        # Recherche des fichiers
        files = self.search_monuments(category, max_images)

        processed = 0
        saved = 0

        for i, filename in enumerate(files, 1):
            logger.info(f"Traitement {i}/{len(files)}: {filename}")

            # Récupération des informations
            page_data = self.get_image_info(filename)
            if not page_data:
                continue

            processed += 1

            # Extraction des données structurées
            monument_data = self.extract_monument_data(page_data, filename)
            if monument_data:
                self.save_to_jsonl(monument_data)
                saved += 1
                places_info = f" - Lieux: {', '.join(monument_data['extracted_places'][:3])}" if monument_data[
                    'extracted_places'] else ""
                logger.info(f"✓ Sauvegardé: {monument_data['monument_name'][:50]}{places_info}")

            # Pause pour respecter les limites
            time.sleep(self.delay)

        logger.info(f"Catégorie terminée: {processed} traités, {saved} sauvegardés")

    def process_keywords(self, keywords: str, max_images: int = 100):
        """Traite une recherche par mots-clés."""
        logger.info(f"Traitement de la recherche: '{keywords}'")

        # Recherche des fichiers par mots-clés
        files = self.search_by_keywords(keywords, max_images)

        processed = 0
        saved = 0

        for i, filename in enumerate(files, 1):
            logger.info(f"Traitement {i}/{len(files)}: {filename}")

            # Récupération des informations
            page_data = self.get_image_info(filename)
            if not page_data:
                continue

            processed += 1

            # Extraction des données structurées
            monument_data = self.extract_monument_data(page_data, filename)
            if monument_data:
                self.save_to_jsonl(monument_data)
                saved += 1
                places_info = f" - Lieux: {', '.join(monument_data['extracted_places'][:3])}" if monument_data[
                    'extracted_places'] else ""
                logger.info(f"✓ Sauvegardé: {monument_data['monument_name'][:50]}{places_info}")

            # Pause pour respecter les limites
            time.sleep(self.delay)

        logger.info(f"Recherche terminée: {processed} traités, {saved} sauvegardés")

    def run(self, categories: List[str] = None, keywords_list: List[str] = None,
            max_per_search: int = 100):
        """Lance le scraping sur plusieurs catégories et/ou recherches par mots-clés."""
        logger.info("=== Début du scraping ===")
        logger.info(f"Fichier de sortie: {self.output_file}")

        # Traitement des catégories
        if categories:
            logger.info(f"\n>>> Traitement de {len(categories)} catégories")
            for category in categories:
                try:
                    self.process_category(category, max_per_search)
                except Exception as e:
                    logger.error(f"Erreur sur la catégorie {category}: {e}")
                    continue

        # Traitement des recherches par mots-clés
        if keywords_list:
            logger.info(f"\n>>> Traitement de {len(keywords_list)} recherches par mots-clés")
            for keywords in keywords_list:
                try:
                    self.process_keywords(keywords, max_per_search)
                except Exception as e:
                    logger.error(f"Erreur sur la recherche '{keywords}': {e}")
                    continue

        logger.info("=== Scraping terminé ===")


def main():
    # Liste de catégories pertinentes pour les monuments français
    categories = [
        "Category:Monuments historiques in France",
        "Category:Châteaux in France",
        "Category:Churches in France",
        "Category:Cathedrals in France",
        "Category:Historic monuments in Paris",
        "Category:Castles in Île-de-France",
        "Category:Roman architecture in France"
    ]
    categories = [ # pour sauter l'étape catégories
    ]

    # Liste de recherches par mots-clés déjà traitée; remplacée par liste suivante
    keywords_searches = [
        "église France",
        "monument France",
        "château Lot",
        "château Loire",
        "cathédrale France",
        "abbaye France",
        "basilique France",
        "château Dordogne",
        "église Bretagne",
        "monument Provence",
        "château Normandie",
        "église Alsace",
        "château Bourgogne",
        "monument Languedoc",
        "église Auvergne",
        "château Périgord",
        "monument Aquitaine",
        "église Limousin",
        "château Midi-Pyrénées",
        "monument Rhône-Alpes"
    ]
    # Liste de recherches par mots-clés 2eme série pour compléter la 1ere déjà traitée
    keywords_searches = [
        "cathédrale Lot",
        "cathédrale Loire",
        "cathédrale Dordogne",
        "cathédrale Normandie",
        "cathédrale Bourgogne",
        "cathédrale Périgord",
        "cathédrale Midi-Pyrénées",
        "cathédrale Bretagne",
        "cathédrale Alsace",
        "cathédrale Auvergne",
        "cathédrale Limousin",
        "cathédrale Provence",
        "cathédrale Languedoc",
        "cathédrale Aquitaine",
        "cathédrale Rhône-Alpes"

        "abbaye Lot",
        "abbaye Loire",
        "abbaye Dordogne",
        "abbaye Normandie",
        "abbaye Bourgogne",
        "abbaye Périgord",
        "abbaye Midi-Pyrénées",
        "abbaye Bretagne",
        "abbaye Alsace",
        "abbaye Auvergne",
        "abbaye Limousin",
        "abbaye Provence",
        "abbaye Languedoc",
        "abbaye Aquitaine",
        "abbaye Rhône-Alpes"

        "basilique Lot",
        "basilique Loire",
        "basilique Dordogne",
        "basilique Normandie",
        "basilique Bourgogne",
        "basilique Périgord",
        "basilique Midi-Pyrénées",
        "basilique Bretagne",
        "basilique Alsace",
        "basilique Auvergne",
        "basilique Limousin",
        "basilique Provence",
        "basilique Languedoc",
        "basilique Aquitaine",
        "basilique Rhône-Alpes"

        # "château Lot",
        #"château Loire",
        #"château Dordogne",
        #"château Normandie",
        #"château Bourgogne",
        #"château Périgord",
        #"château Midi-Pyrénées",
        "château Bretagne",
        "château Alsace",
        "château Auvergne",
        "château Limousin",
        "château Provence",
        "château Languedoc",
        "château Aquitaine",
        "château Rhône-Alpes"

        #"église Bretagne",
        #"église Alsace",
        #"église Auvergne",
        #"église Limousin",
        "église Lot",
        "église Loire",
        "église Dordogne",
        "église Normandie",
        "église Bourgogne",
        "église Périgord",
        "église Midi-Pyrénées",
        "église Provence",
        "église Languedoc",
        "église Aquitaine",
        "église Rhône-Alpes"

        #"monument Provence",
        #"monument Languedoc",
        #"monument Aquitaine",
        #"monument Rhône-Alpes"
        "monument Lot",
        "monument Loire",
        "monument Dordogne",
        "monument Normandie",
        "monument Bourgogne",
        "monument Périgord",
        "monument Midi-Pyrénées",
        "monument Bretagne",
        "monument Alsace",
        "monument Auvergne",
        "monument Limousin",
    ]

    # Initialisation du scraper
    scraper = WikimediaMonumentsScraper(output_file="monuments_france.jsonl")

    # Lancement du scraping
    # Limiter à 100 images par recherche pour commencer
    scraper.run(
        categories=categories,
        keywords_list=keywords_searches,
        max_per_search=100
    )

    print(f"\nRésultats sauvegardés dans: {scraper.output_file}")


if __name__ == "__main__":
    main()