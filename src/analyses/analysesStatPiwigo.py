#!/usr/bin/env python3
"""
Analyseur de logs Piwigo via API - Détection de robots
Usage: python piwigo_analyzer.py --url https://votre-piwigo.com --username admin --password votre_pass

Configuration via fichier piwigo_config.json (optionnel):
{
    "url": "https://votre-piwigo.com",
    "username": "admin",
    "password": "votre_mot_de_passe"
}
"""

import requests
import json
import argparse
import getpass
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import hashlib
from pathlib import Path


def load_config(config_file='piwigo_config.json'):
    """Charge la configuration depuis un fichier JSON"""
    config_path = Path(config_file)

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"✅ Configuration chargée depuis {config_file}")
                return config
        except json.JSONDecodeError as e:
            print(f"⚠️  Erreur de lecture du fichier {config_file}: {e}")
            return {}
        except Exception as e:
            print(f"⚠️  Impossible de lire {config_file}: {e}")
            return {}

    return {}


def get_credentials(args):
    """Récupère les identifiants selon l'ordre: config file > arguments > prompt"""

    # Charger le fichier de config
    config = load_config(args.config if hasattr(args, 'config') and args.config else 'piwigo_config.json')

    # URL
    url = args.url or config.get('url')
    if not url:
        print("\n❌ URL Piwigo manquante")
        print("\n💡 Solutions:")
        print("   1. Créez un fichier piwigo_config.json:")
        print('      {"url": "https://votre-piwigo.com", "username": "admin", "password": "motdepasse"}')
        print("   2. Utilisez --url https://votre-piwigo.com")
        return None, None, None

    # Username
    username = args.username or config.get('username')
    if not username:
        print("\n🔐 Authentification requise")
        try:
            username = input("Nom d'utilisateur Piwigo: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n❌ Opération annulée")
            return None, None, None

    # Password
    password = args.password or config.get('password')
    if not password:
        try:
            password = getpass.getpass("Mot de passe: ")
        except (KeyboardInterrupt, EOFError):
            print("\n❌ Opération annulée")
            return None, None, None

    if not username or not password:
        print("\n❌ Identifiants incomplets")
        print("\n💡 Solutions:")
        print("   1. Créez piwigo_config.json avec vos identifiants")
        print("   2. Utilisez --username et --password")
        print("   3. Le script demandera les identifiants manquants")
        return None, None, None

    return url, username, password


def create_sample_config():
    """Crée un fichier de configuration exemple"""
    sample_config = {
        "url": "https://votre-piwigo.com",
        "username": "admin",
        "password": "votre_mot_de_passe",
        "_comment": "Renommez ce fichier en piwigo_config.json et modifiez les valeurs"
    }

    config_file = 'piwigo_config.example.json'
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=4, ensure_ascii=False)

    print(f"📝 Fichier exemple créé: {config_file}")
    print("   Renommez-le en 'piwigo_config.json' et modifiez les valeurs")


