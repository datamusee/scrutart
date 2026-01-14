# Piwigo Deduplicator - Outil de gestion des doublons

Application Flask pour identifier et supprimer les images en double dans vos galeries Piwigo.

## 🎯 Fonctionnalités

- **Connexion à Piwigo** : Se connecte à votre site Piwigo via l'API
- **Analyse intelligente** : Détecte les images ayant le même créateur et le même titre
- **Interface visuelle** : Compare les images côte à côte pour faciliter le choix
- **Suppression sélective** : Choisissez quelles images garder ou supprimer
- **Traçabilité complète** : Journal JSON de toutes les opérations effectuées
- **Gestion des albums traités** : Évite de retraiter les mêmes albums
- **Statistiques en temps réel** : Vue d'ensemble des opérations effectuées

## 📋 Prérequis

- Python 3.7 ou supérieur
- Un site Piwigo avec accès administrateur
- Connexion Internet

## 🚀 Installation

1. **Cloner ou télécharger le projet**
```bash
cd piwigo_deduplicator
```

2. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

3. **Lancer l'application**
```bash
python app.py
```

4. **Ouvrir dans le navigateur**
```
http://localhost:5000
```

## 📖 Utilisation

### 1. Configuration initiale

Au premier lancement, configurez votre connexion Piwigo :

- **URL du site** : L'adresse complète de votre galerie Piwigo (ex: `https://photos.exemple.com`)
- **Nom d'utilisateur** : Votre identifiant administrateur
- **Mot de passe** : Votre mot de passe
- **Retraiter les albums** : Cochez pour analyser à nouveau les albums déjà traités

Cliquez sur "Enregistrer et tester la connexion" pour valider.

### 2. Charger les albums

Une fois connecté, vous avez deux options :

- **Charger les albums** : Affiche la liste des albums disponibles pour sélection manuelle
- **Parcourir tous les albums** : Scanne automatiquement tous les albums et traite tous les doublons d'un seul coup

Les albums déjà traités apparaissent en vert et peuvent être ignorés (sauf si vous avez coché "Retraiter les albums").

### 3. Analyser les albums

#### Option A : Album par album
Cliquez sur un album pour l'analyser individuellement.

#### Option B : Tous les albums automatiquement
Cliquez sur "🚀 Parcourir tous les albums" pour :
- Récupérer la liste de tous les albums non traités
- **Traiter les albums un par un de manière séquentielle** :
  1. Charge le premier album
  2. Scanne et affiche ses doublons
  3. Vous traitez les doublons (valider/passer)
  4. Une fois l'album terminé, passe automatiquement au suivant
  5. Continue jusqu'à ce que tous les albums soient traités
- Afficher la progression (album X/Y)
- Marquer automatiquement chaque album comme traité

**Avantage** : Pas besoin de retourner à la liste des albums entre chaque traitement, le processus est continu et automatique.

L'application va :
- Récupérer toutes les images de chaque album
- Extraire le créateur depuis la description (champ "Créateur" dans une balise `<a>`)
- Identifier les images avec le même créateur ET le même titre
- Afficher les doublons trouvés

### 4. Traiter les doublons

Pour chaque groupe de doublons :

1. **Visualisez les images** côte à côte avec leurs informations (ID, taille, date)
2. **Cochez les images à conserver** (toutes sont cochées par défaut)
3. **Décochez les images à supprimer**
4. Cliquez sur "✓ Valider et passer au suivant" pour :
   - Supprimer les images non cochées
   - Enregistrer l'opération dans le journal
   - Passer au doublon suivant

Vous pouvez aussi cliquer sur "→ Passer sans supprimer" pour ignorer ce groupe.

### 5. Consulter les statistiques

La section "Statistiques" affiche :
- **Albums traités** : Nombre d'albums analysés
- **Doublons trouvés** : Nombre de groupes de doublons identifiés
- **Images supprimées** : Nombre total d'images supprimées

Boutons disponibles :
- **📋 Voir le journal** : Télécharge le fichier JSON complet des opérations
- **🗑️ Réinitialiser le journal** : Efface l'historique (albums à retraiter)

## 🔍 Comment l'outil détecte les doublons

L'application considère deux images comme des doublons si :

1. **Même créateur** : Le champ "Créateur" dans la description est identique
2. **Même titre** : Le titre de l'image est identique

### Format de la description

Le créateur doit être indiqué dans la description de l'image, idéalement dans une balise HTML `<a>` :

```html
Créateur: <a href="#">Nom du Créateur</a>
```

ou en texte simple :

```
Créateur: Nom du Créateur
```

