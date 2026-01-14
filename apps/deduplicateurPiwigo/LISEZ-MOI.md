# 🖼️ Piwigo Deduplicator - Bienvenue !

## 📦 Contenu du package

Vous avez téléchargé l'outil complet de gestion des doublons pour Piwigo. Voici ce que contient ce package :

### 🚀 Application principale
- **app.py** : Application Flask principale
- **templates/index.html** : Interface web moderne et responsive
- **requirements.txt** : Dépendances Python

### 📚 Documentation
- **README.md** : Documentation complète avec toutes les fonctionnalités
- **DEMARRAGE_RAPIDE.md** : Installation et utilisation en 3 étapes
- **GUIDE_DEBOGAGE.md** : Guide détaillé si aucun doublon n'est détecté
- **EXEMPLES_DESCRIPTIONS.md** : Formats de description supportés
- **CHANGELOG.md** : Liste des améliorations et corrections

### 🔧 Outils de débogage
- **test_api.py** : Teste la connexion et exporte les données d'un album
- **debug_duplicates.py** : Analyse pourquoi les doublons ne sont pas détectés

## ⚡ Démarrage rapide

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer l'application
python app.py

# 3. Ouvrir dans le navigateur
http://localhost:5000
```

## 🎯 Deux modes d'utilisation

### Mode 1 : Album par album
Parcourez vos albums un par un, idéal pour un contrôle précis.

### Mode 2 : Automatique (séquentiel) 🆕
Cliquez sur "🚀 Parcourir tous les albums" pour :
- Charger automatiquement chaque album un par un
- Scanner et afficher les doublons de l'album actuel
- Traiter les doublons
- Passer automatiquement à l'album suivant
- Continuer jusqu'à ce que tous les albums soient traités

**Avantage** : Traitement continu sans avoir à retourner sélectionner manuellement chaque album.

## 🔍 Problème avec la détection ?

Si aucun doublon n'est trouvé alors que vous savez qu'il y en a :

1. **Utilisez test_api.py** pour voir vos données réelles
2. **Utilisez debug_duplicates.py** pour analyser le problème
3. **Consultez GUIDE_DEBOGAGE.md** pour un diagnostic complet

## 📋 Critères de détection

Deux images sont considérées comme doublons si :
1. ✅ Elles ont le **même créateur** (extrait de la description)
2. ✅ Elles ont le **même titre**
3. ✅ Elles sont dans le **même album**

### Format requis dans la description :
```html
Créateur: <a href="#">Nom du Créateur</a>
```
ou simplement :
```
Créateur: Nom du Créateur
```

## 🆕 Nouveautés version 2.1

- ✨ **Traitement séquentiel** : Les albums sont traités un par un automatiquement
- ⚡ **Plus efficace** : Pas besoin de scanner tous les albums d'avance
- 📊 **Progression en temps réel** : Vous voyez quel album est en cours (X/Y)
- 🔄 **Passage automatique** : Quand un album est fini, le suivant se charge automatiquement
- 🔧 Extraction améliorée du créateur (support des balises `<a>`)
- 🐛 Détection améliorée avec normalisation des espaces
- 🔍 Outils de débogage complets (test_api.py, debug_duplicates.py)
- 📊 Logs détaillés dans le terminal
- 📖 Guide de débogage complet

## 📂 Structure du projet

```
piwigo_deduplicator/
├── app.py                      # Application Flask
├── templates/
│   └── index.html             # Interface web
├── requirements.txt           # Dépendances
├── test_api.py               # Outil de test API
├── debug_duplicates.py       # Outil d'analyse
├── README.md                 # Documentation complète
├── DEMARRAGE_RAPIDE.md       # Guide rapide
├── GUIDE_DEBOGAGE.md         # Guide de débogage
├── EXEMPLES_DESCRIPTIONS.md  # Exemples de formats
└── CHANGELOG.md              # Liste des changements
```

## 🎓 Parcours d'utilisation recommandé

### Pour les utilisateurs pressés
1. Lisez **DEMARRAGE_RAPIDE.md**
2. Lancez `python app.py`
3. Utilisez le bouton "🚀 Parcourir tous les albums"

### Pour les utilisateurs qui veulent comprendre
1. Lisez **README.md** pour la documentation complète
2. Consultez **EXEMPLES_DESCRIPTIONS.md** pour le format
3. Lancez `python app.py` et testez album par album

### Si ça ne fonctionne pas
1. Lisez **GUIDE_DEBOGAGE.md**
2. Lancez `python test_api.py` pour exporter vos données
3. Lancez `python debug_duplicates.py` pour analyser
4. Ajustez vos descriptions dans Piwigo

## 💡 Conseils

- 🔒 **Faites une sauvegarde** de votre base Piwigo avant
- 🧪 **Testez sur un petit album** d'abord
- 📝 **Vérifiez le format** de vos descriptions
- 🔍 **Utilisez les outils de debug** si besoin
- 📊 **Consultez les logs** dans le terminal Python

## 🆘 Support

En cas de problème :

1. **Consultez GUIDE_DEBOGAGE.md** - Solutions aux problèmes courants
2. **Utilisez les outils** - test_api.py et debug_duplicates.py
3. **Vérifiez les logs** - Le terminal affiche des infos détaillées
4. **Examinez trace.json** - Historique de toutes les opérations

## 📄 Fichiers générés par l'application

- **config.json** : Votre configuration Piwigo (à ne pas partager)
- **trace.json** : Journal de toutes les opérations
- **album_XXX_images.json** : Export de données (si vous utilisez test_api.py)

## 🌟 Fonctionnalités principales

- ✅ Connexion sécurisée à Piwigo via API
- ✅ Détection intelligente des doublons
- ✅ Interface visuelle pour comparer les images
- ✅ Suppression sélective (cases à cocher)
- ✅ Mode automatique pour tous les albums
- ✅ Traçabilité complète des opérations
- ✅ Gestion des albums déjà traités
- ✅ Statistiques en temps réel
- ✅ Outils de débogage intégrés

## 🚀 C'est parti !

Tout est prêt pour nettoyer vos doublons Piwigo. Commencez par :

```bash
python app.py
```

Puis ouvrez http://localhost:5000 dans votre navigateur.

**Bon nettoyage de vos galeries ! 🎉**

---

*Pour plus d'informations, consultez README.md*
*Pour un démarrage rapide, consultez DEMARRAGE_RAPIDE.md*
*En cas de problème, consultez GUIDE_DEBOGAGE.md*
