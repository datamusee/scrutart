from flask import Flask, jsonify, request
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import ipaddress
import re
from functools import lru_cache
import mysql.connector
from typing import Optional
from CPiwigoManager import CPiwigoManager, CategoryType

app = Flask(__name__)

# Configuration Piwigo
pimag = CPiwigoManager()
PIWIGO_URL = "https://galeries.grains-de-culture.fr"
PIWIGO_API = f"{PIWIGO_URL}/ws.php"
PIWIGO_USERNAME = pimag.login
PIWIGO_PASSWORD = pimag.password

# Configuration base de données (optionnelle)
DB_CONFIG = {
    'host': 'votre_host',
    'user': 'votre_user',
    'password': 'votre_password',
    'database': 'piwigo_db'
}


class PiwigoAPI:
    """Gestionnaire d'API Piwigo"""

    def __init__(self):
        self.session = requests.Session()
        self.token = None

    def login(self):
        """Connexion à l'API Piwigo"""
        try:
            response = self.session.post(
                PIWIGO_API,
                params={
                    'format': 'json',
                    'method': 'pwg.session.login'
                },
                data={
                    'username': PIWIGO_USERNAME,
                    'password': PIWIGO_PASSWORD
                }
            )
            result = response.json()
            if result.get('stat') == 'ok':
                return True
            return False
        except Exception as e:
            print(f"Erreur de connexion: {e}")
            return False

    def get_categories(self):
        """Récupère toutes les catégories/albums"""
        try:
            response = self.session.get(
                PIWIGO_API,
                params={
                    'format': 'json',
                    'method': 'pwg.categories.getList',
                    'recursive': 'true',
                    'fullname': 'true'
                }
            )
            result = response.json()
            if result.get('stat') == 'ok':
                return result.get('result', {}).get('categories', [])
            return []
        except Exception as e:
            print(f"Erreur récupération catégories: {e}")
            return []

    def get_images_count(self):
        """Récupère le nombre total d'images"""
        try:
            response = self.session.get(
                PIWIGO_API,
                params={
                    'format': 'json',
                    'method': 'pwg.images.search',
                    'per_page': '1'
                }
            )
            result = response.json()
            if result.get('stat') == 'ok':
                paging = result.get('result', {}).get('paging', {})
                return paging.get('total_count', 0)
            return 0
        except Exception as e:
            print(f"Erreur comptage images: {e}")
            return 0


class WhoisAnalyzer:
    """Analyseur WHOIS pour identifier les propriétaires d'IP"""

    @staticmethod
    @lru_cache(maxsize=1000)
    def get_ip_owner(ip: str) -> str:
        """Récupère le propriétaire d'une IP via WHOIS"""
        try:
            # Utilisation d'un service WHOIS (ex: ipinfo.io, ipapi.co)
            response = requests.get(
                f"https://ipapi.co/{ip}/json/",
                timeout=3
            )
            if response.status_code == 200:
                data = response.json()
                org = data.get('org', '')
                asn = data.get('asn', '')
                return f"{org} ({asn})" if org else f"ASN {asn}"
            return "Inconnu"
        except Exception as e:
            print(f"Erreur WHOIS pour {ip}: {e}")
            return "Inconnu"

    @staticmethod
    def is_bot_ip(ip_owner: str) -> bool:
        """Détecte si l'IP appartient à un bot connu"""
        bot_keywords = [
            'google', 'googlebot', 'bot', 'crawler', 'spider',
            'scraper', 'facebook', 'twitter', 'amazon', 'microsoft',
            'cloudflare', 'bytedance', 'baidu', 'yandex'
        ]
        return any(keyword in ip_owner.lower() for keyword in bot_keywords)


class DatabaseAnalyzer:
    """Analyseur de base de données (optionnel)"""

    @staticmethod
    def get_connection():
        """Crée une connexion à la base de données"""
        return mysql.connector.connect(**DB_CONFIG)

    @staticmethod
    def get_visit_stats(days: int = 30):
        """Récupère les statistiques de visite depuis la DB"""
        try:
            conn = DatabaseAnalyzer.get_connection()
            cursor = conn.cursor(dictionary=True)

            date_limit = datetime.now() - timedelta(days=days)

            query = """
                SELECT 
                    DATE(time) as date,
                    IP as ip,
                    COUNT(*) as hits,
                    section,
                    category_id
                FROM piwigo_history
                WHERE time >= %s
                GROUP BY DATE(time), IP, section, category_id
                ORDER BY date DESC, hits DESC
            """

            cursor.execute(query, (date_limit,))
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            return results
        except Exception as e:
            print(f"Erreur récupération stats DB: {e}")
            return []

    @staticmethod
    def get_most_viewed_images(limit: int = 20):
        """Récupère les images les plus vues"""
        try:
            conn = DatabaseAnalyzer.get_connection()
            cursor = conn.cursor(dictionary=True)

            query = """
                SELECT 
                    i.id,
                    i.name,
                    i.file,
                    COUNT(h.id) as views,
                    i.date_creation
                FROM piwigo_history h
                JOIN piwigo_images i ON h.image_id = i.id
                WHERE h.image_id IS NOT NULL
                GROUP BY h.image_id
                ORDER BY views DESC
                LIMIT %s
            """

            cursor.execute(query, (limit,))
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            return results
        except Exception as e:
            print(f"Erreur récupération images populaires: {e}")
            return []


