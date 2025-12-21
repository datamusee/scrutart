from flask import Flask, render_template, request, jsonify
import requests
from requests.auth import HTTPBasicAuth
import json
import os
import sqlite3
from datetime import datetime
from CPiwigoManager import CPiwigoManager, CategoryType
import re

app = Flask(__name__)

pimag = CPiwigoManager()

# Configuration Piwigo
PIWIGO_URL = "https://galeries.grains-de-culture.fr"
PIWIGO_USER = pimag.login
PIWIGO_PASSWORD = pimag.password

# Base de données pour suivre les images traitées
DB_PATH = "processed_images.db"

# Session Piwigo
piwigo_session = requests.Session()


def init_database():
    """Initialise la base de données pour suivre les images traitées"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_images (
            image_id INTEGER PRIMARY KEY,
            processed_date TEXT NOT NULL,
            tags_added TEXT,
            wikidata_entity TEXT
        )
    ''')
    conn.commit()
    conn.close()


def mark_image_processed(image_id, tags_added, wikidata_entity=None):
    """Marque une image comme traitée"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO processed_images 
        (image_id, processed_date, tags_added, wikidata_entity)
        VALUES (?, ?, ?, ?)
    ''', (image_id, datetime.now().isoformat(), json.dumps(tags_added), wikidata_entity))
    conn.commit()
    conn.close()


def is_image_processed(image_id):
    """Vérifie si une image a déjà été traitée"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT image_id FROM processed_images WHERE image_id = ?', (image_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_processed_images_info(image_id):
    """Récupère les informations de traitement d'une image"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT processed_date, tags_added, wikidata_entity 
        FROM processed_images 
        WHERE image_id = ?
    ''', (image_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'processed_date': result[0],
            'tags_added': json.loads(result[1]) if result[1] else [],
            'wikidata_entity': result[2]
        }
    return None


def unmark_image_processed(image_id):
    """Supprime le marquage d'une image (pour retraiter)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM processed_images WHERE image_id = ?', (image_id,))
    conn.commit()
    conn.close()


def get_stats():
    """Récupère les statistiques de traitement"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM processed_images')
    total = cursor.fetchone()[0]
    conn.close()
    return {'total_processed': total}


def login_piwigo():
    """Connexion à Piwigo"""
    url = f"{PIWIGO_URL}/ws.php?format=json"
    data = {
        'method': 'pwg.session.login',
        'username': PIWIGO_USER,
        'password': PIWIGO_PASSWORD
    }
    response = piwigo_session.post(url, data=data)
    return response.json()


def get_piwigo_images(page=0, per_page=10):
    """Récupère les images de Piwigo"""
    url = f"{PIWIGO_URL}/ws.php?format=json"
    data = {
        'method': 'pwg.images.search',
        'query':'christ',
        'page': page,
        'per_page': per_page
    }
    response = piwigo_session.post(url, data=data)
    return response.json()


def get_image_info(image_id):
    """Récupère les informations complètes d'une image"""
    url = f"{PIWIGO_URL}/ws.php?format=json"
    data = {
        'method': 'pwg.images.getInfo',
        'image_id': image_id
    }
    response = piwigo_session.post(url, data=data)
    result = response.json()
    if result.get('stat') == 'ok':
        return result.get('result', {})
    return {}


def extract_author_from_categories(categories):
    """Extrait le nom de l'auteur depuis les catégories/galeries"""
    for cat in categories:
        name = cat.get('name', '')
        # Recherche de patterns comme "Galerie XXX", "Artiste XXX", etc.
        if 'galerie' in name.lower():
            return name.replace('Galerie', '').replace('galerie', '').strip()
        if 'artiste' in name.lower():
            return name.replace('Artiste', '').replace('artiste', '').strip()
        # Si c'est un nom propre (commence par majuscule et contient espace)
        if name and name[0].isupper() and ' ' in name:
            return name.strip()
    return None


