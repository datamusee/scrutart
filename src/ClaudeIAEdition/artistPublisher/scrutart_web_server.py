"""
Serveur Web Scrutart - API Bridge
Fait le lien entre l'interface web et les flows Prefect
"""

import os
import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string #, websocket
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests
from prefect.client.orchestration import PrefectClient
from prefect.client.schemas import FlowRun
import sqlite3


# Configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'scrutart-secret-key-2024')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Prefect
PREFECT_API_URL = os.getenv('PREFECT_API_URL', 'http://localhost:4200/api')
PREFECT_CLIENT = None

# Base de données locale pour le suivi
DB_PATH = Path('scrutart_tracking.db')


def init_database():
    """Initialise la base de données de suivi"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flow_runs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            qids TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS artist_cache (
            qid TEXT PRIMARY KEY,
            name TEXT,
            data TEXT,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def get_db_connection():
    """Obtient une connexion à la base de données"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


async def get_prefect_client():
    """Obtient un client Prefect async"""
    global PREFECT_CLIENT
    if PREFECT_CLIENT is None:
        PREFECT_CLIENT = PrefectClient(api=PREFECT_API_URL)
    return PREFECT_CLIENT


# Routes API

@app.route('/api/status')
def api_status():
    """Statut de l'API"""
    try:
        # Vérifier la connexion à Prefect
        response = requests.get(f"{PREFECT_API_URL}/health", timeout=5)
        prefect_status = response.status_code == 200
    except:
        prefect_status = False
    
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'prefect_connected': prefect_status,
        'database_connected': DB_PATH.exists()
    })


