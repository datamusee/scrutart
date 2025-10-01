# Configuration Google OAuth (Optionnel)

## Étapes pour configurer Google OAuth :

1. **Aller sur Google Cloud Console**
   - https://console.cloud.google.com/

2. **Créer un projet** (si nécessaire)

3. **Activer Google+ API**
   - APIs & Services → Library
   - Rechercher "Google+ API" et l'activer

4. **Créer des credentials OAuth 2.0**
   - APIs & Services → Credentials
   - Create Credentials → OAuth 2.0 Client ID
   - Application type: Web application
   - Name: Wikidata Artist Search
   - Authorized redirect URIs: http://localhost:5000/auth

5. **Récupérer Client ID et Client Secret**

6. **Configurer les variables d'environnement**
```bash
   export GOOGLE_CLIENT_ID="votre-client-id.googleusercontent.com"
   export GOOGLE_CLIENT_SECRET="votre-client-secret"
   export SECRET_KEY="votre-clé-secrète-super-sécurisée"