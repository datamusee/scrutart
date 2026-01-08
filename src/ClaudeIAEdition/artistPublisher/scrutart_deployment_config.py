"""
Configuration de déploiement Scrutart
Fichier de configuration pour automatiser le déploiement des flows Prefect
"""

import os
from pathlib import Path
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import IntervalSchedule
from prefect.blocks.system import Secret
from datetime import timedelta

# Import des flows depuis le module principal
from scrutart_prefect_automation import (
    process_artist_complete,
    process_artists_batch,
    config
)


def create_scrutart_deployments():
    """
    Crée tous les déploiements Prefect pour Scrutart
    """
    
    # Déploiement pour artiste unique
    single_artist_deployment = Deployment.build_from_flow(
        flow=process_artist_complete,
        name="scrutart-single-artist",
        version="1.0.0",
        description="Traitement complet d'un artiste unique avec génération de contenu Scrutart",
        tags=["scrutart", "artist", "single", "automation"],
        parameters={
            "qid": "Q296",  # Valeur par défaut (Claude Monet)
        },
        work_pool_name="scrutart-pool",
        work_queue_name="default",
        schedule=None,  # Pas de schedule automatique pour les traitements individuels
        is_schedule_active=False
    )
    
    # Déploiement pour traitement par lots
    batch_deployment = Deployment.build_from_flow(
        flow=process_artists_batch,
        name="scrutart-batch-processing",
        version="1.0.0", 
        description="Traitement par lots d'artistes avec génération de contenu Scrutart",
        tags=["scrutart", "batch", "artists", "automation"],
        parameters={
            "qids": ["Q296", "Q5582", "Q5597"],  # Exemples par défaut
            "batch_id": None
        },
        work_pool_name="scrutart-pool",
        work_queue_name="batch",
        schedule=IntervalSchedule(interval=timedelta(hours=6)),  # Toutes les 6 heures
        is_schedule_active=False  # Désactivé par défaut
    )
    
    return [single_artist_deployment, batch_deployment]


def setup_prefect_blocks():
    """
    Configure les blocs Prefect nécessaires (secrets, configurations, etc.)
    """
    
    # Configuration WordPress
    wordpress_config = {
        "api_url": os.getenv("WORDPRESS_API_URL", "https://scrutart.grains-de-culture.fr/wp-json/wp/v2/"),
        "username": os.getenv("WORDPRESS_USERNAME", ""),
        "password": os.getenv("WORDPRESS_PASSWORD", "")
    }
    
    # Configuration Piwigo
    piwigo_config = {
        "url": os.getenv("PIWIGO_URL", "https://galeries.grains-de-culture.fr/"),
        "username": os.getenv("PIWIGO_USERNAME", ""),
        "password": os.getenv("PIWIGO_PASSWORD", "")
    }
    
    # Configuration du graphe d'état Scrutart
    scrutart_state_config = {
        "url": os.getenv("SCRUTART_STATE_URL", "http://localhost:5000"),
        "token": os.getenv("SCRUTART_STATE_TOKEN", "")
    }
    
    try:
        # Créer les blocs de secrets
        wordpress_secret = Secret(value=wordpress_config)
        wordpress_secret.save("wordpress-credentials", overwrite=True)
        
        piwigo_secret = Secret(value=piwigo_config)
        piwigo_secret.save("piwigo-credentials", overwrite=True)
        
        scrutart_state_secret = Secret(value=scrutart_state_config)
        scrutart_state_secret.save("scrutart-state-credentials", overwrite=True)
        
        print("✅ Blocs Prefect créés avec succès")
        
    except Exception as e:
        print(f"❌ Erreur création des blocs: {e}")


def deploy_all():
    """
    Déploie tous les composants Scrutart
    """
    print("🚀 Début du déploiement Scrutart...")
    
    try:
        # 1. Configurer les blocs
        print("📦 Configuration des blocs Prefect...")
        setup_prefect_blocks()
        
        # 2. Créer les déploiements
        print("🔧 Création des déploiements...")
        deployments = create_scrutart_deployments()
        
        # 3. Appliquer les déploiements
        for deployment in deployments:
            print(f"📤 Application du déploiement: {deployment.name}")
            deployment_id = deployment.apply()
            print(f"   ✅ Déploiement créé avec l'ID: {deployment_id}")
        
        print("🎉 Déploiement terminé avec succès!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du déploiement: {e}")
        return False