class DashboardDataBuilder:
    """Constructeur de données pour le dashboard"""

    def __init__(self):
        self.piwigo = PiwigoAPI()
        self.whois = WhoisAnalyzer()

    def build_albums_structure(self):
        """Construit la structure JSON des albums"""
        if not self.piwigo.login():
            return {'error': 'Connexion échouée'}

        categories = self.piwigo.get_categories()

        # Crée un dictionnaire pour accès rapide par ID
        cat_by_id = {cat['id']: cat for cat in categories}

        # Analyse des albums
        root_albums = {}
        total_albums = len(categories)
        public_albums = 0

        for cat in categories:
            if cat.get('status') == 'public':
                public_albums += 1

            # Identifie les albums racine (id_uppercat est vide ou None)
            if not cat.get('id_uppercat'):
                album_id = cat['id']
                root_albums[album_id] = {
                    'name': cat.get('name', ''),
                    'id': album_id,
                    'total_sub_albums': 0,
                    'public_sub_albums': 0,
                    'nb_images': cat.get('nb_images', 0),
                    'total_nb_images': cat.get('total_nb_images', 0)
                }

        # Compte les sous-albums pour chaque racine
        for cat in categories:
            uppercat = cat.get('id_uppercat')
            if uppercat:
                # Trouve la racine de cet album
                root_id = self._find_root_parent(cat['id'], cat_by_id)
                if root_id and root_id in root_albums:
                    root_albums[root_id]['total_sub_albums'] += 1
                    if cat.get('status') == 'public':
                        root_albums[root_id]['public_sub_albums'] += 1

        return {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_albums': total_albums,
                'public_albums': public_albums,
                'private_albums': total_albums - public_albums,
                'total_images': self.piwigo.get_images_count()
            },
            'root_albums': list(root_albums.values())
        }

    def _find_root_parent(self, cat_id, cat_by_id):
        """Trouve l'ID de l'album racine d'une catégorie"""
        if cat_id not in cat_by_id:
            return None

        current_cat = cat_by_id[cat_id]
        uppercat = current_cat.get('id_uppercat')

        # Si pas de parent, c'est une racine
        if not uppercat:
            return cat_id

        # Sinon, remonte récursivement
        return self._find_root_parent(uppercat, cat_by_id)

    def build_traffic_analysis(self, days: int = 30):
        """Construit l'analyse de trafic avancée"""
        visits = DatabaseAnalyzer.get_visit_stats(days)

        if not visits:
            return {'error': 'Aucune donnée disponible'}

        # Agrégation par IP avec identification WHOIS
        ip_stats = defaultdict(lambda: {
            'hits': 0,
            'days_active': set(),
            'owner': '',
            'is_bot': False
        })

        daily_stats = defaultdict(lambda: {
            'unique_ips': set(),
            'total_hits': 0,
            'bot_hits': 0,
            'human_hits': 0
        })

        for visit in visits:
            ip = visit['ip']
            date = visit['date'].strftime('%Y-%m-%d')
            hits = visit['hits']

            # Analyse WHOIS (avec cache)
            if not ip_stats[ip]['owner']:
                owner = self.whois.get_ip_owner(ip)
                ip_stats[ip]['owner'] = owner
                ip_stats[ip]['is_bot'] = self.whois.is_bot_ip(owner)

            ip_stats[ip]['hits'] += hits
            ip_stats[ip]['days_active'].add(date)

            # Stats quotidiennes
            daily_stats[date]['unique_ips'].add(ip)
            daily_stats[date]['total_hits'] += hits

            if ip_stats[ip]['is_bot']:
                daily_stats[date]['bot_hits'] += hits
            else:
                daily_stats[date]['human_hits'] += hits

        # Formatage des résultats
        top_sources = sorted(
            [
                {
                    'ip': ip,
                    'owner': data['owner'],
                    'hits': data['hits'],
                    'days_active': len(data['days_active']),
                    'is_bot': data['is_bot'],
                    'category': 'Bot' if data['is_bot'] else 'Humain'
                }
                for ip, data in ip_stats.items()
            ],
            key=lambda x: x['hits'],
            reverse=True
        )[:50]

        # Stats quotidiennes formatées
        daily_formatted = [
            {
                'date': date,
                'unique_visitors': len(stats['unique_ips']),
                'total_hits': stats['total_hits'],
                'bot_hits': stats['bot_hits'],
                'human_hits': stats['human_hits']
            }
            for date, stats in sorted(daily_stats.items())
        ]

        return {
            'timestamp': datetime.now().isoformat(),
            'period_days': days,
            'top_sources': top_sources,
            'daily_stats': daily_formatted,
            'summary': {
                'total_unique_ips': len(ip_stats),
                'identified_bots': sum(1 for s in ip_stats.values() if s['is_bot']),
                'human_visitors': sum(1 for s in ip_stats.values() if not s['is_bot'])
            }
        }


