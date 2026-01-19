# Application d'Enrichissement Wikidata - Version Améliorée

## Nouvelles Fonctionnalités

### ✨ Extracteurs Modulaires
- **Système de plugins** : Les extracteurs sont chargés dynamiquement depuis le dossier `extractors/`
- **Choix de l'extracteur** : Possibilité de choisir quel extracteur utiliser pour chaque URL ou liste
- **Extracteur spécialisé** : Extracteur pour le Musée des Beaux-Arts de Rennes inclus

### 💾 Cache Wikidata Permanent
- Toutes les requêtes Wikidata sont mises en cache
- Cache persistent entre les sessions
- Accélération importante des traitements répétitifs
- Statistiques de cache disponibles

### 🎨 Extracteur Musée de Rennes
Extracteur spécialisé pour `collections.mba.rennes.fr` qui extrait :
- Type d'objet et domaine
- Créateur avec dates de naissance/mort
- Titre de l'œuvre
- Date de création
- Matériaux
- Dimensions (hauteur, largeur)
- Concepts clés / mots-clés
- Personnes représentées
- Image de l'œuvre

### 🔍 Mapping Automatique des Concepts
- Les mots-clés sont automatiquement recherchés dans Wikidata
- Les personnes représentées sont matchées avec leurs entités Wikidata
- Le créateur est recherché avec ses dates de vie

## Structure des Fichiers

```
wikidata_enrichment/
├── app.py                          # Application Flask principale
├── base_extractor.py               # Classe de base pour les extracteurs
├── extractor_manager.py            # Gestionnaire d'extracteurs
├── wikidata_enricher.py            # Interface Wikidata avec cache
├── wikidata_cache.py               # Système de cache
├── requirements.txt                # Dépendances Python
├── extractors/                     # Dossier des extracteurs
│   ├── __init__.py
│   ├── generic_extractor.py       # Extracteur par défaut
│   └── rennes_museum_extractor.py # Extracteur Musée de Rennes
├── templates/
│   ├── index.html                  # Interface principale
│   └── config.html                 # Configuration
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── data/
    ├── single_url_history.json    # Historique URLs unitaires
    ├── wikidata_cache/            # Cache Wikidata
    │   └── wikidata_cache.json
    └── list_processing/           # États de traitement
        └── [nom_liste]_state.json
```

## Installation

### 1. Créer la structure

```bash
# Créer les dossiers nécessaires
mkdir -p templates static/css static/js data/wikidata_cache extractors
```

### 2. Placer les fichiers

**Racine :**
- `app.py`
- `base_extractor.py`
- `extractor_manager.py`
- `wikidata_enricher.py`
- `wikidata_cache.py`
- `requirements.txt`

**extractors/ :**
- `__init__.py`
- `generic_extractor.py`
- `rennes_museum_extractor.py`

**templates/ :**
- `index.html`
- `config.html`

**static/css/ :**
- `style.css`

**static/js/ :**
- `main.js`

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Lancer l'application

```bash
python app.py
```

Accéder à : http://localhost:5000

## Utilisation

### 1. Configuration
- Aller dans "Configuration"
- Entrer vos identifiants Wikidata

### 2. Traiter une URL unique

**Sans choix d'extracteur :**
- L'extracteur approprié sera sélectionné automatiquement

**Avec choix d'extracteur :**
- Sélectionner l'extracteur dans le menu déroulant
- Entrer l'URL
- Cliquer sur "Traiter"

### 3. Traiter une liste d'URLs

**Créer un fichier texte :**
```
https://collections.mba.rennes.fr/ark:/10946/0021068
https://collections.mba.rennes.fr/ark:/10946/0012345
# Les lignes avec # sont des commentaires
```

**Charger et traiter :**
- Choisir l'extracteur (optionnel)
- Charger le fichier
- La liste sera traitée séquentiellement

### 4. Validation des correspondances

Lorsqu'une URL est traitée :

1. **Informations extraites** s'affichent
2. **Correspondances Wikidata** proposées pour :
   - L'œuvre/artiste principal
   - Le créateur
   - Les personnes représentées
   - Les concepts/mots-clés

3. **Validation** :
   - Sélectionner une entité existante
   - Ou créer une nouvelle entité
   - Valider les propriétés à ajouter

4. **Passage automatique** à l'URL suivante (mode liste)

## Créer un Nouvel Extracteur

