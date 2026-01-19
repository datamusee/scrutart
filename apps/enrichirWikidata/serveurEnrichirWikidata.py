#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application Flask pour l'enrichissement de Wikidata
Version améliorée avec extracteurs et matchers modulaires
"""

from flask import Flask, render_template, request, jsonify, session
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# Imports des modules personnalisés
from extractor_manager import ExtractorManager
from matcher_manager import MatcherManager
from wikidata_enrichir import WikidataEnrichir
from property_matcher import PropertyMatcher

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
CONFIG_FILE = 'config.json'
SINGLE_URL_HISTORY = 'data/single_url_history.json'
LIST_PROCESSING_DIR = 'data/list_processing'

# Créer les répertoires nécessaires
os.makedirs('data', exist_ok=True)
os.makedirs(LIST_PROCESSING_DIR, exist_ok=True)
os.makedirs('data/wikidata_cache', exist_ok=True)

# Initialiser les gestionnaires
extractor_manager = ExtractorManager('extractors')
matcher_manager = MatcherManager('matchers')
property_matcher = PropertyMatcher()


class ProcessingManager:
    """Classe pour gérer le traitement des URLs"""

    @staticmethod
    def load_url_list(file_path: str) -> List[str]:
        """Charger une liste d'URLs depuis un fichier"""
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return urls

    @staticmethod
    def get_list_state_file(list_filename: str) -> str:
        """Obtenir le nom du fichier d'état pour une liste"""
        base_name = os.path.splitext(os.path.basename(list_filename))[0]
        return os.path.join(LIST_PROCESSING_DIR, f"{base_name}_state.json")

    @staticmethod
    def load_list_state(list_filename: str) -> Dict:
        """Charger l'état de traitement d'une liste"""
        state_file = ProcessingManager.get_list_state_file(list_filename)
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'list_file': list_filename,
            'current_index': 0,
            'total_urls': 0,
            'processed': [],
            'created_at': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat()
        }

    @staticmethod
    def save_list_state(list_filename: str, state: Dict):
        """Sauvegarder l'état de traitement d'une liste"""
        state['last_update'] = datetime.now().isoformat()
        state_file = ProcessingManager.get_list_state_file(list_filename)
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    @staticmethod
    def add_to_single_url_history(url: str, result: Dict):
        """Ajouter une URL au historique des URLs unitaires"""
        history = []
        if os.path.exists(SINGLE_URL_HISTORY):
            with open(SINGLE_URL_HISTORY, 'r', encoding='utf-8') as f:
                history = json.load(f)

        history.append({
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'result': result
        })

        with open(SINGLE_URL_HISTORY, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)


def load_config() -> Dict:
    """Charger la configuration"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_config(config: Dict):
    """Sauvegarder la configuration"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# Routes Flask

@app.route('/')
def index():
    """Page d'accueil"""
    extractors = extractor_manager.list_extractors()
    return render_template('index.html', extractors=extractors)


@app.route('/config', methods=['GET', 'POST'])
def config():
    """Page de configuration"""
    if request.method == 'POST':
        config_data = {
            'wikidata_username': request.form.get('username', ''),
            'wikidata_password': request.form.get('password', '')
        }
        save_config(config_data)
        return jsonify({'success': True, 'message': 'Configuration sauvegardée'})

    config_data = load_config()
    return render_template('config.html', config=config_data)


@app.route('/list_extractors', methods=['GET'])
def list_extractors():
    """Lister tous les extracteurs disponibles"""
    extractors = extractor_manager.list_extractors()
    return jsonify({'extractors': extractors})


@app.route('/list_matchers', methods=['GET'])
def list_matchers():
    """Lister tous les matchers disponibles"""
    entity_type = request.args.get('type', None)

    if entity_type:
        matchers = matcher_manager.list_matchers_for_type(entity_type)
    else:
        matchers = matcher_manager.list_matchers()

    return jsonify({'matchers': matchers})


