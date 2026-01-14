# 🚀 Démarrage Rapide - Piwigo Deduplicator

## Installation en 3 étapes

### 1. Installer les dépendances
```bash
cd piwigo_deduplicator
pip install -r requirements.txt
```

### 2. Lancer l'application
```bash
python app.py
```

### 3. Ouvrir dans le navigateur
```
http://localhost:5000
```

## ⚡ Utilisation Express

### Mode standard (album par album)
1. **Configurer** : Entrez l'URL de votre site Piwigo et vos identifiants
2. **Charger** : Cliquez sur "Charger les albums"
3. **Sélectionner** : Cliquez sur un album à analyser
4. **Traiter** : Décochez les images à supprimer, validez

### Mode automatique (tous les albums) 🆕
1. **Configurer** : Entrez l'URL de votre site Piwigo et vos identifiants
2. **Lancer** : Cliquez sur "🚀 Parcourir tous les albums"
3. **Traiter** : Les albums sont chargés et traités un par un automatiquement
   - L'album actuel est scanné
   - Ses doublons sont affichés
   - Vous validez ou passez les doublons
   - L'album suivant est chargé automatiquement
4. **Continuer** jusqu'à ce que tous les albums soient traités

### Mode débogage (si aucun doublon n'est trouvé) 🆕
```bash
python test_api.py           # Exporter les données d'un album
python debug_duplicates.py   # Analyser pourquoi pas de doublons
```
Consultez `GUIDE_DEBOGAGE.md` pour les détails.

## 📋 Ce que fait l'application

- ✅ Trouve les images avec le même créateur et le même titre
- ✅ Extrait le créateur depuis la balise `<a>` ou le texte simple
- ✅ Les affiche côte à côte pour comparaison
- ✅ Supprime les images que vous ne cochez pas
- ✅ Garde une trace complète dans `trace.json`
- ✅ Mémorise les albums déjà traités
- ✅ Mode automatique pour traiter tous les albums d'un coup

## ⚠️ Important

- Le **créateur** doit être dans la description : 
  - `Créateur: <a href="#">Nom</a>` (idéal)
  - `Créateur: Nom` (fonctionne aussi)
- Les images doivent avoir le **même titre exact**
- Faites une **sauvegarde** avant de commencer !

## 🔍 Si aucun doublon n'est trouvé

Utilisez les outils de débogage :
```bash
python test_api.py        # Voir vos données réelles
python debug_duplicates.py  # Analyser pourquoi pas de doublons
```
Consultez `GUIDE_DEBOGAGE.md` pour un diagnostic complet.

## 🔧 Configuration Piwigo

Assurez-vous que :
- L'API Piwigo est activée
- Votre compte a les droits administrateur
- Les descriptions d'images contiennent bien "Créateur:"

## 📁 Fichiers générés

- `config.json` : Votre configuration (à ne pas partager)
- `trace.json` : Journal de toutes les opérations

## 🆘 Problème ?

Consultez le `README.md` complet pour le dépannage détaillé.

---

**Prêt à nettoyer vos doublons ! 🎯**