### 1. Créer le fichier

Créer `extractors/mon_extracteur.py` :

```python
from base_extractor import BaseContentExtractor
from bs4 import BeautifulSoup
from typing import Dict

class MonExtracteur(BaseContentExtractor):
    name = "Mon Extracteur"
    description = "Description de mon extracteur"
    supported_domains = ["monsite.com"]
    
    def can_handle(self, url: str, soup: BeautifulSoup = None) -> bool:
        """Vérifier si l'URL peut être traitée"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc in self.supported_domains
    
    def extract(self, url: str, soup: BeautifulSoup) -> Dict:
        """Extraire les informations"""
        info = {
            'type': 'painting',  # ou 'artist'
            'url': url,
            'extractor': self.name,
            'title': '',
            'creator': '',
            # ... autres champs
        }
        
        # Extraire les informations depuis soup
        h1 = soup.find('h1')
        if h1:
            info['title'] = h1.get_text().strip()
        
        # ... extraction personnalisée
        
        return info
```

### 2. Redémarrer l'application

L'extracteur sera automatiquement chargé au démarrage.

## Exemple : Musée de Rennes

**URL d'exemple :**
```
https://collections.mba.rennes.fr/ark:/10946/0021068
```

**Informations extraites :**
- Type : Tableau
- Domaine : Peinture
- Créateur : TOUDOUZE Edouard (1848-1907)
- Titre : Duguesclin sur son lit de mort
- Date : 1904
- Matière : Toile
- Dimensions : H. 550 cm × L. 780 cm
- Concepts : scène historique, cadavre, lit, dais, etc.
- Personne représentée : Bertrand Du Guesclin

**Mapping Wikidata :**
- Créateur → recherché avec dates (1848-1907)
- Bertrand Du Guesclin → Q202422
- Tous les concepts → entités Wikidata correspondantes

## Cache Wikidata

### Avantages
- Réduction du nombre de requêtes API
- Accélération des traitements
- Fonctionnement offline pour données déjà en cache

### Statistiques

Accéder à : `GET /cache_stats`

Retourne :
```json
{
  "total_entries": 125,
  "cache_file": "data/wikidata_cache/wikidata_cache.json",
  "size_bytes": 458362
}
```

### Vider le cache

Si nécessaire, supprimer le fichier :
```bash
rm data/wikidata_cache/wikidata_cache.json
```

## API Routes

### Extracteurs
- `GET /list_extractors` - Liste des extracteurs disponibles
- `GET /cache_stats` - Statistiques du cache

### Traitement
- `POST /process_url` - Traiter une URL
  ```json
  {
    "url": "https://...",
    "extractor": "Musée de Rennes"  // optionnel
  }
  ```

- `POST /upload_list` - Charger une liste
- `POST /process_list_item` - Traiter un élément
- `POST /validate_match` - Valider une correspondance
- `POST /create_entity` - Créer une entité

## Propriétés Wikidata Supportées

### Peintures
- P31 : instance de
- P170 : créateur (avec mapping automatique)
- P571 : date de création
- P186 : matériau
- P2048 : hauteur
- P2049 : largeur
- P180 : représente (depicts - avec mapping automatique)
- P195 : collection

### Artistes
- P31 : instance de
- P106 : occupation
- P569 : date de naissance
- P570 : date de mort
- P135 : mouvement

## Développement

### Ajouter un extracteur
1. Hériter de `BaseContentExtractor`
2. Implémenter `can_handle()` et `extract()`
3. Placer dans `extractors/`
4. Redémarrer l'app

### Personnaliser le cache
Modifier `wikidata_cache.py` pour :
- Changer la durée de vie des entrées
- Ajouter un nettoyage automatique
- Exporter/importer le cache

## Dépannage

### L'extracteur ne se charge pas
- Vérifier que le fichier est dans `extractors/`
- Vérifier qu'il hérite de `BaseContentExtractor`
- Voir les messages de démarrage de l'app

### Cache trop volumineux
- Vider le cache : `rm data/wikidata_cache/wikidata_cache.json`
- Implémenter un nettoyage périodique

### Erreurs d'extraction
- Vérifier les logs de l'extracteur
- Tester avec l'extracteur générique
- Améliorer les patterns regex

## Licence

Projet éducatif - Adaptez selon vos besoins

## Contact

Pour signaler des bugs ou proposer des améliorations, créez une issue.