@app.route('/process_url', methods=['POST'])
def process_url():
    """Traiter une URL unique"""
    data = request.json
    url = data.get('url', '')
    extractor_name = data.get('extractor', None)
    matcher_name = data.get('matcher', None)

    if not url:
        return jsonify({'error': 'URL manquante'}), 400

    # Extraire les informations de l'URL
    content_info = extractor_manager.extract_from_url(url, extractor_name)

    if 'error' in content_info:
        return jsonify({'error': content_info['error']}), 400

    # Déterminer le type d'entité
    entity_type = content_info.get('type', 'unknown')

    # Utiliser les matchers pour trouver des correspondances Wikidata
    wikidata_matches = matcher_manager.find_matches(
        entity_type,
        content_info,
        matcher_name
    )

    # Rechercher dans Wikidata (ancienne méthode - gardée pour les concepts)
    config_data = load_config()
    enrichir = WikidataEnrichir(
        config_data.get('wikidata_username', ''),
        config_data.get('wikidata_password', '')
    )

    # Mapper les concepts/mots-clés vers Wikidata
    keywords = content_info.get('keywords', [])
    depicted_persons = content_info.get('depicted_persons', [])

    concepts_mapping = {}
    if keywords:
        concepts_mapping = enrichir.map_concepts_to_wikidata(keywords)

    # Rechercher les personnes représentées
    persons_mapping = {}
    if depicted_persons:
        for person in depicted_persons:
            persons_matches = enrichir.search_person(person)
            if persons_matches:
                persons_mapping[person] = persons_matches[0]

    # Rechercher le créateur avec le matcher approprié
    creator_match = None
    if content_info.get('creator'):
        # Utiliser le matcher artiste
        artist_data = {
            'type': 'artist',
            'name': content_info['creator'],
            'creator_birth': content_info.get('creator_birth', ''),
            'creator_death': content_info.get('creator_death', '')
        }
        creator_matches = matcher_manager.find_matches('artist', artist_data)
        if creator_matches:
            creator_match = creator_matches[0]

    result = {
        'content_info': content_info,
        'wikidata_matches': wikidata_matches,
        'concepts_mapping': concepts_mapping,
        'persons_mapping': persons_mapping,
        'creator_match': creator_match
    }

    # Sauvegarder dans l'historique
    ProcessingManager.add_to_single_url_history(url, result)

    return jsonify(result)


