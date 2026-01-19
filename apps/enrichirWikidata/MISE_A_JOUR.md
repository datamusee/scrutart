# Guide de Mise à Jour - Corrections SSL et Interface

## Problèmes Corrigés

### ✅ 1. Erreur SSL Certificate
**Symptôme:** `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed`

**Solution:** 
- Ajout de `verify=False` dans les requêtes HTTP
- Désactivation des warnings SSL avec urllib3
- Les certificats auto-signés sont maintenant acceptés

### ✅ 2. Interface de Sélection d'Extracteur
**Nouveau:**
- Menu déroulant pour choisir l'extracteur (URL unique)
- Menu déroulant pour choisir l'extracteur (liste d'URLs)
- Détection automatique si aucun extracteur n'est choisi
- Badge affichant l'extracteur utilisé dans les résultats

### ✅ 3. Affichage Amélioré des Résultats
**Nouveau:**
- Section "Créateur" avec entité Wikidata
- Section "Personnes représentées" avec mapping
- Section "Concepts et Mots-clés" avec mapping Wikidata
- Meilleure présentation visuelle

## Fichiers à Remplacer

### Fichiers Principaux (téléchargez les nouvelles versions)
1. ✅ `base_extractor.py` - Correction SSL
2. ✅ `index.html` - Nouvelle interface
3. ✅ `style.css` - Nouveaux styles

### Fichiers Identiques (pas de changement)
- `app.py`
- `extractor_manager.py`
- `wikidata_enricher.py`
- `wikidata_cache.py`
- `rennes_museum_extractor.py`
- `generic_extractor.py`
- `config.html`
- `main.js`

## Installation des Corrections

### Option 1: Remplacer les fichiers modifiés
```bash
# Sauvegarder les anciennes versions (optionnel)
mv base_extractor.py base_extractor.py.old
mv templates/index.html templates/index.html.old
mv static/css/style.css static/css/style.css.old

# Télécharger et placer les nouveaux fichiers
# - base_extractor.py → racine
# - index.html → templates/
# - style.css → static/css/
```

### Option 2: Réinstallation complète
Si vous préférez tout réinstaller :
```bash
# Sauvegarder votre config et cache
cp config.json config.json.backup
cp -r data data.backup

# Supprimer l'ancienne installation
rm -rf *

# Réinstaller tous les fichiers
# ... puis restaurer
cp config.json.backup config.json
cp -r data.backup/* data/
```

## Test de l'Extracteur Rennes

Un script de test est inclus : `test_rennes.py`

```bash
python test_rennes.py
```

Ce script va :
1. Tester l'URL exemple du Musée de Rennes
2. Afficher toutes les informations extraites
3. Sauvegarder le résultat dans `test_rennes_result.json`

**Résultat attendu :**
```
Type: painting
Titre: Duguesclin sur son lit de mort
Type d'objet: Tableau
Domaine: Peinture

Créateur: TOUDOUZE Edouard
  Naissance: 1848
  Mort: 1907

Date de création: 1904
Matériau: Toile
Hauteur: 550 cm
Largeur: 780 cm

Mots-clés: scène historique, cadavre, lit, dais, ...
Personnes représentées: Bertrand Du Guesclin
```

## Vérification Post-Installation

### 1. Test de l'Interface
```bash
python app.py
```

Ouvrir : http://localhost:5000

✅ Vérifier que :
- Les menus déroulants d'extracteurs sont visibles
- L'option "Auto (détection automatique)" est présente
- Les autres extracteurs sont listés

### 2. Test de l'URL Rennes
Dans l'interface :
1. Entrer : `https://collections.mba.rennes.fr/ark:/10946/0021068`
2. Choisir "Musée de Rennes" ou laisser "Auto"
3. Cliquer "Traiter"

✅ Vérifier que :
- Pas d'erreur SSL
- Les informations sont extraites
- Le badge "Extracteur: Musée de Rennes" s'affiche
- Les sections Créateur, Personnes, Concepts apparaissent

### 3. Test du Cache
```bash
# Vérifier que le cache se crée
ls -la data/wikidata_cache/

# Traiter plusieurs fois la même URL
# Les requêtes suivantes devraient être en cache
```

Vous devriez voir des messages : `Cache hit pour...`

## Dépannage

### Erreur SSL persiste
Si l'erreur SSL persiste :

1. Vérifier que `urllib3` est installé :
```bash
pip install urllib3
```

2. Vérifier que `base_extractor.py` contient :
```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

3. Vérifier la méthode `fetch_page()` :
```python
response = requests.get(url, timeout=10, verify=False)
```

### Menu déroulant vide
Si les extracteurs ne s'affichent pas :

1. Vérifier que le dossier `extractors/` existe
2. Vérifier que les fichiers sont dedans :
```bash
ls -la extractors/
# Doit contenir : __init__.py, rennes_museum_extractor.py, generic_extractor.py
```

3. Regarder les logs au démarrage de l'app :
```bash
python app.py
# Doit afficher : "X extracteur(s) chargé(s)"
```

### Styles cassés
Si les styles ne s'appliquent pas :

1. Vider le cache du navigateur (Ctrl+Shift+R)
2. Vérifier que `style.css` est dans `static/css/`
3. Vérifier les logs du navigateur (F12)

## Nouvelles Fonctionnalités

### 1. Sélection d'Extracteur
```html
<select id="extractor-select-single">
    <option value="">Auto (détection automatique)</option>
    <option value="Musée de Rennes">Musée de Rennes - ...</option>
    <option value="Extracteur Générique">Extracteur Générique - ...</option>
</select>
```

### 2. Mapping de Concepts
Lorsqu'un mot-clé est trouvé dans Wikidata :
```
scène historique → Scène de genre (Q1358372)
cadavre → Cadavre (Q48422)
Bertrand Du Guesclin → Bertrand du Guesclin (Q202422)
```

### 3. Cache Wikidata
Toutes les requêtes sont cachées pour :
- Accélérer les traitements répétitifs
- Réduire la charge sur l'API Wikidata
- Permettre un fonctionnement offline (données déjà en cache)

Voir les stats : http://localhost:5000/cache_stats

## Support

Si vous rencontrez des problèmes :

1. Vérifier les logs de la console Python
2. Vérifier la console du navigateur (F12)
3. Tester avec le script `test_rennes.py`
4. Vérifier que tous les fichiers sont bien placés

## Prochaines Étapes

Une fois l'installation vérifiée :

1. ✅ Tester avec votre propre URL Rennes
2. ✅ Créer votre propre extracteur (voir README.md)
3. ✅ Traiter une liste d'URLs
4. ✅ Explorer les mappings Wikidata

Profitez bien de l'application améliorée ! 🎨