def create_work_pool():
    """
    Crée le work pool pour Scrutart si nécessaire
    """
    import subprocess
    import sys
    
    try:
        # Créer le work pool
        result = subprocess.run([
            sys.executable, '-m', 'prefect', 'work-pool', 'create',
            'scrutart-pool', '--type', 'process'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Work pool 'scrutart-pool' créé")
        else:
            print(f"⚠️ Work pool existe peut-être déjà: {result.stderr}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur création work pool: {e}")
        return False


def start_agent():
    """
    Démarre un agent Prefect pour le work pool Scrutart
    """
    import subprocess
    import sys
    
    try:
        print("🤖 Démarrage de l'agent Prefect...")
        
        # Commande pour démarrer l'agent
        cmd = [
            sys.executable, '-m', 'prefect', 'agent', 'start',
            '--pool', 'scrutart-pool',
            '--work-queue', 'default'
        ]
        
        print(f"Commande: {' '.join(cmd)}")
        
        # Démarrer l'agent (cette commande bloque)
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("🛑 Agent arrêté")
    except Exception as e:
        print(f"❌ Erreur agent: {e}")


# Configuration pour les fichiers YAML de déploiement
DEPLOYMENT_YAML_TEMPLATE = """
name: {name}
description: {description}
version: {version}
tags: {tags}
flow_name: {flow_name}
schedule: {schedule}
parameters: {parameters}
work_pool:
  name: scrutart-pool
  work_queue_name: {work_queue}
"""


def generate_deployment_files():
    """
    Génère les fichiers YAML de déploiement
    """
    deployments_config = [
        {
            "name": "scrutart-single-artist",
            "description": "Traitement complet d'un artiste unique",
            "version": "1.0.0",
            "tags": ["scrutart", "artist", "single"],
            "flow_name": "process_artist_complete",
            "schedule": "null",
            "parameters": {"qid": "Q296"},
            "work_queue": "default"
        },
        {
            "name": "scrutart-batch-processing", 
            "description": "Traitement par lots d'artistes",
            "version": "1.0.0",
            "tags": ["scrutart", "batch", "artists"],
            "flow_name": "process_artists_batch",
            "schedule": "null",  # Modifié en fonction des besoins
            "parameters": {"qids": ["Q296", "Q5582"], "batch_id": "null"},
            "work_queue": "batch"
        }
    ]
    
    for config in deployments_config:
        filename = f"{config['name']}-deployment.yaml"
        content = DEPLOYMENT_YAML_TEMPLATE.format(**config)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Fichier généré: {filename}")


def check_prefect_server():
    """
    Vérifie que le serveur Prefect est accessible
    """
    import requests
    
    try:
        response = requests.get("http://localhost:4200/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Serveur Prefect accessible")
            return True
        else:
            print(f"❌ Serveur Prefect inaccessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Impossible de joindre le serveur Prefect: {e}")
        return False


def setup_environment():
    """
    Configure l'environnement complet Scrutart
    """
    print("🔧 Configuration de l'environnement Scrutart...")
    
    # Vérifications préalables
    if not check_prefect_server():
        print("❌ Veuillez démarrer le serveur Prefect avec: prefect server start")
        return False
    
    # Création du work pool
    if not create_work_pool():
        return False
    
    # Déploiement complet
    if not deploy_all():
        return False
    
    # Génération des fichiers de configuration
    generate_deployment_files()
    
    print("""
🎉 Configuration terminée!

Prochaines étapes:
1. Démarrer l'agent Prefect:
   python -c "from scrutart_deployment_config import start_agent; start_agent()"

2. Démarrer le serveur web:
   python scrutart_web_server.py

3. Accéder à l'interface:
   http://localhost:5001

4. Interface Prefect:
   http://localhost:4200
""")
    
    return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            setup_environment()
        elif command == "deploy":
            deploy_all()
        elif command == "agent":
            start_agent()
        elif command == "check":
            check_prefect_server()
        elif command == "yaml":
            generate_deployment_files()
        else:
            print(f"Commande inconnue: {command}")
            print("Commandes disponibles: setup, deploy, agent, check, yaml")
    else:
        print("Usage: python scrutart_deployment_config.py [setup|deploy|agent|check|yaml]")
        print("\nCommandes:")
        print("  setup  - Configuration complète de l'environnement")
        print("  deploy - Déploiement des flows seulement") 
        print("  agent  - Démarrage de l'agent Prefect")
        print("  check  - Vérification du serveur Prefect")
        print("  yaml   - Génération des fichiers YAML de déploiement")