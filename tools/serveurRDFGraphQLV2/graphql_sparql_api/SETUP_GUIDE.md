# Guide de Configuration

## Installation rapide

1. Cloner le projet
2. Créer l'environnement virtuel: `python -m venv venv`
3. Activer: `source venv/bin/activate`
4. Installer: `pip install -r requirements.txt`
5. Configurer: `cp .env.example .env` et éditer
6. Démarrer: `python app.py`

## Configuration Google OAuth

1. Aller sur https://console.cloud.google.com
2. Créer un projet
3. Activer Google+ API
4. Créer des identifiants OAuth 2.0
5. Ajouter l'URI de redirection: http://localhost:5000/auth/callback
6. Copier Client ID et Secret dans .env

## Tests

```bash
pytest tests/ -v
```

Pour plus de détails, voir README.md
