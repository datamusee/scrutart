#!/usr/bin/env python3
"""
Script de déploiement pour WikimediaAccess amélioré
"""
import os
import sys
import shutil
import subprocess
import yaml
from pathlib import Path


def backup_current_version():
    """Sauvegarde la version actuelle"""
    print("📦 Sauvegarde de la version actuelle...")

    backup_dir = Path("backups") / f"backup_{int(time.time())}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Fichiers à sauvegarder
    files_to_backup = [
        "WikimediaManagerPackage/WikimediaAccess.py",
        "WikimediaManagerPackage/apiManager.py"
    ]

    for file_path in files_to_backup:
        if os.path.exists(file_path):
            shutil.copy2(file_path, backup_dir / os.path.basename(file_path))

    print(f"✅ Sauvegarde créée dans {backup_dir}")
    return backup_dir


def run_tests():
    """Lance tous les tests"""
    print("🧪 Lancement des tests...")

    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/", "-v", "--tb=short"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ Tests échoués:")
        print(result.stdout)
        print(result.stderr)
        return False

    print("✅ Tous les tests sont passés")
    return True


def setup_production_config():
    """Configure l'environnement de production"""
    print("⚙️ Configuration de l'environnement de production...")

    # Créer les répertoires nécessaires
    dirs_to_create = ["logs", "cache", "backups"]
    for dir_name in dirs_to_create:
        Path(dir_name).mkdir(exist_ok=True)

    # Charger la config production si elle existe
    prod_config_path = Path("config/production.yaml")
    if prod_config_path.exists():
        with open(prod_config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Créer le répertoire de logs si spécifié
        log_file = Path(config.get('logging', {}).get('file', 'logs/wikimedia_access.log'))
        log_file.parent.mkdir(parents=True, exist_ok=True)

    print("✅ Configuration production appliquée")


def validate_deployment():
    """Valide le déploiement"""
    print("✅ Validation du déploiement...")

    try:
        # Test d'import
        from WikimediaManagerPackage.WikimediaAccess import WikimediaAccess
        from WikimediaManagerPackage.exceptions import WikimediaAccessError
        from WikimediaManagerPackage.metrics import metrics_collector

        # Test simple de fonctionnement
        with WikimediaAccess("Q762", log_level="WARNING") as wma:
            health = wma.get_health_status()

            if health['status'] != 'healthy':
                print(f"❌ Health check échoué: {health}")
                return False

        print("✅ Déploiement validé")
        return True

    except Exception as e:
        print(f"❌ Erreur lors de la validation: {e}")
        return False


def main():
    """Processus de déploiement principal"""
    print("🚀 Début du déploiement WikimediaAccess amélioré")

    try:
        # 1. Sauvegarde
        backup_dir = backup_current_version()

        # 2. Tests
        if not run_tests():
            print("❌ Déploiement annulé à cause des tests échoués")
            return False

        # 3. Configuration
        setup_production_config()

        # 4. Validation
        if not validate_deployment():
            print("❌ Validation échouée")
            return False

        print("🎉 Déploiement réussi!")
        print(f"💾 Sauvegarde disponible dans: {backup_dir}")

        return True

    except Exception as e:
        print(f"❌ Erreur critique durant le déploiement: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)