def extract_commons_url(description):
    """Extrait l'URL Wikimedia Commons depuis la description"""
    if not description:
        return None

    # Recherche d'URLs Wikimedia Commons
    patterns = [
        r'https?://commons\.wikimedia\.org/wiki/File:([^"\s<>]+)',
        r'https?://commons\.wikimedia\.org/wiki/([^"\s<>]+)',
        r'commons\.wikimedia\.org/wiki/File:([^"\s<>]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            return match.group(0) if match.group(0).startswith(
                'http') else f"https://commons.wikimedia.org/wiki/{match.group(1)}"

    return None


def get_wikidata_from_commons(commons_url):
    """Récupère l'entité Wikidata depuis une page Wikimedia Commons"""
    if not commons_url:
        return None

    try:
        # Extraire le nom du fichier
        match = re.search(r'File:(.+)$', commons_url)
        if not match:
            return None

        filename = match.group(1).replace('_', ' ')

        # Rechercher sur Wikidata avec le nom du fichier
        url = "https://www.wikidata.org/w/api.php"
        params = {
            'action': 'wbsearchentities',
            'format': 'json',
            'language': 'fr',
            'type': 'item',
            'search': filename,
            'limit': 1
        }
        response = requests.get(url, params=params)
        data = response.json()

        if data.get('search'):
            return data['search'][0]['id']
    except Exception as e:
        print(f"Erreur lors de la recherche Commons: {e}")

    return None


def search_wikidata_entity(query):
    """Recherche une entité sur Wikidata"""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbsearchentities',
        'format': 'json',
        'language': 'fr',
        'type': 'item',
        'search': query,
        'limit': 1
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data.get('search'):
        return data['search'][0]
    return None


def search_artwork_on_wikidata(title, author=None):
    """Recherche une œuvre d'art sur Wikidata en utilisant le titre et l'auteur"""
    # Construire la requête de recherche
    search_query = title
    if author:
        search_query = f"{title} {author}"

    # Recherche initiale
    entity = search_wikidata_entity(search_query)
    if entity:
        return entity['id']

    # Si pas trouvé et qu'on a un auteur, essayer juste avec le titre
    if author:
        entity = search_wikidata_entity(title)
        if entity:
            return entity['id']

    return None


def get_wikidata_depicts(entity_id):
    """Récupère les depicts d'une entité Wikidata"""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbgetclaims',
        'format': 'json',
        'entity': entity_id,
        'property': 'P180'  # P180 = depicts
    }
    response = requests.get(url, params=params)
    data = response.json()

    depicts = []
    claims = data.get('claims', {}).get('P180', [])

    for claim in claims:
        try:
            depicted_entity = claim['mainsnak']['datavalue']['value']['id']
            label = get_wikidata_label(depicted_entity)
            depicts.append({
                'id': depicted_entity,
                'label': label,
                'url': f"https://www.wikidata.org/wiki/{depicted_entity}"
            })
        except (KeyError, TypeError):
            continue

    return depicts


def get_wikidata_label(entity_id, langs=['fr', 'en', 'es']):
    """Récupère le label d'une entité Wikidata"""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbgetentities',
        'format': 'json',
        'ids': entity_id,
        'props': 'labels',
        'languages': '|'.join(langs)
    }
    response = requests.get(url, params=params)
    data = response.json()

    entity = data.get('entities', {}).get(entity_id, {})
    labels = entity.get('labels', {})

    for lang in langs:
        if lang in labels:
            return labels[lang]['value']

    return entity_id


