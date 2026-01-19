# Structure Complète du Projet

## 📁 Arborescence

```
wikidata_enrichment/
│
├── 📄 app.py                          # Application Flask principale
├── 📄 base_extractor.py               # Classe de base pour extracteurs (MODIFIÉ)
├── 📄 extractor_manager.py            # Gestionnaire d'extracteurs
├── 📄 wikidata_enricher.py            # Interface Wikidata avec cache
├── 📄 wikidata_cache.py               # Système de cache permanent
├── 📄 requirements.txt                # Dépendances Python
├── 📄 README.md                       # Documentation principale
├── 📄 MISE_A_JOUR.md                  # Guide de mise à jour
├── 📄 FICHIERS.md                     # Ce fichier
├── 📄 test_rennes.py                  # Script de test
│
├── 📁 extractors/                     # Dossier des extracteurs
│   ├── 📄 __init__.py
│   ├── 📄 generic_extractor.py        # Extracteur par défaut
│   └── 📄 rennes_museum_extractor.py  # Extracteur Musée de Rennes
│
├── 📁 templates/                      # Templates HTML
│   ├── 📄 index.html                  # Interface principale (MODIFIÉ)
│   └── 📄 config.html                 # Page de configuration
│
├── 📁 static/                         # Fichiers statiques
│   ├── 📁 css/
│   │   └── 📄 style.css               # Styles CSS (MODIFIÉ)
│   └── 📁 js/
│       └── 📄 main.js                 # JavaScript
│
└── 📁 data/                           # Données (créé automatiquement)
    ├── 📄 config.json                 # Configuration (créé auto)
    ├── 📄 single_url_history.json     # Historique URLs (créé auto)
    ├── 📁 wikidata_cache/             # Cache Wikidata
    │   └── 📄 wikidata_cache.json     # Fichier de cache (créé auto)
    └── 📁 list_processing/            # États de traitement
        └── 📄 [nom]_state.json        # États des listes (créé auto)
```

## 📥 Fichiers à Télécharger et Placer

### 🔴 RACINE du projet

| Fichier | Obligatoire | Description |
|---------|-------------|-------------|
| `app.py` | ✅ OUI | Application Flask |
| `base_extractor.py` | ✅ OUI | Classe de base (avec fix SSL) |
| `extractor_manager.py` | ✅ OUI | Gestion des extracteurs |
| `wikidata_enricher.py` | ✅ OUI | Interface Wikidata |
| `wikidata_cache.py` | ✅ OUI | Système de cache |
| `requirements.txt` | ✅ OUI | Dépendances |
| `README.md` | 📘 Recommandé | Documentation |
| `MISE_A_JOUR.md` | 📘 Recommandé | Guide de migration |
| `test_rennes.py` | 🧪 Optionnel | Script de test |

### 🔴 extractors/

| Fichier | Obligatoire | Description |
|---------|-------------|-------------|
| `__init__.py` | ✅ OUI | Fichier module Python |
| `generic_extractor.py` | ✅ OUI | Extracteur par défaut |
| `rennes_museum_extractor.py` | ✅ OUI | Extracteur Rennes |

### 🔴 templates/

| Fichier | Obligatoire | Description |
|---------|-------------|-------------|
| `index.html` | ✅ OUI | Interface principale (avec sélecteur) |
| `config.html` | ✅ OUI | Page de configuration |

### 🔴 static/css/

| Fichier | Obligatoire | Description |
|---------|-------------|-------------|
| `style.css` | ✅ OUI | Styles CSS (avec nouveaux styles) |

### 🔴 static/js/

| Fichier | Obligatoire | Description |
|---------|-------------|-------------|
| `main.js` | ⚠️ Optionnel | JavaScript (peut être vide) |

## 🔧 Fichiers Modifiés (Corrections)

Ces 3 fichiers ont été modifiés pour corriger les problèmes :

### 1. `base_extractor.py`
**Changements :**
- ✅ Ajout de `import urllib3`
- ✅ Ajout de `urllib3.disable_warnings()`
- ✅ Ajout de `verify=False` dans `requests.get()`

**Ligne critique :**
```python
response = requests.get(url, timeout=10, verify=False)
```