class PiwigoAPIAnalyzer:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/ws.php?format=json"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.pwg_token = None

        # Patterns à exclure des vraies pages vues
        self.technical_patterns = [
            r'/themes/', r'/plugins/', r'.css', r'.js', r'.ico',
            r'.woff', r'.ttf', r'/template/', r'/admin/', r'/_data/',
            r'/upload/', r'/i.php', r'picture.php', r'action.php'
        ]

    def login(self):
        """Connexion à l'API Piwigo"""
        print(f"🔐 Connexion à {self.base_url}...")

        # Méthode 1: pwg.session.login
        try:
            response = self.session.post(self.api_url, data={
                'method': 'pwg.session.login',
                'username': self.username,
                'password': self.password
            })

            result = response.json()

            if result.get('stat') == 'ok':
                print("✅ Connexion réussie")
                # Récupérer le token
                self.get_token()
                return True
            else:
                print(f"❌ Erreur de connexion: {result.get('message', 'Erreur inconnue')}")
                return False

        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False

    def get_token(self):
        """Récupère le token PWG pour les requêtes"""
        try:
            response = self.session.post(self.api_url, data={
                'method': 'pwg.session.getStatus'
            })
            result = response.json()
            if result.get('stat') == 'ok':
                self.pwg_token = result['result'].get('pwg_token')
        except:
            pass

    def get_history(self, limit=10000, days_back=2):
        """Récupère l'historique des visites depuis la base Piwigo"""
        print(f"\n📊 Récupération de l'historique (derniers {days_back} jours, max {limit} entrées)...")

        # Calculer la date de début
        date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        date_to = datetime.now().strftime('%Y-%m-%d')

        history_data = []
        try:
            # Utiliser l'API Piwigo Community si disponible
            # Sinon, utiliser une requête SQL via plugin
            params = {
                'method': 'pwg.extensions.checkUpdates'  # Test si admin
            }

            # Essayer avec le plugin Statistics
            crtPage = 0
            while True:
                response = self.session.post(self.api_url, data={
                    'method': 'pwg.history.search',
                    'start': date_from,
                    'end': date_to,
                    #'types': 'none|picture|high|other',
                    'format':'json',
                    # 'per_page': 100000,
                    'pageNumber': crtPage
                })

                result = response.json()

                if result.get('stat') == 'ok' and 'result' in result:
                    page_data = result['result'].get('lines', [])
                    history_data.extend(page_data)
                    if crtPage==0:
                        remainingPageCount = result['result']['maxPage']
                        crtPage = 1
                    else:
                        crtPage += 1
                    if crtPage>remainingPageCount:
                        break
                else:
                    # L'API history n'existe pas, on va récupérer via une autre méthode
                    print("⚠️  API pwg.history.search non disponible")
                    print("💡 Tentative de récupération via base MySQL...")
                    return self.get_history_via_mysql()

        except Exception as e:
            print(f"❌ Erreur lors de la récupération: {e}")
            return []
        print(f"✅ {len(history_data)} entrées récupérées via API")
        return history_data

    def get_history_via_mysql(self):
        """Alternative: proposer script SQL pour export manuel"""
        print("\n" + "=" * 70)
        print("🔧 SOLUTION ALTERNATIVE: Export MySQL")
        print("=" * 70)
        print("\nL'API Piwigo ne permet pas d'accéder directement à l'historique.")
        print("Exécutez cette requête SQL sur votre base Piwigo:\n")

        sql_query = """
-- Export de l'historique Piwigo (30 derniers jours)
SELECT 
    date,
    time,
    user_id,
    IP,
    section,
    category_id,
    image_id,
    image_type,
    tag_ids,
    user_agent
FROM piwigo_history
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
ORDER BY date DESC, time DESC
LIMIT 10000
INTO OUTFILE '/tmp/piwigo_history.csv'
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\\n';
        """

        print(sql_query)
        print("\nPuis lancez le script avec:")
        print("python piwigo_analyzer.py --csv /tmp/piwigo_history.csv")
        print("=" * 70 + "\n")

        return []

    def get_stats_summary(self):
        """Récupère les statistiques générales de Piwigo"""
        print("\n📈 Récupération des statistiques générales...")

        try:
            # Stats globales
            response = self.session.post(self.api_url, data={
                'method': 'pwg.getInfos'
            })

            result = response.json()

            if result.get('stat') == 'ok' and 'result' in result:
                infos = result['result']
                return {
                    'version': infos.get('version', 'inconnue'),
                    'nb_elements': infos.get('nb_elements', 0),
                    'nb_categories': infos.get('nb_categories', 0),
                    'nb_users': infos.get('nb_users', 0)
                }
        except Exception as e:
            print(f"⚠️  Impossible de récupérer les stats: {e}")

        return {}

    def analyze_history_data(self, history_data):
        """Analyse les données d'historique"""
        if not history_data:
            return None

        suspicious_ips = defaultdict(lambda: {
            'requests': 0,
            'images': 0,
            'pages': 0,
            'categories': set(),
            'user_agents': set(),
            'dates': [],
            'sections': Counter()
        })

        print(f"\n🔍 Analyse de {len(history_data)} entrées...")

        for entry in history_data:
            ip = entry.get('IP', 'unknown')
            section = entry.get('SECTION', '')
            image_id = entry.get('IMAGEID')
            user_agent = entry.get('USERAGENT', '')
            date_time = f"{entry.get('DATE', '')} {entry.get('time', '')}"

            suspicious_ips[ip]['requests'] += 1
            suspicious_ips[ip]['sections'][section] += 1

            if user_agent:
                suspicious_ips[ip]['user_agents'].add(user_agent)

            if date_time.strip():
                suspicious_ips[ip]['dates'].append(date_time)

            if image_id:
                suspicious_ips[ip]['images'] += 1
            else:
                suspicious_ips[ip]['pages'] += 1

            cat_id = entry.get('category_id')
            if cat_id:
                suspicious_ips[ip]['categories'].add(cat_id)

        return suspicious_ips

    def detect_bots(self, suspicious_ips, min_requests=5, images_per_hour=5):
        """Détecte les IPs suspectes"""
        bots = []

        bot_keywords = ['bot', 'crawler', 'spider', 'scraper', 'wget',
                        'curl', 'python', 'java', 'go-http', 'scrapy']

        for ip, stats in suspicious_ips.items():
            score = 0
            reasons = []

            # Critère 1: Nombre de requêtes élevé
            if stats['requests'] > min_requests:
                score += 1
                reasons.append(f"{stats['requests']} requêtes")

            # Critère 2: Taux de téléchargement d'images
            if stats['dates']:
                try:
                    dates = [datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
                             for d in stats['dates'] if d.strip()]
                    if len(dates) > 1:
                        duration_hours = (max(dates) - min(dates)).total_seconds() / 3600
                        if duration_hours > 0:
                            rate = stats['images'] / duration_hours
                            if rate > images_per_hour:
                                score += 2
                                reasons.append(f"{rate:.1f} images/h")
                except:
                    pass

            # Critère 3: Ratio images/pages anormal
            if stats['pages'] > 0:
                ratio = stats['images'] / stats['pages']
                if ratio > 30:
                    score += 2
                    reasons.append(f"Ratio img/page: {ratio:.1f}")
            elif stats['images'] > 50:
                score += 2
                reasons.append("Que des images, aucune page")

            # Critère 4: User agent suspect
            for ua in stats['user_agents']:
                ua_lower = ua.lower()
                if any(keyword in ua_lower for keyword in bot_keywords):
                    score += 3
                    reasons.append(f"Bot UA: {ua[:40]}")
                    break

            # Critère 5: Comportement de scraping (beaucoup de catégories)
            if len(stats['categories']) > 100:
                score += 1
                reasons.append(f"{len(stats['categories'])} catégories visitées")

            if score >= 3:
                bots.append({
                    'ip': ip,
                    'score': score,
                    'stats': stats,
                    'reasons': reasons
                })

        return sorted(bots, key=lambda x: x['score'], reverse=True)

    def generate_reports(self, bots, stats_summary):
        """Génère les rapports de détection"""
        print("\n" + "=" * 70)
        print("RAPPORT D'ANALYSE PIWIGO")
        print("=" * 70)

        if stats_summary:
            print(f"\nINFORMATIONS INSTANCE:")
            print(f"  Version Piwigo:      {stats_summary.get('version', 'N/A')}")
            print(f"  Photos:              {stats_summary.get('nb_elements', 0):,}")
            print(f"  Albums:              {stats_summary.get('nb_categories', 0):,}")
            print(f"  Utilisateurs:        {stats_summary.get('nb_users', 0):,}")

        print(f"\n\nROBOTS/IPS SUSPECTS: {len(bots)}")
        print("=" * 70)

        if not bots:
            print("\n✅ Aucun robot suspect détecté avec les critères actuels")
            return

        for i, bot in enumerate(bots[:30], 1):
            print(f"\n{i}. IP: {bot['ip']} (Score: {bot['score']}/10)")
            print(f"   📊 Requêtes: {bot['stats']['requests']:,} | "
                  f"Images: {bot['stats']['images']:,} | "
                  f"Pages: {bot['stats']['pages']:,}")
            print(f"   📂 Albums visités: {len(bot['stats']['categories'])}")

            # Sections les plus visitées
            top_sections = bot['stats']['sections'].most_common(3)
            if top_sections:
                sections_str = ", ".join([f"{s}({c})" for s, c in top_sections])
                print(f"   🔍 Top sections: {sections_str}")

            print(f"   ⚠️  Raisons: {', '.join(bot['reasons'])}")

            if bot['stats']['user_agents']:
                ua = list(bot['stats']['user_agents'])[0]
                print(f"   🤖 User-Agent: {ua[:70]}...")

        # Générer fichier de bannissement
        self.generate_ban_files(bots)

    def generate_ban_files(self, bots):
        """Génère les fichiers de bannissement"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # .htaccess
        htaccess_file = f'piwigo_ban_htaccess_{timestamp}.txt'
        with open(htaccess_file, 'w') as f:
            f.write("# Règles de bannissement pour Apache (.htaccess)\n")
            f.write(f"# Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# À ajouter dans votre .htaccess Piwigo\n\n")
            f.write("<RequireAll>\n")
            f.write("    Require all granted\n")
            for bot in bots[:50]:  # Top 50
                f.write(f"    Require not ip {bot['ip']}\n")
            f.write("</RequireAll>\n")

        # nginx
        nginx_file = f'piwigo_ban_nginx_{timestamp}.conf'
        with open(nginx_file, 'w') as f:
            f.write("# Règles de bannissement pour Nginx\n")
            f.write(f"# Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# À inclure dans votre config nginx\n\n")
            for bot in bots[:50]:
                f.write(f"deny {bot['ip']};\n")

        # Fail2ban
        fail2ban_file = f'piwigo_ips_banned_{timestamp}.txt'
        with open(fail2ban_file, 'w') as f:
            f.write("# IPs à bannir (format simple)\n")
            f.write(f"# Généré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for bot in bots:
                f.write(f"{bot['ip']}\n")

        print(f"\n📝 Fichiers générés:")
        print(f"   ✓ {htaccess_file} (Apache)")
        print(f"   ✓ {nginx_file} (Nginx)")
        print(f"   ✓ {fail2ban_file} (Liste simple)")

    def logout(self):
        """Déconnexion"""
        try:
            self.session.post(self.api_url, data={'method': 'pwg.session.logout'})
        except:
            pass


def analyze_csv_file(csv_file):
    """Analyse un fichier CSV exporté de MySQL"""
    import csv

    print(f"📂 Lecture du fichier CSV: {csv_file}")

    history_data = []

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                history_data.append(row)

        print(f"✅ {len(history_data)} entrées chargées depuis le CSV")
        return history_data

    except Exception as e:
        print(f"❌ Erreur lecture CSV: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Analyse Piwigo pour détecter les robots',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Via API Piwigo avec fichier de config
  python piwigo_analyzer.py

  # Via API avec paramètres en ligne de commande
  python piwigo_analyzer.py --url https://photos.exemple.com --username admin --password monpass

  # Via fichier CSV exporté
  python piwigo_analyzer.py --csv /tmp/piwigo_history.csv

  # Créer un fichier de config exemple
  python piwigo_analyzer.py --create-config

  # Avec options personnalisées
  python piwigo_analyzer.py --days 60 --min-requests 100

Fichier de configuration (piwigo_config.json):
  {
      "url": "https://votre-piwigo.com",
      "username": "admin",
      "password": "votre_mot_de_passe"
  }
        """)

    parser.add_argument('--url', help='URL de votre instance Piwigo')
    parser.add_argument('-u', '--username', help='Nom d\'utilisateur admin')
    parser.add_argument('-p', '--password', help='Mot de passe')
    parser.add_argument('--config', default='piwigo_config.json',
                        help='Fichier de configuration (défaut: piwigo_config.json)')
    parser.add_argument('--create-config', action='store_true',
                        help='Créer un fichier de configuration exemple')
    parser.add_argument('--csv', help='Fichier CSV exporté de la base MySQL')
    parser.add_argument('--days', type=int, default=2,
                        help='Nombre de jours à analyser (défaut: 2)')
    parser.add_argument('--min-requests', type=int, default=50,
                        help='Seuil de requêtes suspectes (défaut: 50)')
    parser.add_argument('--images-per-hour', type=int, default=100,
                        help='Seuil d\'images/heure suspect (défaut: 100)')

    args = parser.parse_args()

    # Option pour créer un fichier de config exemple
    if args.create_config:
        create_sample_config()
        return

    history_data = []
    stats_summary = {}

    if args.csv:
        # Mode CSV
        if not Path(args.csv).exists():
            print(f"❌ Fichier {args.csv} introuvable")
            return

        history_data = analyze_csv_file(args.csv)

    else:
        # Mode API - Récupération des credentials
        url, username, password = get_credentials(args)

        if not all([url, username, password]):
            print(
                "\n💡 Astuce: Lancez 'python piwigo_analyzer.py --create-config' pour créer un fichier de configuration")
            return

        analyzer = PiwigoAPIAnalyzer(url, username, password)

        if not analyzer.login():
            print("\n💡 Conseil: Vérifiez vos identifiants ou utilisez --csv pour analyser un export")
            return

        stats_summary = analyzer.get_stats_summary()
        history_data = analyzer.get_history(days_back=args.days)
        analyzer.logout()

    if not history_data:
        print("\n⚠️  Aucune donnée à analyser")
        return

    # Analyse
    print("\n🔄 Analyse en cours...")
    api_analyzer = PiwigoAPIAnalyzer('', '', '')  # Instance vide pour les méthodes
    suspicious_ips = api_analyzer.analyze_history_data(history_data)

    if suspicious_ips:
        bots = api_analyzer.detect_bots(
            suspicious_ips,
            args.min_requests,
            args.images_per_hour
        )
        api_analyzer.generate_reports(bots, stats_summary)

        print(f"\n✅ Analyse terminée - {len(bots)} robots détectés")
    else:
        print("\n⚠️  Aucune IP suspecte détectée")


if __name__ == '__main__':
    main()