def add_tags_to_image(image_id, tags):
    """Ajoute des tags à une image dans Piwigo"""
    url = f"{PIWIGO_URL}/ws.php?format=json"

    # Créer les tags s'ils n'existent pas et récupérer leurs IDs
    tag_ids = []
    for tag in tags:
        # Rechercher si le tag existe
        search_data = {
            'method': 'pwg.tags.getList'
        }
        response = piwigo_session.post(url, data=search_data)
        existing_tags = response.json().get('result', {}).get('tags', [])

        tag_id = None
        for existing_tag in existing_tags:
            if existing_tag.get('name') == tag['label']:
                tag_id = existing_tag.get('id')
                break

        # Créer le tag s'il n'existe pas
        if not tag_id:
            create_data = {
                'method': 'pwg.tags.add',
                'name': tag['label']
            }
            if tag.get('url'):
                create_data['url_name'] = tag['url']

            create_response = piwigo_session.post(url, data=create_data)
            result = create_response.json()
            if result.get('stat') == 'ok':
                tag_id = result.get('result', {}).get('id')

        if tag_id:
            tag_ids.append(tag_id)

    # Associer les tags à l'image
    if tag_ids:
        data = {
            'method': 'pwg.images.setInfo',
            'image_id': image_id,
            'tag_ids': ','.join(map(str, tag_ids))
        }
        response = piwigo_session.post(url, data=data)
        return response.json()

    return {'stat': 'fail', 'message': 'No tags to add'}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/images')
def get_images():
    page = request.args.get('page', 0, type=int)
    show_all = request.args.get('show_all', 'false').lower() == 'true'

    login_piwigo()
    images_data = get_piwigo_images(page=page, per_page=10)

    if images_data.get('stat') != 'ok':
        return jsonify({'error': 'Erreur lors de la récupération des images'}), 500

    images = images_data.get('result', {}).get('images', [])

    result = []
    for img in images:
        # Vérifier si l'image a déjà été traitée
        processed_info = get_processed_images_info(img['id'])
        is_processed = processed_info is not None

        # Si l'image est traitée et qu'on ne veut pas voir les images traitées, on la saute
        if is_processed and not show_all:
            continue

        # Récupérer les informations complètes de l'image
        img_info = get_image_info(img['id'])

        title = img_info.get('name', img_info.get('file', 'Sans nom'))
        tags = img_info.get('tags', [])
        categories = img_info.get('categories', [])
        description = img_info.get('comment', '')

        # Extraire l'auteur depuis les catégories/galeries
        author = extract_author_from_categories(categories)

        # Extraire l'URL Commons depuis la description
        commons_url = extract_commons_url(description)

        # Rechercher l'entité Wikidata
        entity_id = None
        search_info = {
            'title': title,
            'author': author,
            'commons_url': commons_url
        }

        # 1. Essayer d'abord avec l'URL Commons si disponible
        if commons_url:
            entity_id = get_wikidata_from_commons(commons_url)

        # 2. Sinon, rechercher avec titre et auteur
        if not entity_id:
            entity_id = search_artwork_on_wikidata(title, author)

        # 3. En dernier recours, essayer avec les tags
        if not entity_id and tags:
            entity = search_wikidata_entity(tags[0]['name'])
            if entity:
                entity_id = entity['id']

        # Récupérer les depicts si on a trouvé une entité
        depicts = []
        if entity_id:
            depicts = get_wikidata_depicts(entity_id)

        result.append({
            'id': img['id'],
            'url': img['derivatives']['large']['url'],
            'name': title,
            'author': author,
            'commons_url': commons_url,
            'wikidata_entity': entity_id,
            'tags': tags,
            'depicts': depicts,
            'search_info': search_info,
            'is_processed': is_processed,
            'processed_info': processed_info
        })

    return jsonify({
        'images': result,
        'has_more': len(images) == 10
    })


@app.route('/api/add_tags', methods=['POST'])
def add_tags():
    data = request.json
    image_id = data.get('image_id')
    validated_tags = data.get('tags', [])
    wikidata_entity = data.get('wikidata_entity')

    result = add_tags_to_image(image_id, validated_tags)

    if result.get('stat') == 'ok':
        # Marquer l'image comme traitée
        mark_image_processed(image_id, validated_tags, wikidata_entity)
        return jsonify({'success': True, 'message': 'Tags ajoutés avec succès'})
    else:
        return jsonify({'success': False, 'message': 'Erreur lors de l\'ajout des tags'}), 500


