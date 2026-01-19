# 🚦 Gestion des Limites de l'API Wikidata

## Problème

Wikidata impose des limites strictes sur les requêtes SPARQL :
- **60 requêtes par minute** maximum
- **Timeout après 60 secondes** par requête
- **429 Too Many Requests** si vous dépassez la limite

## Erreurs Communes

```
Erreur SPARQL: HTTPSConnectionPool: Read timed out
Erreur SPARQL: 429 Client Error: Too Many Requests
```

## Solutions Implémentées

### 1. Délai Entre les Requêtes

**Dans `property_matcher.py` :**
```python
REQUEST_DELAY = 1.5  # 1.5 secondes entre chaque requête
```

Cela limite à ~40 requêtes/minute (marge de sécurité).

### 2. Retry Automatique

```python
MAX_RETRIES = 3

# Si erreur 429 : attente progressive (5s, 10s, 15s)
# Si timeout : attente de 2s, 4s, 6s
```

### 3. Timeout Réduit

```python
REQUEST_TIMEOUT = 15  # 15 secondes au lieu de 30
```

Les requêtes complexes qui timeout sont probablement trop lourdes.

### 4. Limitation des Propriétés

**Dans les tests et l'application :**
- Limiter les mots-clés à 5 maximum
- Traiter les propriétés essentielles en priorité

## Bonnes Pratiques

### 1. Optimiser les Requêtes SPARQL

**❌ MAUVAIS - Trop large :**
```sparql
SELECT * WHERE {
  ?item ?p ?o .
  FILTER(CONTAINS(?o, "mot"))
}
```

**✅ BON - Filtré tôt :**
```sparql
SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q5 .  # Filtre type d'abord
  ?item rdfs:label "Nom exact"@fr .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr" . }
}
LIMIT 5
```

### 2. Traiter Par Lots

Si vous avez beaucoup de propriétés :
```python
# Diviser en groupes
keywords_batch1 = keywords[:5]
keywords_batch2 = keywords[5:10]

# Traiter avec pause entre les lots
results1 = process_batch(keywords_batch1)
time.sleep(5)  # Pause de 5s entre les lots
results2 = process_batch(keywords_batch2)
```

### 3. Prioriser les Propriétés

Ordre de traitement recommandé :
1. **Créateur** (1 requête)
2. **Personnes représentées** (1-3 requêtes)
3. **Top 3-5 mots-clés** (3-5 requêtes)
4. **Matériau** (1 requête)
5. **Collection** (1 requête si nécessaire)

**Total : 7-11 requêtes** par peinture → Safe

### 4. Éviter les Requêtes en Parallèle

**❌ Ne PAS faire :**
```python
# Toutes les requêtes en même temps
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(search, kw) for kw in keywords]
```

**✅ Faire :**
```python
# Une après l'autre avec délai
for keyword in keywords:
    result = search(keyword)
    time.sleep(1.5)
```

### 5. Utiliser le Cache

**Important :** Les mêmes requêtes peuvent être faites plusieurs fois.

Implémenter un cache simple :
```python
cache = {}

def search_with_cache(term):
    if term in cache:
        return cache[term]
    
    result = search(term)
    cache[term] = result
    return result
```

## Configuration Recommandée

### Pour les Tests

```python
# test_property_matching.py
extracted_data = {
    'creator': '...',
    'keywords': [...][:3],  # Limiter à 3
    'depicted_persons': [...][: 2],  # Limiter à 2
}
```

### Pour la Production

```python
# property_matcher.py
class PropertyMatcher:
    REQUEST_DELAY = 1.5  # Ajuster selon vos besoins
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = 15
    MAX_KEYWORDS = 5  # Limiter le nombre de mots-clés
```

## Monitoring

### Compter les Requêtes

Ajouter un compteur :
```python
class PropertyMatcher:
    def __init__(self):
        self.request_count = 0
        self.start_time = time.time()
    
    def _execute_sparql(self, query):
        self.request_count += 1
        
        # Vérifier le taux
        elapsed = time.time() - self.start_time
        rate = self.request_count / (elapsed / 60)  # requêtes/minute
        
        if rate > 50:
            print(f"⚠️  Taux élevé: {rate:.1f} req/min")
            time.sleep(2)  # Ralentir
        
        # ... rest of method
```

## Alternatives

### 1. Utiliser l'API Wikidata Entity Search

Pour les recherches simples, utiliser :
```python
# Au lieu de SPARQL
endpoint = "https://www.wikidata.org/w/api.php"
params = {
    'action': 'wbsearchentities',
    'format': 'json',
    'language': 'fr',
    'search': term,
    'limit': 5
}
```

**Avantage :** Plus rapide, moins de limitations.

### 2. Batch Processing

Traiter plusieurs éléments dans une seule requête SPARQL (quand possible) :
```sparql
SELECT ?item ?itemLabel WHERE {
  VALUES ?label { "mot1"@fr "mot2"@fr "mot3"@fr }
  ?item rdfs:label ?label .
}
```

### 3. Utiliser un Service Tiers

- **Wikidata Query Service UI** : Pour tester les requêtes
- **SPARQL Proxy** : Pour mettre en cache les résultats

## Erreurs et Solutions

| Erreur | Cause | Solution |
|--------|-------|----------|
| 429 Too Many Requests | Trop de requêtes/minute | Augmenter REQUEST_DELAY à 2s |
| Read timeout | Requête trop complexe | Simplifier la requête SPARQL |
| Connection refused | Service surchargé | Réessayer plus tard |
| Empty results | Requête trop stricte | Assouplir les filtres |

## Checklist Avant de Lancer

- [ ] REQUEST_DELAY >= 1.5 secondes
- [ ] Mots-clés limités à 5 maximum
- [ ] Requêtes SPARQL optimisées (LIMIT, filtres)
- [ ] Retry logic implémenté
- [ ] Timeout raisonnable (15-20s)
- [ ] Messages de progression pour l'utilisateur
- [ ] Gestion d'erreurs gracieuse

## Test Progressif

```bash
# Test 1 : Une seule propriété
python -c "from property_matcher import PropertyMatcher; \
           m = PropertyMatcher(); \
           print(m.search_person('Édouard Toudouze', '1848', '1907'))"

# Test 2 : Quelques propriétés
python test_property_matching.py

# Test 3 : Charge complète
# Seulement si les tests précédents passent
```

## Résumé

**Règles d'or :**
1. ⏱️  **1.5s minimum** entre chaque requête
2. 🔢 **5 mots-clés max** par traitement
3. 🔄 **3 retries** en cas d'erreur
4. ⏰ **15s timeout** par requête
5. 📊 **Optimiser** les requêtes SPARQL
6. 💾 **Cacher** les résultats quand possible

Avec ces règles, vous restez largement sous la limite de 60 req/min ! ✅