@app.route('/api/flows/process-artist', methods=['POST'])
async def process_single_artist():
    """Lance le traitement d'un artiste unique"""
    try:
        data = request.get_json()
        qid = data.get('qid')
        languages = data.get('languages', ['fr'])
        auto_publish = data.get('auto_publish', 'draft')
        
        if not qid:
            return jsonify({'error': 'QID requis'}), 400
        
        # Lancer le flow Prefect
        client = await get_prefect_client()
        
        flow_run = await client.create_flow_run_from_deployment(
            deployment_id="scrutart-single-artist-deployment",
            parameters={
                'qid': qid,
                'languages': languages,
                'auto_publish': auto_publish
            },
            name=f"Single Artist - {qid}"
        )
        
        # Enregistrer dans la base
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO flow_runs (id, name, type, qids, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (str(flow_run.id), f"Artist {qid}", "single", qid, "scheduled"))
        conn.commit()
        conn.close()
        
        # Émettre via WebSocket
        socketio.emit('flow_started', {
            'flow_run_id': str(flow_run.id),
            'type': 'single',
            'qid': qid
        })
        
        return jsonify({
            'success': True,
            'flow_run_id': str(flow_run.id),
            'message': f'Traitement lancé pour {qid}'
        })
        
    except Exception as e:
        logger.error(f"Erreur process_single_artist: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/flows/process-batch', methods=['POST'])
async def process_artist_batch():
    """Lance le traitement d'un lot d'artistes"""
    try:
        data = request.get_json()
        qids = data.get('qids', [])
        batch_name = data.get('batch_name', f'Batch {datetime.now().strftime("%Y%m%d_%H%M%S")}')
        batch_size = data.get('batch_size', 10)
        languages = data.get('languages', ['fr'])
        auto_publish = data.get('auto_publish', 'draft')
        
        if not qids:
            return jsonify({'error': 'Liste de QID requise'}), 400
        
        # Lancer le flow Prefect batch
        client = await get_prefect_client()
        
        flow_run = await client.create_flow_run_from_deployment(
            deployment_id="scrutart-batch-processing-deployment",
            parameters={
                'qids': qids,
                'batch_name': batch_name,
                'batch_size': batch_size,
                'languages': languages,
                'auto_publish': auto_publish
            },
            name=f"Batch - {batch_name}"
        )
        
        # Enregistrer dans la base
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO flow_runs (id, name, type, qids, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (str(flow_run.id), batch_name, "batch", json.dumps(qids), "scheduled"))
        conn.commit()
        conn.close()
        
        # Émettre via WebSocket
        socketio.emit('flow_started', {
            'flow_run_id': str(flow_run.id),
            'type': 'batch',
            'batch_name': batch_name,
            'qid_count': len(qids)
        })
        
        return jsonify({
            'success': True,
            'flow_run_id': str(flow_run.id),
            'message': f'Traitement par lot lancé pour {len(qids)} artistes'
        })
        
    except Exception as e:
        logger.error(f"Erreur process_artist_batch: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/flows/<flow_run_id>/status')
async def get_flow_status(flow_run_id):
    """Récupère le statut d'un flow"""
    try:
        client = await get_prefect_client()
        flow_run = await client.read_flow_run(flow_run_id)
        
        if not flow_run:
            return jsonify({'error': 'Flow run non trouvé'}), 404
        
        # Mettre à jour la base de données
        conn = get_db_connection()
        conn.execute('''
            UPDATE flow_runs 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (flow_run.state.type.value.lower(), flow_run_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'id': str(flow_run.id),
            'name': flow_run.name,
            'state': flow_run.state.type.value.lower(),
            'created_at': flow_run.created.isoformat(),
            'updated_at': flow_run.updated.isoformat() if flow_run.updated else None,
            'duration': (flow_run.total_run_time.total_seconds() if flow_run.total_run_time else 0)
        })
        
    except Exception as e:
        logger.error(f"Erreur get_flow_status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/flows/active')
def get_active_flows():
    """Récupère tous les flows actifs"""
    try:
        conn = get_db_connection()
        flows = conn.execute('''
            SELECT * FROM flow_runs 
            WHERE status IN ('scheduled', 'running', 'pending')
            ORDER BY created_at DESC
        ''').fetchall()
        conn.close()
        
        result = []
        for flow in flows:
            qids = json.loads(flow['qids']) if flow['type'] == 'batch' else [flow['qids']]
            result.append({
                'id': flow['id'],
                'name': flow['name'],
                'type': flow['type'],
                'qids': qids,
                'status': flow['status'],
                'created_at': flow['created_at'],
                'updated_at': flow['updated_at']
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur get_active_flows: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/flows/history')
def get_flow_history():
    """Récupère l'historique des flows"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        conn = get_db_connection()
        flows = conn.execute('''
            SELECT * FROM flow_runs 
            ORDER BY updated_at DESC 
            LIMIT ?
        ''', (limit,)).fetchall()
        conn.close()
        
        result = []
        for flow in flows:
            qids = json.loads(flow['qids']) if flow['type'] == 'batch' else [flow['qids']]
            result.append({
                'id': flow['id'],
                'name': flow['name'],
                'type': flow['type'],
                'qids': qids,
                'status': flow['status'],
                'created_at': flow['created_at'],
                'updated_at': flow['updated_at'],
                'result': json.loads(flow['result']) if flow['result'] else None
            })
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Erreur get_flow_history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/flows/<flow_run_id>/cancel', methods=['POST'])
async def cancel_flow(flow_run_id):
    """Annule un flow"""
    try:
        client = await get_prefect_client()
        await client.cancel_flow_run(flow_run_id)
        
        # Mettre à jour la base
        conn = get_db_connection()
        conn.execute('''
            UPDATE flow_runs 
            SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (flow_run_id,))
        conn.commit()
        conn.close()
        
        # Émettre via WebSocket
        socketio.emit('flow_cancelled', {'flow_run_id': flow_run_id})
        
        return jsonify({'success': True, 'message': 'Flow annulé'})
        
    except Exception as e:
        logger.error(f"Erreur cancel_flow: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/artist/<qid>/preview')
def preview_artist(qid):
    """Aperçu des informations d'un artiste"""
    try:
        # Vérifier le cache d'abord
        conn = get_db_connection()
        cached = conn.execute('''
            SELECT data FROM artist_cache 
            WHERE qid = ? AND datetime(cached_at) > datetime('now', '-1 hour')
        ''', (qid,)).fetchone()
        
        if cached:
            conn.close()
            return jsonify(json.loads(cached['data']))
        
        # Requête vers Wikidata
        sparql_query = f"""
        SELECT ?artistLabel ?description ?birthYear ?deathYear ?nationalityLabel ?movementLabel ?image WHERE {{
          wd:{qid} rdfs:label ?artistLabel ;
                   schema:description ?description .
          FILTER(LANG(?artistLabel) = "fr" && LANG(?description) = "fr")
          
          OPTIONAL {{
            wd:{qid} wdt:P569 ?birth .
            BIND(YEAR(?birth) AS ?birthYear)
          }}
          
          OPTIONAL {{
            wd:{qid} wdt:P570 ?death .
            BIND(YEAR(?death) AS ?deathYear)
          }}
          
          OPTIONAL {{
            wd:{qid} wdt:P27 ?nationality .
            ?nationality rdfs:label ?nationalityLabel .
            FILTER(LANG(?nationalityLabel) = "fr")
          }}
          
          OPTIONAL {{
            wd:{qid} wdt:P135 ?movement .
            ?movement rdfs:label ?movementLabel .
            FILTER(LANG(?movementLabel) = "fr")
          }}
          
          OPTIONAL {{
            wd:{qid} wdt:P18 ?image .
          }}
        }}
        LIMIT 1
        """
        
        response = requests.post(
            'https://query.wikidata.org/sparql',
            data={
                'query': sparql_query,
                'format': 'json'
            },
            headers={'User-Agent': 'Scrutart/1.0'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            bindings = data['results']['bindings']
            
            if bindings:
                binding = bindings[0]
                artist_data = {
                    'qid': qid,
                    'name': binding.get('artistLabel', {}).get('value', f'Artiste {qid}'),
                    'description': binding.get('description', {}).get('value', ''),
                    'birth_year': binding.get('birthYear', {}).get('value'),
                    'death_year': binding.get('deathYear', {}).get('value'),
                    'nationality': binding.get('nationalityLabel', {}).get('value'),
                    'movement': binding.get('movementLabel', {}).get('value'),
                    'image': binding.get('image', {}).get('value')
                }
                
                # Mettre en cache
                conn.execute('''
                    INSERT OR REPLACE INTO artist_cache (qid, name, data)
                    VALUES (?, ?, ?)
                ''', (qid, artist_data['name'], json.dumps(artist_data)))
                conn.commit()
                conn.close()
                
                return jsonify(artist_data)
            else:
                conn.close()
                return jsonify({'error': 'Artiste non trouvé'}), 404
        else:
            conn.close()
            return jsonify({'error': 'Erreur Wikidata'}), 500
            
    except Exception as e:
        logger.error(f"Erreur preview_artist: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/dashboard')
def dashboard():
    with open("scrutart_web_interface.html", encoding="utf-8") as fh:
        page = fh.read()
        return page
    return """<h1>Erreur d'accès au dashboard</h1>"""

@app.route('/')
def index():
    """Page d'accueil avec l'interface"""
    # Dans un environnement de production, vous devriez servir le fichier HTML séparément
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Scrutart Dashboard</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <div style="text-align: center; padding: 50px;">
            <h1>🎨 Scrutart Automation Dashboard</h1>
            <p>Interface de gestion automatisée des contenus artistiques</p>
            <p><a href="/dashboard">Accéder au tableau de bord</a></p>
            <p><a href="/api/status">Statut de l'API</a></p>
        </div>
    </body>
    </html>
    """

@app.route('/api/artist/<qid>/artworks/count')
def get_artworks_count(qid):
    """Compte les œuvres d'un artiste"""
    try:
        sparql_query = f"""
        SELECT (COUNT(?artwork) AS ?count) WHERE {{
          ?artwork wdt:P170 wd:{qid} ;
                   wdt:P31 wd:Q3305213 .
        }}
        """
        
        response = requests.post(
            'https://query.wikidata.org/sparql',
            data={
                'query': sparql_query,
                'format': 'json'
            },
            headers={'User-Agent': 'Scrutart/1.0'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            bindings = data['results']['bindings']
            count = int(bindings[0]['count']['value']) if bindings else 0
            return jsonify({'qid': qid, 'artworks_count': count})
        else:
            return jsonify({'error': 'Erreur Wikidata'}), 500
            
    except Exception as e:
        logger.error(f"Erreur get_artworks_count: {e}")
        return jsonify({'error': str(e)}), 500


# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Connexion WebSocket"""
    logger.info('Client WebSocket connecté')
    emit('connected', {'message': 'Connecté au serveur Scrutart'})


@socketio.on('disconnect')
def handle_disconnect():
    """Déconnexion WebSocket"""
    logger.info('Client WebSocket déconnecté')


@socketio.on('subscribe_flow')
def handle_subscribe_flow(data):
    """Abonnement aux mises à jour d'un flow"""
    flow_run_id = data.get('flow_run_id')
    if flow_run_id:
        # Ajouter à une room pour recevoir les mises à jour
        join_room(flow_run_id)
        emit('subscribed', {'flow_run_id': flow_run_id})


# Tâche de fond pour surveiller les flows Prefect
async def monitor_flows():
    """Surveille les flows Prefect et émet les mises à jour"""
    while True:
        try:
            # Récupérer les flows actifs de la base
            conn = get_db_connection()
            active_flows = conn.execute('''
                SELECT id FROM flow_runs 
                WHERE status IN ('scheduled', 'running', 'pending')
            ''').fetchall()
            conn.close()
            
            if active_flows:
                client = await get_prefect_client()
                
                for flow_row in active_flows:
                    flow_id = flow_row['id']
                    try:
                        flow_run = await client.read_flow_run(flow_id)
                        if flow_run:
                            current_state = flow_run.state.type.value.lower()
                            
                            # Mettre à jour la base
                            conn = get_db_connection()
                            old_status = conn.execute(
                                'SELECT status FROM flow_runs WHERE id = ?', 
                                (flow_id,)
                            ).fetchone()
                            
                            if old_status and old_status['status'] != current_state:
                                conn.execute('''
                                    UPDATE flow_runs 
                                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (current_state, flow_id))
                                conn.commit()
                                
                                # Émettre la mise à jour
                                socketio.emit('flow_status_update', {
                                    'flow_run_id': flow_id,
                                    'status': current_state,
                                    'timestamp': datetime.now().isoformat()
                                })
                            
                            conn.close()
                            
                    except Exception as e:
                        logger.error(f"Erreur monitoring flow {flow_id}: {e}")
            
            # Attendre 10 secondes avant la prochaine vérification
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.error(f"Erreur monitor_flows: {e}")
            await asyncio.sleep(30)


# Commandes CLI
@app.cli.command()
def init_db():
    """Initialise la base de données"""
    init_database()
    print("Base de données initialisée")


@app.cli.command()
def create_deployments():
    """Crée les déploiements Prefect"""
    import subprocess
    import sys
    
    try:
        # Deployer les flows
        result = subprocess.run([
            sys.executable, '-m', 'prefect', 'deployment', 'apply', 
            'scrutart_flows.py:process_artist_complete-deployment.yaml'
        ], check=True, capture_output=True, text=True)
        
        print("Déploiements créés avec succès")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Erreur création déploiements: {e}")
        print(e.stderr)


if __name__ == '__main__':
    # Initialiser la base de données
    init_database()
    
    # Lancer la surveillance des flows en arrière-plan
    import threading
    def run_monitor():
        asyncio.run(monitor_flows())
    
    monitor_thread = threading.Thread(target=run_monitor, daemon=True)
    monitor_thread.start()
    
    # Lancer l'application
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