@app.route('/api/unmark_image', methods=['POST'])
def unmark_image():
    """Permet de retirer le marquage d'une image pour la retraiter"""
    data = request.json
    image_id = data.get('image_id')

    unmark_image_processed(image_id)
    return jsonify({'success': True, 'message': 'Image marquée comme non traitée'})


@app.route('/api/stats')
def get_processing_stats():
    """Récupère les statistiques de traitement"""
    return jsonify(get_stats())


if __name__ == '__main__':
    # Initialiser la base de données
    init_database()

    # Créer le template HTML
    os.makedirs('templates', exist_ok=True)

    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piwigo - Wikidata Tagger</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
        h1 { text-align: center; margin-bottom: 20px; color: #333; }
        .header { max-width: 1400px; margin: 0 auto 20px; }
        .stats { display: flex; gap: 20px; justify-content: center; align-items: center; margin-bottom: 20px; }
        .stat-box { background: white; padding: 15px 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-box strong { display: block; font-size: 24px; color: #1976d2; }
        .stat-box span { font-size: 13px; color: #666; }
        .filter-controls { display: flex; gap: 15px; justify-content: center; align-items: center; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .filter-controls label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
        .filter-controls input[type="checkbox"] { width: 18px; height: 18px; cursor: pointer; }
        .container { max-width: 1400px; margin: 0 auto; }
        .image-grid { display: grid; gap: 20px; }
        .image-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: relative; }
        .image-card.processed { border: 3px solid #4caf50; }
        .processed-badge { position: absolute; top: 10px; right: 10px; background: #4caf50; color: white; padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .image-content { display: grid; grid-template-columns: 400px 1fr; gap: 20px; }
        .image-wrapper img { width: 100%; height: auto; border-radius: 4px; }
        .tags-section { display: flex; flex-direction: column; gap: 15px; }
        .tags-group { padding: 10px; background: #f9f9f9; border-radius: 4px; }
        .tags-group h3 { margin-bottom: 10px; font-size: 14px; color: #666; }
        .tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
        .tag { padding: 6px 12px; background: #e3f2fd; border-radius: 4px; font-size: 13px; color: #1976d2; }
        .depicts-item { display: flex; align-items: center; gap: 10px; padding: 8px; background: white; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 8px; }
        .depicts-item input[type="checkbox"] { width: 18px; height: 18px; cursor: pointer; }
        .depicts-label { flex: 1; cursor: pointer; }
        .depicts-link { color: #1976d2; text-decoration: none; font-size: 12px; }
        .depicts-link:hover { text-decoration: underline; }
        .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; font-weight: bold; }
        .btn-primary { background: #1976d2; color: white; }
        .btn-primary:hover { background: #1565c0; }
        .btn-primary:disabled { background: #bdbdbd; cursor: not-allowed; }
        .btn-secondary { background: #757575; color: white; margin-right: 10px; }
        .btn-secondary:hover { background: #616161; }
        .actions { display: flex; justify-content: flex-end; margin-top: 15px; }
        .loading { text-align: center; padding: 40px; color: #666; }
        .message { padding: 12px; margin: 10px 0; border-radius: 4px; }
        .message.success { background: #c8e6c9; color: #2e7d32; }
        .message.error { background: #ffcdd2; color: #c62828; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖼️ Piwigo - Wikidata Tagger</h1>
        <div class="stats">
            <div class="stat-box">
                <strong id="processedCount">0</strong>
                <span>images traitées</span>
            </div>
        </div>
        <div class="filter-controls">
            <label>
                <input type="checkbox" id="showAllCheckbox" onchange="toggleShowAll()">
                <span>Afficher aussi les images déjà traitées</span>
            </label>
        </div>
    </div>
    <div class="container">
        <div id="messages"></div>
        <div id="images" class="image-grid"></div>
        <div class="actions" style="margin-top: 20px;">
            <button class="btn btn-secondary" id="prevBtn" onclick="loadPrevPage()">← Précédent</button>
            <button class="btn btn-primary" id="nextBtn" onclick="loadNextPage()">Suivant →</button>
        </div>
    </div>

    <script>
        let currentPage = 0;
        let showAll = false;

        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                document.getElementById('processedCount').textContent = data.total_processed;
            } catch (error) {
                console.error('Erreur lors du chargement des stats:', error);
            }
        }

        function toggleShowAll() {
            showAll = document.getElementById('showAllCheckbox').checked;
            currentPage = 0;
            loadImages(currentPage);
        }

        async function loadImages(page) {
            document.getElementById('images').innerHTML = '<div class="loading">Chargement des images...</div>';

            try {
                const response = await fetch(`/api/images?page=${page}&show_all=${showAll}`);
                const data = await response.json();

                if (data.error) {
                    showMessage(data.error, 'error');
                    return;
                }

                renderImages(data.images);
                loadStats();

                document.getElementById('prevBtn').disabled = page === 0;
                document.getElementById('nextBtn').disabled = !data.has_more;
            } catch (error) {
                showMessage('Erreur de connexion', 'error');
            }
        }

        function renderImages(images) {
            const container = document.getElementById('images');
            container.innerHTML = '';

            if (images.length === 0) {
                container.innerHTML = '<div class="loading">✓ Aucune image non traitée sur cette page</div>';
                return;
            }

            images.forEach(img => {
                const card = document.createElement('div');
                card.className = 'image-card' + (img.is_processed ? ' processed' : '');
                card.innerHTML = `
                    ${img.is_processed ? `<div class="processed-badge">✓ Traitée le ${new Date(img.processed_info.processed_date).toLocaleString('fr-FR')}</div>` : ''}
                    <div class="image-content">
                        <div class="image-wrapper">
                            <img src="${img.url}" alt="${img.name}">
                            <p style="margin-top: 10px; font-weight: bold;">${img.name}</p>
                            ${img.author ? `<p style="color: #666; font-size: 13px;">👤 Auteur: ${img.author}</p>` : ''}
                            ${img.commons_url ? `<p style="font-size: 12px;"><a href="${img.commons_url}" target="_blank">🔗 Wikimedia Commons</a></p>` : ''}
                            ${img.wikidata_entity ? `<p style="font-size: 12px;"><a href="https://www.wikidata.org/wiki/${img.wikidata_entity}" target="_blank">📊 Entité Wikidata: ${img.wikidata_entity}</a></p>` : '<p style="font-size: 12px; color: #999;">❌ Aucune entité Wikidata trouvée</p>'}
                        </div>
                        <div class="tags-section">
                            <div class="tags-group">
                                <h3>Tags Piwigo actuels</h3>
                                <div class="tag-list">
                                    ${img.tags.length ? img.tags.map(t => `<span class="tag">${t.name}</span>`).join('') : '<em style="color: #999;">Aucun tag</em>'}
                                </div>
                            </div>
                            ${img.is_processed ? `
                                <div class="tags-group" style="background: #e8f5e9;">
                                    <h3>Tags ajoutés lors du traitement</h3>
                                    <div class="tag-list">
                                        ${img.processed_info.tags_added.map(t => `<span class="tag" style="background: #c8e6c9;">${t.label}</span>`).join('')}
                                    </div>
                                </div>
                            ` : ''}
                            <div class="tags-group">
                                <h3>Depicts Wikidata ${img.is_processed ? '(image déjà traitée)' : '(sélectionnez pour ajouter)'}</h3>
                                ${img.wikidata_entity ? `<p style="font-size: 12px; color: #666; margin-bottom: 8px;">Recherche basée sur: ${img.search_info.commons_url ? '🔗 URL Commons' : img.search_info.author ? `📝 "${img.search_info.title}" par ${img.search_info.author}` : `📝 "${img.search_info.title}"`}</p>` : ''}
                                <div id="depicts-${img.id}">
                                    ${img.depicts.length ? img.depicts.map(d => `
                                        <div class="depicts-item">
                                            <input type="checkbox" id="dep-${img.id}-${d.id}" value="${d.id}" data-label="${d.label}" data-url="${d.url}" ${img.is_processed ? 'disabled' : ''}>
                                            <label class="depicts-label" for="dep-${img.id}-${d.id}">${d.label}</label>
                                            <a href="${d.url}" target="_blank" class="depicts-link">Voir sur Wikidata →</a>
                                        </div>
                                    `).join('') : '<em style="color: #999;">Aucun depicts trouvé sur cette entité</em>'}
                                </div>
                            </div>
                            <div class="actions">
                                ${img.is_processed ? `
                                    <button class="btn btn-secondary" onclick="reprocessImage(${img.id})">🔄 Retraiter cette image</button>
                                ` : `
                                    <button class="btn btn-primary" onclick="sendTags(${img.id}, '${img.wikidata_entity || ''}')" ${img.depicts.length === 0 ? 'disabled' : ''}>📤 Envoyer les tags validés</button>
                                `}
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        async function sendTags(imageId, wikidataEntity) {
            const checkboxes = document.querySelectorAll(`#depicts-${imageId} input[type="checkbox"]:checked`);
            const tags = Array.from(checkboxes).map(cb => ({
                id: cb.value,
                label: cb.dataset.label,
                url: cb.dataset.url
            }));

            if (tags.length === 0) {
                showMessage('Veuillez sélectionner au moins un tag', 'error');
                return;
            }

            try {
                const response = await fetch('/api/add_tags', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        image_id: imageId, 
                        tags: tags,
                        wikidata_entity: wikidataEntity
                    })
                });

                const result = await response.json();

                if (result.success) {
                    showMessage('✓ Tags ajoutés avec succès - Image marquée comme traitée', 'success');
                    loadImages(currentPage);
                } else {
                    showMessage(result.message, 'error');
                }
            } catch (error) {
                showMessage("Erreur lors de l'envoi", 'error');
            }
        }

        async function reprocessImage(imageId) {
            if (!confirm('Voulez-vous vraiment retraiter cette image ?')) {
                return;
            }

            try {
                const response = await fetch('/api/unmark_image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image_id: imageId })
                });

                const result = await response.json();

                if (result.success) {
                    showMessage('✓ Image marquée pour retraitement', 'success');
                    loadImages(currentPage);
                } else {
                    showMessage('Erreur lors du marquage', 'error');
                }
            } catch (error) {
                showMessage('Erreur lors de la communication', 'error');
            }
        }

        function showMessage(text, type) {
            const div = document.createElement('div');
            div.className = `message ${type}`;
            div.textContent = text;
            document.getElementById('messages').appendChild(div);
            setTimeout(() => div.remove(), 5000);
        }

        function loadNextPage() {
            currentPage++;
            loadImages(currentPage);
        }

        function loadPrevPage() {
            if (currentPage > 0) {
                currentPage--;
                loadImages(currentPage);
            }
        }

        loadImages(0);
        loadStats();
    </script>
</body>
</html>''')

    print("=" * 60)
    print("CONFIGURATION REQUISE:")
    print("=" * 60)
    print("Avant de lancer l'application, modifiez les lignes suivantes:")
    print(f"  PIWIGO_URL = '{PIWIGO_URL}'")
    print(f"  PIWIGO_USER = '{PIWIGO_USER}'")
    print(f"  PIWIGO_PASSWORD = '{PIWIGO_PASSWORD}'")
    print("=" * 60)
    print("\nDépendances à installer:")
    print("  pip install flask requests")
    print("=" * 60)

    app.run(debug=False, port=5000)