### 2. `index.html`
**Changements :**
- ✅ Ajout des menus déroulants d'extracteurs
- ✅ Fonction `loadExtractors()` pour charger la liste
- ✅ Nouvelles sections : Créateur, Personnes, Concepts
- ✅ Badge affichant l'extracteur utilisé
- ✅ Meilleur affichage des mappings Wikidata

**Nouveaux éléments :**
```html
<select id="extractor-select-single">
    <option value="">Auto (détection automatique)</option>
</select>
```

### 3. `style.css`
**Changements :**
- ✅ Styles pour `.extractor-select`
- ✅ Styles pour `.extractor-badge`
- ✅ Styles pour `.concept-item`, `.concept-match`, etc.
- ✅ Amélioration des `.match-card`
- ✅ Styles responsive

**Nouveaux styles :**
```css
.extractor-badge { ... }
.concept-item { ... }
.concept-match { ... }
```

## 📦 Installation Depuis Zéro

### Étape 1: Créer la structure
```bash
mkdir -p wikidata_enrichment
cd wikidata_enrichment
mkdir -p extractors templates static/css static/js data/wikidata_cache
```

### Étape 2: Télécharger les fichiers
Télécharger tous les fichiers listés ci-dessus et les placer dans les bons dossiers.

### Étape 3: Installer les dépendances
```bash
pip install -r requirements.txt
```

### Étape 4: Lancer
```bash
python app.py
```

## 🔍 Vérification de l'Installation

### Checklist Complète

#### Racine (9 fichiers)
- [ ] `app.py` existe
- [ ] `base_extractor.py` existe (avec fix SSL)
- [ ] `extractor_manager.py` existe
- [ ] `wikidata_enricher.py` existe
- [ ] `wikidata_cache.py` existe
- [ ] `requirements.txt` existe
- [ ] `README.md` existe
- [ ] `MISE_A_JOUR.md` existe
- [ ] `test_rennes.py` existe

#### extractors/ (3 fichiers)
- [ ] `__init__.py` existe
- [ ] `generic_extractor.py` existe
- [ ] `rennes_museum_extractor.py` existe

#### templates/ (2 fichiers)
- [ ] `index.html` existe (nouvelle version)
- [ ] `config.html` existe

#### static/css/ (1 fichier)
- [ ] `style.css` existe (nouvelle version)

#### static/js/ (1 fichier)
- [ ] `main.js` existe (peut être vide)

### Test Rapide
```bash
# Tester le chargement des extracteurs
python -c "from extractor_manager import ExtractorManager; m=ExtractorManager('extractors'); print(f'{len(m.extractors)} extracteur(s)')"

# Devrait afficher : "2 extracteur(s)" ou plus
```

## 🆘 Dépannage

### Problème : ImportError
**Solution :** Vérifier que tous les fichiers Python sont bien dans la racine

### Problème : Extracteurs non chargés
**Solution :** Vérifier le dossier `extractors/` et ses fichiers

### Problème : Templates non trouvés
**Solution :** Vérifier que les HTML sont dans `templates/`

### Problème : CSS ne s'applique pas
**Solution :** Vérifier que `style.css` est dans `static/css/`

## 📊 Taille des Fichiers (Approximative)

| Fichier | Taille |
|---------|--------|
| app.py | ~12 KB |
| base_extractor.py | ~3 KB |
| extractor_manager.py | ~5 KB |
| wikidata_enricher.py | ~8 KB |
| wikidata_cache.py | ~5 KB |
| rennes_museum_extractor.py | ~10 KB |
| generic_extractor.py | ~6 KB |
| index.html | ~15 KB |
| config.html | ~2 KB |
| style.css | ~6 KB |
| main.js | ~2 KB |

**Total :** ~75 KB pour tout le code source

## ✅ Version Finale

Cette structure représente la version finale et complète de l'application avec :
- ✅ Support SSL corrigé
- ✅ Interface de sélection d'extracteur
- ✅ Extracteur Musée de Rennes fonctionnel
- ✅ Cache Wikidata permanent
- ✅ Mapping automatique des concepts
- ✅ Tests inclus

Tous les fichiers sont téléchargeables individuellement !