# Routes Flask
@app.route('/')
def index():
    """Page d'accueil du dashboard"""
    return DASHBOARD_TEMPLATE


@app.route('/api/albums')
def api_albums():
    """API: Structure des albums"""
    builder = DashboardDataBuilder()
    data = builder.build_albums_structure()
    return jsonify(data)


@app.route('/analytics')
def analytics():
    """Page d'analyse de trafic"""
    return ANALYTICS_TEMPLATE


@app.route('/api/traffic')
def api_traffic():
    """API: Analyse de trafic"""
    days = request.args.get('days', 30, type=int)
    builder = DashboardDataBuilder()
    data = builder.build_traffic_analysis(days)
    return jsonify(data)


@app.route('/api/popular-images')
def api_popular_images():
    """API: Images les plus vues (optionnel, nécessite DB)"""
    limit = request.args.get('limit', 20, type=int)
    images = DatabaseAnalyzer.get_most_viewed_images(limit)
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'images': images
    })


# Templates HTML intégrés
DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Piwigo</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f6fa;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .nav {
            margin-top: 20px;
        }
        .nav a {
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            margin-right: 10px;
            display: inline-block;
        }
        .nav a:hover { background: rgba(255,255,255,0.3); }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .stat-card .value {
            font-size: 2.5em;
            color: #667eea;
            font-weight: bold;
        }
        .albums-list {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .albums-list h2 {
            margin-bottom: 20px;
            color: #333;
        }
        .album-item {
            padding: 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .album-item:last-child { border-bottom: none; }
        .album-name { font-weight: 600; color: #333; }
        .album-stats {
            display: flex;
            gap: 20px;
            font-size: 0.9em;
            color: #666;
        }
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge.public { background: #d4edda; color: #155724; }
        .badge.private { background: #f8d7da; color: #721c24; }
        .loading {
            text-align: center;
            padding: 50px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Dashboard Piwigo</h1>
        <p>Statistiques et analyse de votre galerie photo</p>
        <div class="nav">
            <a href="/">Accueil</a>
            <a href="/analytics">Analyses de trafic</a>
        </div>
    </div>

    <div class="stats-grid" id="stats">
        <div class="loading">Chargement des statistiques...</div>
    </div>

    <div class="albums-list" id="albums">
        <h2>Albums Racine</h2>
        <div class="loading">Chargement des albums...</div>
    </div>

    <script>
        async function loadDashboard() {
            try {
                const response = await fetch('/api/albums');
                const data = await response.json();

                if (data.error) {
                    alert('Erreur: ' + data.error);
                    return;
                }

                // Affichage des statistiques
                const statsHTML = `
                    <div class="stat-card">
                        <h3>Albums Total</h3>
                        <div class="value">${data.summary.total_albums}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Albums Publics</h3>
                        <div class="value">${data.summary.public_albums}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Albums Privés</h3>
                        <div class="value">${data.summary.private_albums}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Images Total</h3>
                        <div class="value">${data.summary.total_images}</div>
                    </div>
                `;
                document.getElementById('stats').innerHTML = statsHTML;

                // Affichage des albums
                const albumsHTML = data.root_albums.map(album => `
                    <div class="album-item">
                        <div class="album-name">${album.name}</div>
                        <div class="album-stats">
                            <span>Sous-albums: ${album.total_sub_albums}</span>
                            <span class="badge public">Public: ${album.public_sub_albums}</span>
                            <span>Images: ${album.total_nb_images}</span>
                        </div>
                    </div>
                `).join('');

                document.getElementById('albums').innerHTML = `
                    <h2>Albums Racine</h2>
                    ${albumsHTML}
                `;
            } catch (error) {
                console.error('Erreur:', error);
                alert('Erreur de chargement des données');
            }
        }

        loadDashboard();
    </script>
</body>
</html>
    '''

ANALYTICS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analyses de Trafic - Piwigo</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f6fa;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .nav {
            margin-top: 20px;
        }
        .nav a {
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            margin-right: 10px;
            display: inline-block;
        }
        .nav a:hover { background: rgba(255,255,255,0.3); }
        .controls {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .controls label {
            margin-right: 10px;
            font-weight: 600;
        }
        .controls select {
            padding: 8px 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 1em;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-card h3 {
            color: #666;
            font-size: 0.85em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        .stat-card .value {
            font-size: 2em;
            color: #f5576c;
            font-weight: bold;
        }
        .chart-container {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .chart-container h2 {
            margin-bottom: 20px;
            color: #333;
        }
        .sources-table {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge.bot { background: #fff3cd; color: #856404; }
        .badge.human { background: #d1ecf1; color: #0c5460; }
        .loading {
            text-align: center;
            padding: 50px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Analyses de Trafic Avancées</h1>
        <p>Identification des sources et analyse du comportement</p>
        <div class="nav">
            <a href="/">Accueil</a>
            <a href="/analytics">Analyses de trafic</a>
        </div>
    </div>

    <div class="controls">
        <label for="period">Période d'analyse:</label>
        <select id="period" onchange="loadAnalytics()">
            <option value="7">7 derniers jours</option>
            <option value="30" selected>30 derniers jours</option>
            <option value="60">60 derniers jours</option>
            <option value="90">90 derniers jours</option>
        </select>
    </div>

    <div class="stats-grid" id="stats">
        <div class="loading">Chargement des statistiques...</div>
    </div>

    <div class="chart-container">
        <h2>📈 Évolution du Trafic</h2>
        <canvas id="trafficChart"></canvas>
    </div>

    <div class="sources-table" id="sources">
        <h2>🌐 Top Sources de Trafic (avec identification WHOIS)</h2>
        <div class="loading">Analyse des sources en cours...</div>
    </div>

    <script>
        let trafficChart = null;

        async function loadAnalytics() {
            const days = document.getElementById('period').value;

            try {
                const response = await fetch(`/api/traffic?days=${days}`);
                const data = await response.json();

                if (data.error) {
                    alert('Erreur: ' + data.error);
                    return;
                }

                // Affichage des statistiques
                const statsHTML = `
                    <div class="stat-card">
                        <h3>IPs Uniques</h3>
                        <div class="value">${data.summary.total_unique_ips}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Bots Identifiés</h3>
                        <div class="value">${data.summary.identified_bots}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Visiteurs Humains</h3>
                        <div class="value">${data.summary.human_visitors}</div>
                    </div>
                    <div class="stat-card">
                        <h3>Période</h3>
                        <div class="value">${data.period_days}j</div>
                    </div>
                `;
                document.getElementById('stats').innerHTML = statsHTML;

                // Graphique de trafic
                renderTrafficChart(data.daily_stats);

                // Table des sources
                renderSourcesTable(data.top_sources);

            } catch (error) {
                console.error('Erreur:', error);
                alert('Erreur de chargement des analyses');
            }
        }

        function renderTrafficChart(dailyStats) {
            const ctx = document.getElementById('trafficChart').getContext('2d');

            if (trafficChart) {
                trafficChart.destroy();
            }

            const labels = dailyStats.map(d => d.date);
            const humanHits = dailyStats.map(d => d.human_hits);
            const botHits = dailyStats.map(d => d.bot_hits);

            trafficChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Trafic Humain',
                            data: humanHits,
                            borderColor: 'rgb(75, 192, 192)',
                            backgroundColor: 'rgba(75, 192, 192, 0.1)',
                            tension: 0.4
                        },
                        {
                            label: 'Trafic Bots',
                            data: botHits,
                            borderColor: 'rgb(255, 159, 64)',
                            backgroundColor: 'rgba(255, 159, 64, 0.1)',
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        function renderSourcesTable(sources) {
            const tableHTML = `
                <h2>🌐 Top Sources de Trafic (avec identification WHOIS)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rang</th>
                            <th>Adresse IP</th>
                            <th>Propriétaire (WHOIS)</th>
                            <th>Type</th>
                            <th>Requêtes</th>
                            <th>Jours Actifs</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${sources.map((source, index) => `
                            <tr>
                                <td>${index + 1}</td>
                                <td><code>${source.ip}</code></td>
                                <td>${source.owner}</td>
                                <td><span class="badge ${source.is_bot ? 'bot' : 'human'}">${source.category}</span></td>
                                <td><strong>${source.hits}</strong></td>
                                <td>${source.days_active}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            document.getElementById('sources').innerHTML = tableHTML;
        }

        loadAnalytics();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=5000)