# Système de Matchers Wikidata

## Vue d'Ensemble

Les **matchers** sont des modules qui recherchent des correspondances dans Wikidata **sans nécessiter d'authentification**. Ils utilisent SPARQL (WDQS) pour interroger Wikidata et retournent des correspondances avec un score de confiance.

## Différence entre Extracteurs et Matchers

| Aspect | Extracteur | Matcher |
|--------|-----------|---------|
| **Rôle** | Extraire des données d'une URL | Trouver des entités Wikidata correspondantes |
| **Entrée** | URL web | Données extraites |
| **Sortie** | Informations structurées | Entités Wikidata avec scores |
| **Authentification** | Aucune | Aucune (lecture seule) |
| **Technologie** | BeautifulSoup, regex | SPARQL queries |

## Architecture

```
matchers/
├── __init__.py
├── painting_matcher.py      # Matcher pour peintures
└── artist_matcher.py         # Matcher pour artistes

base_matcher.py              # Classe de base
matcher_manager.py           # Gestionnaire de matchers
```

## Fonctionnement

### 1. Extraction → Matching → Enrichissement

```
URL → [Extractor] → Données → [Matcher] → Entités Wikidata → [Validation] → Enrichissement
```

### 2. Flux Détaillé

1. **Extraction** : L'extracteur extrait les données de l'URL
2. **Matching** : Le matcher recherche dans Wikidata via SPARQL
3. **Scoring** : Chaque correspondance reçoit un score de confiance
4. **Présentation** : Les correspondances sont présentées à l'utilisateur
5. **Validation** : L'utilisateur valide ou rejette
6. **Enrichissement** : Nécessite authentification (pas le matcher)

## Matchers Disponibles

### 🎨 Painting Matcher

**Type supporté :** `painting`

**Stratégies de recherche :**
1. **Titre exact** : Recherche par titre exact (confiance: 95%)
2. **Titre partiel** : Recherche par mots-clés du titre (confiance: 70%)
3. **Créateur + Date** : Recherche par créateur et année (confiance: 60-80%)

**Exemple de requête SPARQL :**
```sparql
SELECT DISTINCT ?item ?itemLabel ?creatorLabel ?date ?image WHERE {
  ?item wdt:P31/wdt:P279* wd:Q3305213 .  # instance de peinture
  ?item rdfs:label "Duguesclin sur son lit de mort"@fr .
  OPTIONAL { ?item wdt:P170 ?creator . }
  OPTIONAL { ?item wdt:P571 ?date . }
  OPTIONAL { ?item wdt:P18 ?image . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en" . }
}
```

### 👤 Artist Matcher

**Types supportés :** `artist`, `painter`

**Stratégies de recherche :**
1. **Nom + Dates** : Recherche par nom avec années de naissance/mort (confiance: 85-95%)
2. **Nom seul** : Recherche par nom uniquement (confiance: 60%)

**Exemple de requête SPARQL :**
```sparql
SELECT DISTINCT ?item ?itemLabel ?birth ?death ?image WHERE {
  ?item wdt:P31 wd:Q5 .  # humain
  ?item wdt:P106 ?occupation .
  ?occupation wdt:P279* wd:Q483501 .  # artiste
  ?item rdfs:label ?label .
  FILTER(CONTAINS(LCASE(?label), LCASE("TOUDOUZE")))
  OPTIONAL { ?item wdt:P569 ?birth . FILTER(YEAR(?birth) = 1848) }
  OPTIONAL { ?item wdt:P570 ?death . FILTER(YEAR(?death) = 1907) }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en" . }
}
```

## Scores de Confiance

| Score | Signification | Exemple |
|-------|---------------|---------|
| 0.95-1.0 | Très haute confiance | Titre exact + créateur + date |
| 0.80-0.94 | Haute confiance | Titre exact + créateur OU date |
| 0.60-0.79 | Confiance moyenne | Titre partiel ou créateur seul |
| 0.40-0.59 | Confiance faible | Correspondance approximative |
| < 0.40 | Très faible | À vérifier manuellement |

## Utilisation

### Dans l'Interface Web

1. L'URL est traitée par un extracteur
2. Les matchers trouvent automatiquement des correspondances
3. Les résultats sont affichés avec scores de confiance
4. L'utilisateur sélectionne la bonne entité
5. L'authentification est requise seulement pour l'enrichissement

### En Python

```python
from matcher_manager import MatcherManager

# Initialiser
manager = MatcherManager('matchers')

# Données extraites
data = {
    'type': 'painting',
    'title': 'Duguesclin sur son lit de mort',
    'creator': 'TOUDOUZE Edouard',
    'date': '1904'
}

# Trouver des correspondances
matches = manager.find_matches('painting', data)

for match in matches:
    print(f"{match['label']} - Confiance: {match['confidence']:.0%}")
```

### Test des Matchers

```bash
python test_matchers.py
```

## Créer un Nouveau Matcher

### 1. Créer le fichier

Créer `matchers/mon_matcher.py` :

