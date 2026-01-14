from flask import Flask, render_template, request, jsonify
import requests
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import re

app = Flask(__name__)

# Configuration
CONFIG_FILE = 'config.json'
TRACE_FILE = 'trace.json'

class PiwigoDeduplicator:
    def __init__(self):
        self.config = self.load_config()
        self.trace = self.load_trace()
        self.session = requests.Session()
        self.logged_in = False
    
    def load_config(self) -> dict:
        """Charge la configuration depuis le fichier JSON"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'piwigo_url': '',
            'username': '',
            'password': '',
            'reprocess_albums': False
        }
    
    def save_config(self, config: dict):
        """Sauvegarde la configuration"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        self.config = config
    
    def load_trace(self) -> dict:
        """Charge le fichier de trace"""
        if os.path.exists(TRACE_FILE):
            with open(TRACE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'processed_albums': [],
            'operations': []
        }
    
    def save_trace(self):
        """Sauvegarde le fichier de trace"""
        with open(TRACE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.trace, f, indent=2, ensure_ascii=False)
    
    def login(self) -> bool:
        """Se connecte à Piwigo"""
        if not self.config.get('piwigo_url'):
            return False
        
        try:
            url = f"{self.config['piwigo_url']}/ws.php?format=json"
            response = self.session.post(url, data={
                'method': 'pwg.session.login',
                'username': self.config['username'],
                'password': self.config['password']
            })
            result = response.json()
            self.logged_in = result.get('stat') == 'ok'
            return self.logged_in
        except Exception as e:
            print(f"Erreur de connexion: {e}")
            return False
    
    def get_albums(self) -> List[Dict]:
        """Récupère tous les albums"""
        if not self.logged_in:
            if not self.login():
                return []
        
        try:
            url = f"{self.config['piwigo_url']}/ws.php?format=json"
            response = self.session.post(url, data={
                'method': 'pwg.categories.getList',
                'recursive': 'true'
            })
            result = response.json()
            if result.get('stat') == 'ok':
                return result.get('result', {}).get('categories', [])
            return []
        except Exception as e:
            print(f"Erreur récupération albums: {e}")
            return []
    
    def get_images_from_album(self, album_id: int) -> List[Dict]:
        """Récupère toutes les images d'un album"""
        if not self.logged_in:
            if not self.login():
                return []
        
        try:
            url = f"{self.config['piwigo_url']}/ws.php?format=json"
            response = self.session.post(url, data={
                'method': 'pwg.categories.getImages',
                'cat_id': album_id,
                'per_page': 1000
            })
            result = response.json()
            if result.get('stat') == 'ok':
                return result.get('result', {}).get('images', [])
            return []
        except Exception as e:
            print(f"Erreur récupération images: {e}")
            return []
    
    def extract_creator(self, description: str) -> Optional[str]:
        """Extrait le nom du créateur depuis la description (dans la balise <a>)"""
        if not description:
            return None
        
        # Recherche de "Créateur:" suivi d'une balise <a>
        match = re.search(r'Créateur\s*:\s*<a[^>]*>([^<]+)</a>', description, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Fallback: recherche sans balise HTML
        match = re.search(r'Créateur\s*:\s*([^\n<,;]+)', description, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def find_duplicates(self, images: List[Dict]) -> List[List[Dict]]:
        """Trouve les images avec le même créateur et le même titre"""
        # Grouper par (créateur, titre)
        groups = {}
        
        print(f"\n=== Analyse de {len(images)} images ===")
        
        for image in images:
            creator = self.extract_creator(image.get('comment', ''))
            title = image.get('name', '').strip()
            
            # Debug
            if creator:
                print(f"Image {image.get('id')}: '{title}' par '{creator}'")
            
            if creator and title:
                # Normalisation pour la comparaison (minuscules, espaces simplifiés)
                key = (
                    ' '.join(creator.lower().split()),
                    ' '.join(title.lower().split())
                )
                
                if key not in groups:
                    groups[key] = []
                groups[key].append(image)
        
        # Retourner seulement les groupes avec plus d'une image
        duplicates = [group for group in groups.values() if len(group) > 1]
        
        print(f"\n=== {len(duplicates)} groupes de doublons trouvés ===")
        for i, group in enumerate(duplicates):
            print(f"Groupe {i+1}: {len(group)} images - '{group[0].get('name')}' par '{self.extract_creator(group[0].get('comment', ''))}'")
        
        return duplicates
    
    def delete_image(self, image_id: int) -> bool:
        """Supprime une image de Piwigo"""
        if not self.logged_in:
            if not self.login():
                return False
        
        try:
            url = f"{self.config['piwigo_url']}/ws.php?format=json"
            response = self.session.post(url, data={
                'method': 'pwg.images.delete',
                'image_id': image_id,
                'pwg_token': self.get_token()
            })
            result = response.json()
            return result.get('stat') == 'ok'
        except Exception as e:
            print(f"Erreur suppression image: {e}")
            return False
    
    def get_token(self) -> str:
        """Récupère le token PWG pour les opérations sensibles"""
        try:
            url = f"{self.config['piwigo_url']}/ws.php?format=json"
            response = self.session.post(url, data={
                'method': 'pwg.session.getStatus'
            })
            result = response.json()
            return result.get('result', {}).get('pwg_token', '')
        except:
            return ''
    
    def add_operation(self, operation_type: str, data: dict):
        """Ajoute une opération au fichier de trace"""
        operation = {
            'timestamp': datetime.now().isoformat(),
            'type': operation_type,
            'data': data
        }
        self.trace['operations'].append(operation)
        self.save_trace()
    
    def mark_album_processed(self, album_id: int):
        """Marque un album comme traité"""
        if album_id not in self.trace['processed_albums']:
            self.trace['processed_albums'].append(album_id)
            self.save_trace()

# Instance globale
deduplicator = PiwigoDeduplicator()

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html', config=deduplicator.config)

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """Gestion de la configuration"""
    if request.method == 'POST':
        data = request.json
        deduplicator.save_config(data)
        return jsonify({'success': True})
    return jsonify(deduplicator.config)

@app.route('/api/login', methods=['POST'])
def login():
    """Test de connexion"""
    success = deduplicator.login()
    return jsonify({'success': success})

@app.route('/api/albums', methods=['GET'])
def get_albums():
    """Récupère la liste des albums"""
    albums = deduplicator.get_albums()
    
    # Filtrer les albums déjà traités si nécessaire
    if not deduplicator.config.get('reprocess_albums', False):
        processed = deduplicator.trace['processed_albums']
        albums = [a for a in albums if a['id'] not in processed]
    
    return jsonify(albums)

@app.route('/api/scan/<int:album_id>', methods=['GET'])
def scan_album(album_id):
    """Scanne un album pour trouver des doublons"""
    images = deduplicator.get_images_from_album(album_id)
    duplicates = deduplicator.find_duplicates(images)
    
    # Enregistrer les candidats trouvés
    if duplicates:
        deduplicator.add_operation('scan', {
            'album_id': album_id,
            'duplicates_found': len(duplicates),
            'total_images': sum(len(group) for group in duplicates)
        })
    
    return jsonify({
        'duplicates': duplicates,
        'album_id': album_id
    })

@app.route('/api/scan_all', methods=['GET'])
def scan_all_albums():
    """Retourne la liste des albums à traiter"""
    albums = deduplicator.get_albums()
    
    # Filtrer les albums déjà traités si nécessaire
    if not deduplicator.config.get('reprocess_albums', False):
        processed = deduplicator.trace['processed_albums']
        albums = [a for a in albums if a['id'] not in processed]
    
    # Retourner seulement la liste des albums, sans scanner
    return jsonify({
        'albums': albums,
        'total_albums': len(albums)
    })

@app.route('/api/delete', methods=['POST'])
def delete_images():
    """Supprime les images sélectionnées"""
    data = request.json
    image_ids = data.get('image_ids', [])
    album_id = data.get('album_id')
    kept_ids = data.get('kept_ids', [])
    
    results = []
    for image_id in image_ids:
        success = deduplicator.delete_image(image_id)
        results.append({
            'image_id': image_id,
            'success': success
        })
    
    # Enregistrer l'opération
    deduplicator.add_operation('delete', {
        'album_id': album_id,
        'deleted': [r for r in results if r['success']],
        'kept': kept_ids,
        'failed': [r for r in results if not r['success']]
    })
    
    return jsonify({'results': results})

@app.route('/api/mark_processed/<int:album_id>', methods=['POST'])
def mark_processed(album_id):
    """Marque un album comme traité"""
    deduplicator.mark_album_processed(album_id)
    return jsonify({'success': True})

@app.route('/api/trace', methods=['GET'])
def get_trace():
    """Récupère le fichier de trace"""
    return jsonify(deduplicator.trace)

@app.route('/api/reset_trace', methods=['POST'])
def reset_trace():
    """Réinitialise le fichier de trace"""
    deduplicator.trace = {
        'processed_albums': [],
        'operations': []
    }
    deduplicator.save_trace()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=7000)