Exemples valides :
- `Créateur: <a href="/tag/123">Jean Dupont</a>`
- `Créateur : <a>Marie Martin</a>`
- `Photo de paysage - Créateur: <a href="#">Pierre Durant</a>`
- `Créateur: Sophie Leblanc` (sans balise HTML, fonctionne aussi)

**Note** : La balise `<a>` est souvent ajoutée automatiquement par Piwigo quand vous utilisez des tags ou des liens.

## 📁 Fichiers de données

### config.json
Stocke votre configuration Piwigo (créé automatiquement) :
```json
{
  "piwigo_url": "https://photos.exemple.com",
  "username": "admin",
  "password": "votre_mot_de_passe",
  "reprocess_albums": false
}
```

### trace.json
Journal complet des opérations (créé automatiquement) :
```json
{
  "processed_albums": [123, 456, 789],
  "operations": [
    {
      "timestamp": "2026-01-14T10:30:00",
      "type": "scan",
      "data": {
        "album_id": 123,
        "duplicates_found": 5,
        "total_images": 15
      }
    },
    {
      "timestamp": "2026-01-14T10:35:00",
      "type": "delete",
      "data": {
        "album_id": 123,
        "deleted": [{"image_id": 456, "success": true}],
        "kept": [457, 458],
        "failed": []
      }
    }
  ]
}
```

## ⚙️ API Piwigo utilisée

L'application utilise les méthodes suivantes de l'API Piwigo :

- `pwg.session.login` : Authentification
- `pwg.session.getStatus` : Récupération du token
- `pwg.categories.getList` : Liste des albums
- `pwg.categories.getImages` : Images d'un album
- `pwg.images.delete` : Suppression d'images

## 🛡️ Sécurité

- Les mots de passe sont stockés localement dans `config.json`
- Ne partagez jamais votre fichier `config.json`
- L'application ne communique qu'avec votre site Piwigo
- Toutes les suppressions sont tracées dans `trace.json`

## 🐛 Dépannage

### Erreur de connexion
- Vérifiez l'URL de votre site (sans / à la fin)
- Vérifiez vos identifiants
- Assurez-vous que l'API Piwigo est activée

### Aucun album ne s'affiche
- Vérifiez que vous avez des albums
- Décochez "Retraiter les albums" si tous sont déjà traités
- Vérifiez les permissions de votre compte

### Les doublons ne sont pas détectés

C'est le problème le plus courant. Utilisez les outils de débogage :

#### 1. Exporter les données d'un album
```bash
python test_api.py
```
Ce script va :
- Tester votre connexion Piwigo
- Lister vos albums
- Exporter les données d'un album en JSON

#### 2. Analyser pourquoi les doublons ne sont pas détectés
```bash
python debug_duplicates.py
```
Ce script va :
- Tester l'extraction du créateur avec différents formats
- Analyser vos données réelles
- Montrer exactement ce qui est détecté ou pas

#### Causes fréquentes :
- Les descriptions ne contiennent pas "Créateur:" (attention à la casse)
- Les créateurs sont dans des balises HTML complexes
- Les titres ne sont pas exactement identiques (espaces, majuscules)
- Les créateurs ne sont pas exactement identiques

#### Solutions :
1. Vérifiez le format exact dans vos descriptions Piwigo
2. Utilisez `test_api.py` pour exporter un album problématique
3. Utilisez `debug_duplicates.py` pour analyser le fichier JSON exporté
4. Ajustez les descriptions dans Piwigo si nécessaire

### Erreur lors de la suppression
- Vérifiez les permissions de votre compte
- L'image existe peut-être encore dans d'autres albums
- Consultez le fichier `trace.json` pour plus de détails
- Regardez les logs Python dans le terminal

## 📝 Notes importantes

- **Sauvegarde recommandée** : Faites une sauvegarde de votre base Piwigo avant utilisation
- **Test sur un album** : Testez d'abord sur un petit album
- **Suppressions définitives** : Les images supprimées ne peuvent pas être récupérées via l'application
- **Un doublon à la fois** : L'interface affiche et traite un groupe de doublons à la fois

## 🎨 Personnalisation

Vous pouvez modifier :
- Le port d'écoute dans `app.py` (ligne `app.run(port=5000)`)
- Les styles CSS dans `templates/index.html`
- La logique de détection dans la méthode `find_duplicates()`

## 📞 Support

Pour toute question ou problème :
1. Vérifiez la section Dépannage
2. Consultez les logs Python dans le terminal
3. Examinez le fichier `trace.json` pour les détails des opérations

## 📄 Licence

Cet outil est fourni "tel quel" sans garantie. Utilisez-le à vos risques et périls.

---

**Bon nettoyage de vos galeries Piwigo ! 🖼️✨**