```python
from base_matcher import BaseWikidataMatcher
from typing import Dict, List

class MonMatcher(BaseWikidataMatcher):
    name = "Mon Matcher"
    description = "Description de mon matcher"
    supported_types = ["mon_type"]
    
    def can_handle(self, entity_type: str, extracted_data: Dict) -> bool:
        """Vérifier si ce matcher peut traiter cette entité"""
        return entity_type in self.supported_types
    
    def find_matches(self, extracted_data: Dict) -> List[Dict]:
        """Trouver des correspondances"""
        matches = []
        
        # Construire la requête SPARQL
        query = """
        SELECT ?item ?itemLabel WHERE {
          # Votre requête ici
          SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en" . }
        }
        LIMIT 10
        """
        
        # Exécuter la requête
        results = self.execute_sparql_query(query)
        
        # Traiter les résultats
        for result in results:
            item_id = self._extract_qid(result.get('item', ''))
            match = {
                'id': item_id,
                'label': result.get('itemLabel', ''),
                'url': f"https://www.wikidata.org/wiki/{item_id}",
                'confidence': 0.8,
                'match_type': 'custom'
            }
            matches.append(match)
        
        return matches
    
    def _extract_qid(self, uri: str) -> str:
        """Extraire le QID d'une URI"""
        import re
        match = re.search(r'Q\d+', uri)
        return match.group(0) if match else ''
```

### 2. Redémarrer l'application

Le matcher sera automatiquement chargé.

## Propriétés Wikidata Utiles

### Peintures
- P31 : instance de (Q3305213 = peinture)
- P170 : créateur
- P571 : date de création
- P180 : représente (depicts)
- P186 : matériau
- P2048 : hauteur
- P2049 : largeur
- P195 : collection
- P18 : image

### Artistes
- P31 : instance de (Q5 = humain)
- P106 : occupation (Q483501 = artiste)
- P569 : date de naissance
- P570 : date de mort
- P135 : mouvement
- P27 : pays de citoyenneté

## Optimisation des Requêtes SPARQL

### Bonnes Pratiques

1. **Limiter les résultats** : Toujours utiliser `LIMIT`
2. **Filtrer tôt** : Mettre les filtres au début
3. **Utiliser les index** : Préférer les propriétés indexées
4. **Éviter les regex** : Utiliser CONTAINS plutôt que REGEX
5. **Optionnel prudent** : Trop d'OPTIONAL ralentit la requête

### Exemple Optimisé

```sparql
# ✅ BON - Filtre tôt, limité
SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q3305213 .           # Filtre type d'abord
  ?item rdfs:label "Titre exact"@fr .    # Filtre exact
  OPTIONAL { ?item wdt:P18 ?image . }    # Optionnel à la fin
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr" . }
}
LIMIT 5

# ❌ MAUVAIS - Trop large, pas de limite
SELECT * WHERE {
  ?item ?p ?o .
  FILTER(REGEX(?o, "motif"))
}
```

## Débogage

### Voir les Requêtes SPARQL

Ajouter des prints dans le matcher :

```python
def find_matches(self, extracted_data: Dict) -> List[Dict]:
    query = "..."
    print(f"Requête SPARQL :\n{query}")
    results = self.execute_sparql_query(query)
    print(f"Résultats: {len(results)}")
    return ...
```

### Tester les Requêtes

Tester directement sur : https://query.wikidata.org/

### Erreurs Communes

| Erreur | Cause | Solution |
|--------|-------|----------|
| Timeout | Requête trop complexe | Simplifier, ajouter des filtres |
| 0 résultats | Filtres trop restrictifs | Assouplir les filtres |
| Trop de résultats | Pas assez de filtres | Ajouter des contraintes |

## Cache SPARQL

Les requêtes SPARQL ne sont **pas** mises en cache par défaut car :
- Wikidata change constamment
- Les requêtes sont rapides (< 1s)
- Le cache pourrait retourner des données obsolètes

Pour ajouter un cache (optionnel), modifier `base_matcher.py`.

## Performance

### Temps Typiques
- Requête simple (titre exact) : 0.5-1s
- Requête complexe (multi-critères) : 1-3s
- Requêtes parallèles : Non recommandé (rate limiting)

### Limites Wikidata
- Max 60 requêtes/minute par IP
- Timeout après 60 secondes
- Limiter à 10-20 résultats par requête

## Sécurité

### Injection SPARQL

⚠️ **Important** : Toujours échapper les entrées utilisateur !

```python
# ❌ DANGEREUX
query = f'SELECT * WHERE {{ ?item rdfs:label "{user_input}"@fr }}'

# ✅ SÛR
user_input_escaped = user_input.replace('"', '\\"')
query = f'SELECT * WHERE {{ ?item rdfs:label "{user_input_escaped}"@fr }}'
```

### Pas d'Authentification

Les matchers n'ont **aucune** capacité d'écriture :
- Lecture seule via SPARQL
- Pas de token nécessaire
- Pas de risque de modification accidentelle

## Conclusion

Les matchers permettent de :
- ✅ Trouver des entités Wikidata sans authentification
- ✅ Scorer les correspondances par confiance
- ✅ Offrir plusieurs stratégies de recherche
- ✅ Faciliter la validation par l'utilisateur
- ✅ Séparer la recherche de l'enrichissement

L'authentification est **uniquement** requise pour créer ou enrichir des entités, pas pour les chercher !
