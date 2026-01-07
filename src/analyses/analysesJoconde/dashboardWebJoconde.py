"""
Dashboard Flask pour l'analyse des collections Joconde
Installation requise: pip install flask ijson

Instructions:
1. Téléchargez le fichier JSON depuis: https://www.data.gouv.fr/api/1/datasets/r/7706931a-c76f-4018-9c29-dd3f42b58c53
2. Placez le fichier dans le même répertoire que ce script et nommez-le 'joconde_data.json'
3. Lancez avec: python app.py
4. Ouvrez votre navigateur sur: http://localhost:5000
"""

from flask import Flask, render_template_string, jsonify, request
import ijson
import json
from collections import Counter, defaultdict
from datetime import datetime
import os
import threading
import time

app = Flask(__name__)

# Configuration
DATA_FILE = 'D:/wamp64/www/givingsense.eu/datamusee/data/joconde/base-joconde-extrait.json'
CACHE_FILE = 'joconde_cache.json'
SAMPLE_SIZE = 10000

# Variables globales pour le suivi des traitements asynchrones
processing_status = {
    'total_count': {'status': 'idle', 'progress': 0, 'message': ''},
    'temporal': {'status': 'idle', 'progress': 0, 'message': ''},
    'geographic': {'status': 'idle', 'progress': 0, 'message': ''},
}