@app.route('/upload_list', methods=['POST'])
def upload_list():
    """Charger un fichier de liste d'URLs"""
    if 'file' not in request.files:
        return jsonify({'error': 'Pas de fichier'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nom de fichier vide'}), 400

    # Récupérer l'extracteur choisi (optionnel)
    extractor_name = request.form.get('extractor', None)

    # Sauvegarder le fichier
    file_path = os.path.join('data', file.filename)
    file.save(file_path)

    # Charger les URLs
    urls = ProcessingManager.load_url_list(file_path)

    # Initialiser l'état
    state = ProcessingManager.load_list_state(file.filename)
    state['total_urls'] = len(urls)
    state['urls'] = urls
    state['extractor'] = extractor_name
    ProcessingManager.save_list_state(file.filename, state)

    return jsonify({
        'success': True,
        'filename': file.filename,
        'total_urls': len(urls),
        'state': state
    })


@app.route('/process_list_item', methods=['POST'])
def process_list_item():
    """Traiter un élément de la liste"""
    data = request.json
    list_filename = data.get('list_filename', '')
    index = data.get('index', 0)

    # Charger l'état
    state = ProcessingManager.load_list_state(list_filename)
    urls = state.get('urls', [])
    extractor_name = state.get('extractor', None)

    if index < 0 or index >= len(urls):
        return jsonify({'error': 'Index invalide'}), 400

    url = urls[index]

    # Traiter l'URL
    content_info = extractor_manager.extract_from_url(url, extractor_name)

    if 'error' in content_info:
        return jsonify({'error': content_info['error']}), 400

    # Rechercher dans Wikidata
    config_data = load_config()
    enrichir = WikidataEnrichir(
        config_data.get('wikidata_username', ''),
        config_data.get('wikidata_password', '')
    )

    search_term = content_info.get('title') or content_info.get('name', '')
    wikidata_matches = enrichir.search_entity(search_term) if search_term else []

    # Mapper les concepts
    keywords = content_info.get('keywords', [])
    concepts_mapping = {}
    if keywords:
        concepts_mapping = enrichir.map_concepts_to_wikidata(keywords)

    # Personnes représentées
    depicted_persons = content_info.get('depicted_persons', [])
    persons_mapping = {}
    if depicted_persons:
        for person in depicted_persons:
            persons_matches = enrichir.search_person(person)
            if persons_matches:
                persons_mapping[person] = persons_matches[0]

    # Créateur
    creator_match = None
    if content_info.get('creator'):
        creator_birth = content_info.get('creator_birth')
        creator_death = content_info.get('creator_death')
        creator_matches = enrichir.search_person(
            content_info['creator'],
            creator_birth,
            creator_death
        )
        if creator_matches:
            creator_match = creator_matches[0]

    result = {
        'index': index,
        'url': url,
        'content_info': content_info,
        'wikidata_matches': wikidata_matches,
        'concepts_mapping': concepts_mapping,
        'persons_mapping': persons_mapping,
        'creator_match': creator_match
    }

    return jsonify(result)


@app.route('/validate_match', methods=['POST'])
def validate_match():
    """Valider une correspondance Wikidata"""
    data = request.json
    entity_id = data.get('entity_id', '')
    new_properties = data.get('new_properties', [])
    list_filename = data.get('list_filename', '')
    index = data.get('index', 0)

    # Ajouter les propriétés
    config_data = load_config()
    enrichir = WikidataEnrichir(
        config_data.get('wikidata_username', ''),
        config_data.get('wikidata_password', '')
    )

    success = enrichir.add_claims(entity_id, new_properties)

    # Mettre à jour l'état
    if list_filename:
        state = ProcessingManager.load_list_state(list_filename)
        state['processed'].append({
            'index': index,
            'entity_id': entity_id,
            'action': 'enriched',
            'timestamp': datetime.now().isoformat()
        })
        state['current_index'] = index + 1
        ProcessingManager.save_list_state(list_filename, state)

    return jsonify({'success': success, 'entity_id': entity_id})


@app.route('/create_entity', methods=['POST'])
def create_entity():
    """Créer une nouvelle entité Wikidata"""
    data = request.json
    entity_data = data.get('entity_data', {})
    list_filename = data.get('list_filename', '')
    index = data.get('index', 0)

    # Créer l'entité
    config_data = load_config()
    enrichir = WikidataEnrichir(
        config_data.get('wikidata_username', ''),
        config_data.get('wikidata_password', '')
    )

    entity_id = enrichir.create_entity(entity_data)

    # Mettre à jour l'état
    if list_filename:
        state = ProcessingManager.load_list_state(list_filename)
        state['processed'].append({
            'index': index,
            'entity_id': entity_id,
            'action': 'created',
            'timestamp': datetime.now().isoformat()
        })
        state['current_index'] = index + 1
        ProcessingManager.save_list_state(list_filename, state)

    return jsonify({'success': True, 'entity_id': entity_id})


@app.route('/list_state/<filename>', methods=['GET'])
def get_list_state(filename):
    """Obtenir l'état d'une liste"""
    state = ProcessingManager.load_list_state(filename)
    return jsonify(state)


@app.route('/reset_list/<filename>', methods=['POST'])
def reset_list(filename):
    """Réinitialiser le traitement d'une liste"""
    state = ProcessingManager.load_list_state(filename)
    state['current_index'] = 0
    state['processed'] = []
    ProcessingManager.save_list_state(filename, state)
    return jsonify({'success': True, 'state': state})


@app.route('/cache_stats', methods=['GET'])
def cache_stats():
    """Obtenir les statistiques du cache Wikidata"""
    config_data = load_config()
    enrichir = WikidataEnrichir(
        config_data.get('wikidata_username', ''),
        config_data.get('wikidata_password', '')
    )

    stats = enrichir.get_cache_stats()
    return jsonify(stats)


@app.route('/match_properties', methods=['POST'])
def match_properties():
    """
    Matcher les propriétés d'une entité extraite avec des entités Wikidata

    Exemple de requête:
    {
        "extracted_data": {
            "creator": "TOUDOUZE Edouard",
            "creator_birth": "1848",
            "creator_death": "1907",
            "keywords": ["scène historique", "cadavre", "lit"],
            "depicted_persons": ["Bertrand Du Guesclin"]
        },
        "entity_type": "painting"
    }
    """
    data = request.json
    extracted_data = data.get('extracted_data', {})
    entity_type = data.get('entity_type', 'painting')

    if not extracted_data:
        return jsonify({'error': 'Données extraites manquantes'}), 400

    # Matcher toutes les propriétés
    property_matches = property_matcher.match_all_properties(extracted_data, entity_type)

    return jsonify({
        'success': True,
        'property_matches': property_matches
    })


if __name__ == '__main__':
    print("=" * 60)
    print("Application d'enrichissement Wikidata")
    print("=" * 60)
    print(f"Extracteurs chargés: {len(extractor_manager.extractors)}")
    for ext in extractor_manager.extractors:
        print(f"  - {ext.name}")
    print(f"\nMatchers chargés: {len(matcher_manager.matchers)}")
    for matcher in matcher_manager.matchers:
        print(f"  - {matcher.name} ({', '.join(matcher.supported_types)})")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5000)