class DataAnalyzer:
    """Classe pour analyser le fichier JSON de manière efficiente"""

    def __init__(self, filepath, cache_file=None):
        self.filepath = filepath
        self.cache_file = cache_file or CACHE_FILE
        self.cache = self.load_cache()

        # Vérifier l'existence du fichier
        if not os.path.exists(filepath):
            print(f"⚠️  ATTENTION: Le fichier {filepath} n'existe pas!")
            print(f"Téléchargez-le depuis: https://www.data.gouv.fr/api/1/datasets/r/7706931a-c76f-4018-9c29-dd3f42b58c53")

    def load_cache(self):
        """Charge le cache depuis le fichier s'il existe"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    print(f"📦 Cache chargé depuis {self.cache_file}")
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Erreur lors du chargement du cache: {e}")
                return {}
        return {}

    def save_cache(self):
        """Sauvegarde le cache dans un fichier"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
            print(f"💾 Cache sauvegardé dans {self.cache_file}")
        except Exception as e:
            print(f"⚠️  Erreur lors de la sauvegarde du cache: {e}")

    def file_exists(self):
        return os.path.exists(self.filepath)

    def count_total_objects(self, async_mode=False):
        """Compte le nombre total d'objets (avec cache persistant)"""
        if 'total_count' in self.cache:
            print(f"✅ Utilisation du cache pour total_count: {self.cache['total_count']}")
            processing_status['total_count'] = {'status': 'completed', 'progress': self.cache['total_count'], 'message': f"Comptage terminé: {self.cache['total_count']:,} objets"}
            return self.cache['total_count']

        if not self.file_exists():
            return 0

        # Vérifier si un traitement est déjà en cours
        if async_mode and processing_status['total_count']['status'] == 'processing':
            return None  # Traitement déjà en cours

        if async_mode:
            # Lancer le comptage en arrière-plan
            thread = threading.Thread(target=self._count_objects_async)
            thread.daemon = True
            thread.start()
            return None  # Indique que le traitement est en cours
        else:
            return self._count_objects_sync()

    def _count_objects_sync(self):
        """Comptage synchrone"""
        print("⏳ Comptage des objets en cours (peut prendre quelques minutes)...")
        count = 0
        try:
            with open(self.filepath, 'rb') as f:
                parser = ijson.items(f, 'item')
                for _ in parser:
                    count += 1
                    if count % 50000 == 0:
                        print(f"   {count:,} objets comptés...")
        except Exception as e:
            print(f"Erreur lors du comptage: {e}")
            return 0

        self.cache['total_count'] = count
        self.save_cache()
        print(f"✅ Comptage terminé: {count:,} objets")
        return count

    def _count_objects_async(self):
        """Comptage asynchrone avec suivi de progression"""
        global processing_status
        processing_status['total_count'] = {'status': 'processing', 'progress': 0, 'message': 'Démarrage du comptage...'}

        count = 0
        start_time = time.time()
        try:
            with open(self.filepath, 'rb') as f:
                parser = ijson.items(f, 'item')
                for _ in parser:
                    count += 1
                    if count % 10000 == 0:
                        elapsed = time.time() - start_time
                        rate = count / elapsed if elapsed > 0 else 0
                        processing_status['total_count']['progress'] = count
                        processing_status['total_count']['message'] = f'{count:,} objets comptés ({rate:.0f} obj/s)...'
                        print(f"   {count:,} objets comptés...")
        except Exception as e:
            error_msg = f"Erreur: {str(e)}"
            print(f"❌ {error_msg}")
            processing_status['total_count'] = {'status': 'error', 'progress': 0, 'message': error_msg}
            return

        # Sauvegarder dans le cache
        self.cache['total_count'] = count
        self.save_cache()

        elapsed = time.time() - start_time
        success_msg = f'Comptage terminé: {count:,} objets en {elapsed:.1f}s'
        print(f"✅ {success_msg}")
        processing_status['total_count'] = {'status': 'completed', 'progress': count, 'message': success_msg}

    def get_sample_data(self, limit=100, offset=0):
        """Récupère un échantillon de données"""
        if not self.file_exists():
            return []

        data = []
        try:
            with open(self.filepath, 'rb') as f:
                parser = ijson.items(f, 'item')
                for i, obj in enumerate(parser):
                    if i < offset:
                        continue
                    if len(data) >= limit:
                        break
                    data.append(obj)
        except Exception as e:
            print(f"Erreur lors de la lecture: {e}")

        return data

    def analyze_field(self, field_name, sample_size=SAMPLE_SIZE):
        """Analyse un champ spécifique"""
        cache_key = f'field_{field_name}_{sample_size}'
        if cache_key in self.cache:
            return self.cache[cache_key]

        if not self.file_exists():
            return {'error': 'Fichier non trouvé'}

        counter = Counter()
        total = 0
        present = 0

        try:
            with open(self.filepath, 'rb') as f:
                parser = ijson.items(f, 'item')
                for i, obj in enumerate(parser):
                    if i >= sample_size:
                        break
                    total += 1
                    value = obj.get(field_name)
                    if value and value not in [None, '', []]:
                        present += 1
                        if isinstance(value, list):
                            for v in value:
                                counter[str(v)[:100]] += 1
                        else:
                            counter[str(value)[:100]] += 1
        except Exception as e:
            print(f"Erreur analyse champ {field_name}: {e}")
            return {'error': str(e)}

        result = {
            'total_analyzed': total,
            'present_count': present,
            'presence_rate': round(present / total * 100, 2) if total > 0 else 0,
            'top_values': counter.most_common(20),
            'unique_values': len(counter)
        }

        self.cache[cache_key] = result
        return result

    def get_temporal_distribution(self, sample_size=SAMPLE_SIZE):
        """Analyse la distribution temporelle (avec cache persistant)"""
        cache_key = f'temporal_distribution_{sample_size}'
        if cache_key in self.cache:
            print(f"✅ Utilisation du cache pour temporal_distribution")
            return self.cache[cache_key]

        if not self.file_exists():
            return {}

        print("⏳ Analyse temporelle en cours...")
        years = []
        try:
            with open(self.filepath, 'rb') as f:
                parser = ijson.items(f, 'item')
                for i, obj in enumerate(parser):
                    if i >= sample_size:
                        break
                    date_str = obj.get('millesime_de_creation', '')
                    if date_str:
                        year = ''.join(filter(str.isdigit, str(date_str).split('-')[0]))[:4]
                        if len(year) == 4 and year.isdigit():
                            years.append(int(year))
        except Exception as e:
            print(f"Erreur distribution temporelle: {e}")
            return {}

        if not years:
            return {}

        decade_counter = Counter()
        for year in years:
            if 1000 <= year <= 2100:
                decade = (year // 10) * 10
                decade_counter[decade] += 1

        result = {
            'by_decade': sorted(decade_counter.items()),
            'min_year': min(years),
            'max_year': max(years),
            'total': len(years)
        }

        self.cache[cache_key] = result
        self.save_cache()
        print("✅ Analyse temporelle terminée")
        return result

    def get_geographic_distribution(self, sample_size=SAMPLE_SIZE):
        """Analyse la distribution géographique (avec cache persistant)"""
        cache_key = f'geographic_distribution_{sample_size}'
        if cache_key in self.cache:
            print(f"✅ Utilisation du cache pour geographic_distribution")
            return self.cache[cache_key]

        if not self.file_exists():
            return {}

        print("⏳ Analyse géographique en cours...")
        regions = Counter()
        cities = Counter()

        try:
            with open(self.filepath, 'rb') as f:
                parser = ijson.items(f, 'item')
                for i, obj in enumerate(parser):
                    if i >= sample_size:
                        break

                    region = obj.get('region')
                    if region:
                        regions[region] += 1

                    city = obj.get('ville')
                    if city:
                        cities[city] += 1
        except Exception as e:
            print(f"Erreur distribution géographique: {e}")
            return {}

        result = {
            'regions': regions.most_common(15),
            'cities': cities.most_common(20)
        }

        self.cache[cache_key] = result
        self.save_cache()
        print("✅ Analyse géographique terminée")
        return result

    def search_objects(self, query, field=None, limit=50):
        """Recherche des objets"""
        if not self.file_exists():
            return []

        results = []
        query_lower = query.lower()

        try:
            with open(self.filepath, 'rb') as f:
                parser = ijson.items(f, 'item')
                for obj in parser:
                    if len(results) >= limit:
                        break

                    match = False
                    if field and field in obj:
                        value = str(obj.get(field, '')).lower()
                        if query_lower in value:
                            match = True
                    elif not field:
                        for key, value in obj.items():
                            if isinstance(value, (str, int, float)):
                                if query_lower in str(value).lower():
                                    match = True
                                    break

                    if match:
                        results.append(obj)
        except Exception as e:
            print(f"Erreur recherche: {e}")

        return results

# Instance globale
analyzer = DataAnalyzer(DATA_FILE)

@app.route('/')
def index():
    """Page principale"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats/overview')
def stats_overview():
    """Statistiques générales"""
    try:
        if not analyzer.file_exists():
            return jsonify({
                'success': False,
                'error': 'Fichier de données non trouvé. Téléchargez-le depuis data.gouv.fr'
            }), 404

        # Vérifier d'abord si le comptage est dans le cache
        if 'total_count' in analyzer.cache:
            total = analyzer.cache['total_count']
        else:
            # Lancer le comptage asynchrone
            total = analyzer.count_total_objects(async_mode=True)

        # Si le traitement est en cours
        if total is None:
            status = processing_status['total_count']
            return jsonify({
                'success': True,
                'processing': True,
                'status': status,
                'total_objects': status.get('progress', 0)
            })

        # Traitement terminé, récupérer les autres stats
        sample = analyzer.get_sample_data(limit=100)

        field_presence = {}
        for obj in sample:
            for key in obj.keys():
                if key not in field_presence:
                    field_presence[key] = 0
                if obj[key] not in [None, '', []]:
                    field_presence[key] += 1

        top_fields = sorted(
            [(k, round(v/len(sample)*100, 1)) for k, v in field_presence.items()],
            key=lambda x: x[1],
            reverse=True
        )[:15]

        return jsonify({
            'success': True,
            'processing': False,
            'total_objects': total,
            'sample_size': len(sample),
            'top_fields': top_fields,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        print(f"❌ Erreur dans stats_overview: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status/<task_name>')
def get_status(task_name):
    """Récupère le statut d'un traitement asynchrone"""
    if task_name in processing_status:
        # Si le traitement est terminé, récupérer les données du cache
        if processing_status[task_name]['status'] == 'completed':
            if task_name == 'total_count' and 'total_count' in analyzer.cache:
                return jsonify({
                    'success': True,
                    'status': processing_status[task_name],
                    'result': analyzer.cache['total_count']
                })

        return jsonify({
            'success': True,
            'status': processing_status[task_name]
        })
    return jsonify({'success': False, 'error': 'Task not found'}), 404

@app.route('/api/stats/field/<field_name>')
def stats_field(field_name):
    """Statistiques pour un champ spécifique"""
    try:
        result = analyzer.analyze_field(field_name)
        return jsonify({
            'success': True,
            'field': field_name,
            'stats': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats/temporal')
def stats_temporal():
    """Distribution temporelle"""
    try:
        result = analyzer.get_temporal_distribution()
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats/geographic')
def stats_geographic():
    """Distribution géographique"""
    try:
        result = analyzer.get_geographic_distribution()
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/search')
def search():
    """Recherche dans les données"""
    try:
        query = request.args.get('q', '')
        field = request.args.get('field', None)
        limit = int(request.args.get('limit', 50))

        if not query:
            return jsonify({'success': False, 'error': 'Query parameter required'}), 400

        results = analyzer.search_objects(query, field, limit)

        return jsonify({
            'success': True,
            'query': query,
            'field': field,
            'count': len(results),
            'results': results
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/objects')
def get_objects():
    """Récupère une liste d'objets avec pagination"""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        objects = analyzer.get_sample_data(limit=limit, offset=offset)

        return jsonify({
            'success': True,
            'count': len(objects),
            'offset': offset,
            'limit': limit,
            'objects': objects
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Template HTML complet
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Joconde - Analyse des Collections</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container { max-width: 1400px; margin: 0 auto; }
        
        header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        
        h1 { color: #333; font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { color: #666; font-size: 1.1em; }
        
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        
        .tab {
            padding: 12px 24px;
            background: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .tab:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }
        .tab.active { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .card h2 { color: #333; margin-bottom: 15px; font-size: 1.5em; }
        .stat-value { font-size: 2.5em; font-weight: bold; color: #667eea; margin: 10px 0; }
        .stat-label { color: #666; font-size: 0.9em; }
        
        .loading { text-align: center; padding: 40px; color: #666; }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .search-box { display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap; }
        
        input[type="text"], select {
            padding: 12px 20px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 1em;
            flex: 1;
            min-width: 200px;
        }
        
        button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s;
        }
        
        button:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.2); }
        
        .results { max-height: 600px; overflow-y: auto; }
        
        .result-item {
            background: #f8f9fa;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .result-item h3 { color: #333; margin-bottom: 8px; font-size: 1.1em; }
        .result-item p { color: #666; font-size: 0.9em; margin: 5px 0; }
        
        .chart-container { position: relative; height: 400px; margin-top: 20px; }
        
        .field-list { list-style: none; max-height: 600px; overflow-y: auto; }
        
        .field-item {
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .field-item:hover { background: #e9ecef; transform: translateX(5px); }
        .field-item.selected { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        
        .field-stats { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; }
        .value-list { display: grid; gap: 10px; margin-top: 15px; }
        
        .value-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 12px;
            background: white;
            border-radius: 5px;
            font-size: 0.9em;
        }
        
        .value-name {
            color: #333;
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .value-count { color: #667eea; font-weight: bold; margin-left: 10px; }
        
        .error-message {
            background: #ffebee;
            color: #c62828;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #c62828;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
            margin: 15px 0;
            position: relative;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
        }
        
        .progress-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #333;
            font-weight: bold;
            font-size: 0.9em;
            z-index: 1;
        }
        
        .processing-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px;
            background: #e3f2fd;
            border-radius: 8px;
            border-left: 4px solid #2196f3;
            margin: 10px 0;
        }
        
        .processing-indicator .spinner {
            width: 20px;
            height: 20px;
            margin: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Dashboard Joconde</h1>
            <p class="subtitle">Analyse des collections des musées de France</p>
        </header>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('overview')">Vue d'ensemble</button>
            <button class="tab" onclick="switchTab('temporal')">Analyse temporelle</button>
            <button class="tab" onclick="switchTab('geographic')">Géographie</button>
            <button class="tab" onclick="switchTab('fields')">Analyse par champs</button>
            <button class="tab" onclick="switchTab('search')">Recherche</button>
        </div>
        
        <div id="overview" class="tab-content active">
            <div class="grid">
                <div class="card">
                    <h2>📦 Total d'objets</h2>
                    <div class="stat-value" id="totalObjects">-</div>
                    <div class="stat-label">objets dans la base</div>
                </div>
                
                <div class="card">
                    <h2>📋 Champs disponibles</h2>
                    <div class="stat-value" id="totalFields">-</div>
                    <div class="stat-label">champs descriptifs</div>
                </div>
                
                <div class="card">
                    <h2>📅 Dernière analyse</h2>
                    <div class="stat-value" style="font-size: 1.5em;" id="lastUpdate">-</div>
                    <div class="stat-label">horodatage</div>
                </div>
            </div>
            
            <div class="card">
                <h2>🎯 Champs les plus renseignés</h2>
                <div class="chart-container">
                    <canvas id="fieldsChart"></canvas>
                </div>
            </div>
        </div>
        
        <div id="temporal" class="tab-content">
            <div class="card">
                <h2>📅 Distribution temporelle des créations</h2>
                <div id="temporalLoading" class="loading">
                    <div class="spinner"></div>
                    <p>Chargement des données temporelles...</p>
                </div>
                <div class="chart-container" id="temporalChart" style="display:none;">
                    <canvas id="timelineChart"></canvas>
                </div>
            </div>
        </div>
        
        <div id="geographic" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h2>🗺️ Par région</h2>
                    <div id="regionLoading" class="loading"><div class="spinner"></div></div>
                    <div class="chart-container" id="regionChart" style="display:none;">
                        <canvas id="regionCanvas"></canvas>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🏛️ Par ville</h2>
                    <div id="cityLoading" class="loading"><div class="spinner"></div></div>
                    <div class="chart-container" id="cityChart" style="display:none;">
                        <canvas id="cityCanvas"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="fields" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h2>📝 Champs principaux</h2>
                    <ul class="field-list" id="fieldList"></ul>
                </div>
                
                <div class="card" style="grid-column: span 2;">
                    <h2>📊 Statistiques du champ sélectionné</h2>
                    <div id="fieldStatsContent">
                        <p style="color: #666; padding: 20px; text-align: center;">
                            Sélectionnez un champ dans la liste à gauche
                        </p>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="search" class="tab-content">
            <div class="card">
                <h2>🔍 Recherche dans les collections</h2>
                <div class="search-box">
                    <input type="text" id="searchQuery" placeholder="Entrez votre recherche..." onkeypress="if(event.key==='Enter') performSearch()">
                    <select id="searchField">
                        <option value="">Tous les champs</option>
                        <option value="titre">Titre</option>
                        <option value="auteur">Auteur</option>
                        <option value="description">Description</option>
                        <option value="domaine">Domaine</option>
                        <option value="localisation">Localisation</option>
                        <option value="ville">Ville</option>
                        <option value="region">Région</option>
                    </select>
                    <button onclick="performSearch()">Rechercher</button>
                </div>
                <div id="searchResults"></div>
            </div>
        </div>
    </div>
    
    <script>
        let charts = {};
        
        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tabName).classList.add('active');
            
            if (tabName === 'temporal' && !charts.timeline) {
                loadTemporalData();
            } else if (tabName === 'geographic' && !charts.region) {
                loadGeographicData();
            } else if (tabName === 'fields' && !document.getElementById('fieldList').children.length) {
                loadFieldsList();
            }
        }
        
        async function loadOverview() {
            try {
                const response = await fetch('/api/stats/overview');
                const data = await response.json();
                
                if (!data.success) {
                    document.getElementById('overview').innerHTML = `<div class="card"><div class="error-message"><strong>Erreur:</strong> ${data.error}</div></div>`;
                    return;
                }
                
                // Si le traitement est en cours
                if (data.processing) {
                    const status = data.status;
                    const totalDiv = document.getElementById('totalObjects');
                    
                    if (status.status === 'processing') {
                        totalDiv.innerHTML = `
                            <div class="processing-indicator">
                                <div class="spinner"></div>
                                <div>
                                    <div><strong>Traitement en cours...</strong></div>
                                    <div style="font-size: 0.8em; margin-top: 5px;">${status.message}</div>
                                </div>
                            </div>
                        `;
                        
                        // Recharger après 2 secondes
                        setTimeout(loadOverview, 2000);
                        return;
                    }
                }
                
                document.getElementById('totalObjects').textContent = data.total_objects.toLocaleString('fr-FR');
                document.getElementById('totalFields').textContent = data.top_fields.length;
                document.getElementById('lastUpdate').textContent = new Date(data.timestamp).toLocaleString('fr-FR', {hour: '2-digit', minute: '2-digit'});
                
                const ctx = document.getElementById('fieldsChart').getContext('2d');
                if (charts.fields) {
                    charts.fields.destroy();
                }
                charts.fields = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.top_fields.map(f => f[0]),
                        datasets: [{
                            label: 'Taux de remplissage (%)',
                            data: data.top_fields.map(f => f[1]),
                            backgroundColor: 'rgba(102, 126, 234, 0.6)',
                            borderColor: 'rgba(102, 126, 234, 1)',
                            borderWidth: 2
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: { x: { beginAtZero: true, max: 100 } }
                    }
                });
            } catch (error) {
                console.error('Erreur:', error);
                document.getElementById('overview').innerHTML = `<div class="card"><div class="error-message">Impossible de charger les données</div></div>`;
            }
        }
        
        async function loadTemporalData() {
            try {
                const response = await fetch('/api/stats/temporal');
                const data = await response.json();
                
                if (data.success && data.data.by_decade) {
                    document.getElementById('temporalLoading').style.display = 'none';
                    document.getElementById('temporalChart').style.display = 'block';
                    
                    const ctx = document.getElementById('timelineChart').getContext('2d');
                    charts.timeline = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: data.data.by_decade.map(d => d[0] + 's'),
                            datasets: [{
                                label: 'Nombre d objets créés',
                                data: data.data.by_decade.map(d => d[1]),
                                backgroundColor: 'rgba(118, 75, 162, 0.2)',
                                borderColor: 'rgba(118, 75, 162, 1)',
                                borderWidth: 3,
                                fill: true,
                                tension: 0.4
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: { y: { beginAtZero: true } }
                        }
                    });
                }
            } catch (error) {
                console.error('Erreur:', error);
            }
        }
        
        async function loadGeographicData() {
            try {
                const response = await fetch('/api/stats/geographic');
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('regionLoading').style.display = 'none';
                    document.getElementById('regionChart').style.display = 'block';
                    
                    const ctxRegion = document.getElementById('regionCanvas').getContext('2d');
                    charts.region = new Chart(ctxRegion, {
                        type: 'pie',
                        data: {
                            labels: data.data.regions.map(r => r[0]),
                            datasets: [{
                                data: data.data.regions.map(r => r[1]),
                                backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#a8edea', '#fed6e3', '#c471ed', '#12c2e9', '#f64f59', '#c3cfe2', '#8e2de2']
                            }]
                        },
                        options: { responsive: true, maintainAspectRatio: false }
                    });
                    
                    document.getElementById('cityLoading').style.display = 'none';
                    document.getElementById('cityChart').style.display = 'block';
                    
                    const ctxCity = document.getElementById('cityCanvas').getContext('2d');
                    charts.city = new Chart(ctxCity, {
                        type: 'bar',
                        data: {
                            labels: data.data.cities.map(c => c[0]),
                            datasets: [{
                                label: 'Nombre d objets',
                                data: data.data.cities.map(c => c[1]),
                                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                                borderColor: 'rgba(102, 126, 234, 1)',
                                borderWidth: 2
                            }]
                        },
                        options: {
                            indexAxis: 'y',
                            responsive: true,
                            maintainAspectRatio: false
                        }
                    });
                }
            } catch (error) {
                console.error('Erreur:', error);
            }
        }
        
        function loadFieldsList() {
            const fields = ['titre', 'auteur', 'domaine', 'localisation', 'ville', 'region', 'denomination', 'description', 'materiaux_techniques', 'periode_de_creation', 'millesime_de_creation', 'sujet_represente', 'ecole_pays', 'inscription', 'mesures', 'ancienne_appartenance', 'date_d_acquisition'];
            
            const list = document.getElementById('fieldList');
            fields.forEach(field => {
                const li = document.createElement('li');
                li.className = 'field-item';
                li.textContent = field;
                li.onclick = () => analyzeField(field, li);
                list.appendChild(li);
            });
        }
        
        async function analyzeField(fieldName, element) {
            document.querySelectorAll('.field-item').forEach(item => item.classList.remove('selected'));
            element.classList.add('selected');
            
            const content = document.getElementById('fieldStatsContent');
            content.innerHTML = '<div class="loading"><div class="spinner"></div><p>Analyse en cours...</p></div>';
            
            try {
                const response = await fetch(`/api/stats/field/${fieldName}`);
                const data = await response.json();
                
                if (data.success && data.stats) {
                    const stats = data.stats;
                    let html = `
                        <div class="field-stats">
                            <h3>${fieldName}</h3>
                            <p><strong>Objets analysés:</strong> ${stats.total_analyzed.toLocaleString('fr-FR')}</p>
                            <p><strong>Présent:</strong> ${stats.present_count.toLocaleString('fr-FR')} (${stats.presence_rate}%)</p>
                            <p><strong>Valeurs uniques:</strong> ${stats.unique_values.toLocaleString('fr-FR')}</p>
                            <h4 style="margin-top: 20px;">Top 20 des valeurs les plus fréquentes:</h4>
                            <div class="value-list">
                    `;
                    
                    stats.top_values.forEach(([value, count]) => {
                        html += '<div class="value-item">';
                        html += '<span class="value-name">' + value + '</span>';
                        html += '<span class="value-count">' + count.toLocaleString('fr-FR') + '</span>';
                        html += '</div>';
                    });
                    
                    html += '</div></div>';
                    content.innerHTML = html;
                }
            } catch (error) {
                console.error('Erreur:', error);
                content.innerHTML = '<div class="error-message">Erreur lors de l analyse</div>';
            }
        }
        
        async function performSearch() {
            const query = document.getElementById('searchQuery').value.trim();
            const field = document.getElementById('searchField').value;
            const resultsDiv = document.getElementById('searchResults');
            
            if (!query) {
                resultsDiv.innerHTML = '<div class="error-message">Veuillez entrer un terme de recherche</div>';
                return;
            }
            
            resultsDiv.innerHTML = `
                <div class="processing-indicator">
                    <div class="spinner"></div>
                    <div><strong>Recherche en cours...</strong></div>
                </div>
            `;
            
            try {
                const url = `/api/search?q=${encodeURIComponent(query)}${field ? '&field=' + field : ''}`;
                const response = await fetch(url);
                const data = await response.json();
                
                if (data.success) {
                    if (data.count === 0) {
                        resultsDiv.innerHTML = '<p style="padding: 20px; text-align: center; color: #666;">Aucun résultat trouvé</p>';
                        return;
                    }
                    
                    let html = `<p style="margin-bottom: 15px; color: #666;"><strong>${data.count}</strong> résultat(s) trouvé(s)</p><div class="results">`;
                    
                    data.results.forEach(obj => {
                        const titre = obj.titre || 'Sans titre';
                        const auteur = obj.auteur || '';
                        const description = obj.description || '';
                        const localisation = obj.localisation || '';
                        const domaine = obj.domaine ? (Array.isArray(obj.domaine) ? obj.domaine.join(', ') : obj.domaine) : '';
                        const periode = obj.periode_de_creation || '';
                        const reference = obj.reference || obj.numero_inventaire || 'N/A';
                        
                        html += '<div class="result-item">';
                        html += '<h3>' + titre + '</h3>';
                        if (auteur) html += '<p><strong>Auteur:</strong> ' + auteur + '</p>';
                        if (description) {
                            const shortDesc = description.length > 200 ? description.substring(0, 200) + '...' : description;
                            html += '<p><strong>Description:</strong> ' + shortDesc + '</p>';
                        }
                        if (localisation) html += '<p><strong>Localisation:</strong> ' + localisation + '</p>';
                        if (domaine) html += '<p><strong>Domaine:</strong> ' + domaine + '</p>';
                        if (periode) html += '<p><strong>Période:</strong> ' + periode + '</p>';
                        html += '<p style="font-size: 0.85em; color: #999; margin-top: 8px;"><strong>Référence:</strong> ' + reference + '</p>';
                        html += '</div>';
                    });
                    
                    html += '</div>';
                    resultsDiv.innerHTML = html;
                }
            } catch (error) {
                console.error('Erreur:', error);
                resultsDiv.innerHTML = '<div class="error-message">Erreur lors de la recherche</div>';
            }
        }
        
        // Chargement initial
        window.addEventListener('load', () => {
            loadOverview();
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("=" * 60)
    print("🎨 DASHBOARD JOCONDE - Collections des musées de France")
    print("=" * 60)
    print()

    if not os.path.exists(DATA_FILE):
        print("⚠️  ATTENTION: Fichier de données non trouvé!")
        print()
        print("📥 Téléchargez le fichier depuis:")
        print("   https://www.data.gouv.fr/api/1/datasets/r/7706931a-c76f-4018-9c29-dd3f42b58c53")
        print()
        print(f"💾 Placez le fichier dans ce répertoire et renommez-le: {DATA_FILE}")
        print()
        print("⚙️  Le serveur va démarrer mais les données ne seront pas disponibles")
        print("   tant que le fichier n'est pas en place.")
        print()
    else:
        file_size = os.path.getsize(DATA_FILE) / (1024 * 1024 * 1024)
        print(f"✅ Fichier de données trouvé: {DATA_FILE}")
        print(f"📊 Taille: {file_size:.2f} GB")
        print()

    print("🚀 Démarrage du serveur Flask...")
    print("🌐 Ouvrez votre navigateur sur: http://localhost:5000")
    print()
    print("💡 Fonctionnalités disponibles:")
    print("   • Vue d'ensemble des statistiques")
    print("   • Analyse temporelle des créations")
    print("   • Distribution géographique")
    print("   • Analyse détaillée par champ")
    print("   • Recherche dans les collections")
    print()
    print("⏹️  Appuyez sur Ctrl+C pour arrêter le serveur")
    print("=" * 60)
    print()

    app.run(debug=False, host='0.0.0.0', port=5000)