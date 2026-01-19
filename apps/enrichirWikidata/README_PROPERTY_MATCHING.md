# 🔗 Property Matching - Documentation

## Vue d'Ensemble

Le **Property Matching** est une phase cruciale qui permet d'associer automatiquement les propriétés extraites d'une URL avec des entités Wikidata correspondantes, avec validation utilisateur pour chaque association.

## Concept

```
Extraction → Property Matching → Validation → Enrichissement
```

### Exemple Concret

**URL traitée :** Peinture "Duguesclin sur son lit de mort"

**Propriétés extraites :**
- Créateur: "TOUDOUZE Edouard" (1848-1907)
- Mots-clés: "scène historique", "cadavre", "lit", "soldat"
- Personne représentée: "Bertrand Du Guesclin"
- Matériau: "Toile"

**Property Matching :**
1. 🔍 Recherche dans Wikidata pour chaque valeur
2. 📊 Présentation des correspondances avec scores
3. ✅ Validation utilisateur propriété par propriété
4. 💾 Préparation pour l'enrichissement

## Flux de Travail

### 1. Extraction (Automatique)

L'extracteur récupère les données de l'URL :
```json
{
  "creator": "TOUDOUZE Edouard",
  "creator_birth": "1848",
  "creator_death": "1907",
  "keywords": ["scène historique", "cadavre", "lit"],
  "depicted_persons": ["Bertrand Du Guesclin"]
}
```

### 2. Property Matching (Bouton déclenché par l'utilisateur)

L'utilisateur clique sur **"🔍 Matcher les propriétés avec Wikidata"**

Le système recherche automatiquement dans Wikidata :

**Pour le créateur "TOUDOUZE Edouard" :**
- ✅ Édouard Toudouze (Q3579990) - Confiance: 95%
  - Naissance: 1848
  - Mort: 1907
  - Peintre français

**Pour "Bertrand Du Guesclin" :**
- ✅ Bertrand du Guesclin (Q202422) - Confiance: 98%
  - Connétable de France
  - 1320-1380

**Pour "scène historique" :**
- ✅ Scène de genre (Q1358372) - Confiance: 85%
- ⚠️ Peinture d'histoire (Q742333) - Confiance: 75%

**Pour "cadavre" :**
- ✅ Cadavre (Q48422) - Confiance: 98%

**Pour "lit" :**
- ✅ Lit (Q42177) - Confiance: 95%
- ⚠️ Mobilier de chambre (Q.....) - Confiance: 60%

### 3. Validation (Interface Interactive)

L'interface affiche chaque propriété avec ses correspondances :

```
┌─────────────────────────────────────────────────┐
│ 📍 CRÉATEUR                                     │
│                                                  │
│ ○ Édouard Toudouze (Q3579990)     [95%]        │
│   Peintre français                              │
│   Naissance: 1848 | Mort: 1907                  │
│   → Voir dans Wikidata                          │
│                                                  │
│ ○ Aucune correspondance / Ne pas ajouter        │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 👤 PERSONNE: Bertrand Du Guesclin               │
│                                                  │
│ ○ Bertrand du Guesclin (Q202422)   [98%]       │
│   Connétable de France                          │
│   → Voir dans Wikidata                          │
│                                                  │
│ ○ Aucune correspondance / Ne pas ajouter        │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 🔑 CONCEPT: scène historique                    │
│                                                  │
│ ○ Scène de genre (Q1358372)        [85%]       │
│ ○ Peinture d'histoire (Q742333)    [75%]       │
│ ○ Aucune correspondance / Ne pas ajouter        │
└─────────────────────────────────────────────────┘
```

L'utilisateur :
1. Sélectionne la bonne correspondance pour chaque propriété
2. Peut choisir "Ne pas ajouter" si aucune ne convient
3. Clique sur "Valider toutes les associations"

### 4. Récapitulatif

Le système affiche un récapitulatif :

```
✅ Propriétés à ajouter :
- créateur (P170): Q3579990 (Édouard Toudouze)
- représente (P180): Q202422 (Bertrand du Guesclin)
- représente (P180): Q1358372 (Scène de genre)
- représente (P180): Q48422 (Cadavre)
- représente (P180): Q42177 (Lit)
```

### 5. Enrichissement (Avec authentification)

Lorsque l'utilisateur confirme l'enrichissement de l'entité principale, toutes les propriétés validées sont ajoutées en une seule opération.

## Types de Propriétés Supportées

### Peintures

| Propriété | ID Wikidata | Exemple |
|-----------|-------------|---------|
| Créateur | P170 | Édouard Toudouze |
| Représente (depicts) | P180 | Bertrand Du Guesclin, scène historique |
| Matériau | P186 | Toile, huile |
| Collection | P195 | Musée de Rennes |
| Mouvement | P135 | Réalisme |
| Genre | P136 | Peinture d'histoire |

### Artistes

| Propriété | ID Wikidata | Exemple |
|-----------|-------------|---------|
| Occupation | P106 | Peintre |
| Mouvement | P135 | Impressionnisme |
| Nationalité | P27 | France |

## Recherche SPARQL par Type

### Personne (Créateur, Personne représentée)

```sparql
SELECT DISTINCT ?item ?itemLabel ?birth ?death WHERE {
  ?item wdt:P31 wd:Q5 .  # humain
  ?item rdfs:label ?label .
  FILTER(CONTAINS(LCASE(?label), LCASE("TOUDOUZE")))
  OPTIONAL { ?item wdt:P569 ?birth . FILTER(YEAR(?birth) = 1848) }
  OPTIONAL { ?item wdt:P570 ?death . FILTER(YEAR(?death) = 1907) }
}
```

### Concept / Mot-clé

```sparql
SELECT DISTINCT ?item ?itemLabel ?description WHERE {
  ?item rdfs:label "scène historique"@fr .
  OPTIONAL { ?item schema:description ?description . }
}
```

### Matériau

```sparql
SELECT DISTINCT ?item ?itemLabel WHERE {
  ?item wdt:P31|wdt:P279* wd:Q214609 .  # matériau
  FILTER(CONTAINS(LCASE(?label), LCASE("toile")))
}
```

### Collection / Musée

```sparql
SELECT DISTINCT ?item ?itemLabel WHERE {
  { ?item wdt:P31 wd:Q33506 . }  # musée
  UNION
  { ?item wdt:P31 wd:Q2668072 . }  # collection
  FILTER(CONTAINS(LCASE(?label), LCASE("rennes")))
}
```

## Scores de Confiance

| Score | Signification | Action Recommandée |
|-------|---------------|-------------------|
| 95-100% | Très haute confiance | ✅ Valider |
| 80-94% | Haute confiance | ✅ Vérifier et valider |
| 60-79% | Confiance moyenne | ⚠️ Vérifier attentivement |
| < 60% | Confiance faible | ⚠️ Vérifier ou rejeter |

### Facteurs Affectant le Score

**Pour les personnes :**
- Correspondance exacte du nom : +0.7
- Date de naissance correspond : +0.15
- Date de mort correspond : +0.15

**Pour les concepts :**
- Correspondance exacte du label : 0.9
- Correspondance partielle : 0.6

## API

### Route: POST /match_properties

**Requête :**
```json
{
  "extracted_data": {
    "creator": "TOUDOUZE Edouard",
    "creator_birth": "1848",
    "creator_death": "1907",
    "keywords": ["scène historique", "cadavre"],
    "depicted_persons": ["Bertrand Du Guesclin"]
  },
  "entity_type": "painting"
}
```

**Réponse :**
```json
{
  "success": true,
  "property_matches": {
    "creator": [
      {
        "id": "Q3579990",
        "label": "Édouard Toudouze",
        "confidence": 0.95,
        "property": "P170",
        "property_label": "créateur"
      }
    ],
    "keywords": {
      "scène historique": [
        {
          "id": "Q1358372",
          "label": "Scène de genre",
          "confidence": 0.85,
          "property": "P180",
          "property_label": "représente (depicts)"
        }
      ]
    },
    "depicted_persons": {
      "Bertrand Du Guesclin": [
        {
          "id": "Q202422",
          "label": "Bertrand du Guesclin",
          "confidence": 0.98,
          "property": "P180",
          "property_label": "représente (depicts)"
        }
      ]
    }
  }
}
```

## Utilisation en Python

```python
from property_matcher import PropertyMatcher

# Initialiser
matcher = PropertyMatcher()

# Données extraites
data = {
    'creator': 'TOUDOUZE Edouard',
    'creator_birth': '1848',
    'creator_death': '1907',
    'keywords': ['scène historique', 'cadavre', 'lit'],
    'depicted_persons': ['Bertrand Du Guesclin']
}

# Matcher toutes les propriétés
matches = matcher.match_all_properties(data, 'painting')

# Afficher les résultats
for prop, prop_matches in matches.items():
    print(f"\n{prop}:")
    if isinstance(prop_matches, dict):
        for key, items in prop_matches.items():
            print(f"  {key}: {len(items)} correspondance(s)")
    else:
        print(f"  {len(prop_matches)} correspondance(s)")
```

## Test

```bash
python test_property_matching.py
```

**Résultat attendu :**
```
🔍 Tests du Property Matching

📍 CRÉATEUR
  Édouard Toudouze (Q3579990)
  Confiance: 95%
  Naissance: 1848
  Mort: 1907

👤 PERSONNES REPRÉSENTÉES
  Recherche pour: Bertrand Du Guesclin
    → Bertrand du Guesclin (Q202422) - 98%

🔑 MOTS-CLÉS
  Recherche pour: 'scène historique'
    → Scène de genre (Q1358372) - 85%

✅ Résultats complets sauvegardés dans: test_property_matching_result.json
```

## Avantages du Property Matching

### 1. **Séparation des Responsabilités**
- Extraction ≠ Matching ≠ Validation ≠ Enrichissement
- Chaque phase est indépendante et testable

### 2. **Pas d'Authentification pour la Recherche**
- Utilise seulement SPARQL (lecture publique)
- Authentification requise uniquement pour l'enrichissement final

### 3. **Validation Granulaire**
- L'utilisateur valide chaque association
- Pas d'ajout automatique non vérifié
- Contrôle total sur les données ajoutées

### 4. **Qualité des Données**
- Scores de confiance pour guider l'utilisateur
- Plusieurs options pour chaque propriété
- Possibilité de rejeter si aucune ne convient

### 5. **Efficacité**
- Toutes les propriétés matchées en une seule étape
- Interface claire et organisée
- Validation en batch

## Limitations

### 1. **Dépendance à la Qualité de l'Extraction**
Si l'extraction est imprécise, le matching sera moins bon.

### 2. **Ambiguïté des Concepts**
Certains mots peuvent avoir plusieurs sens :
- "lit" → le meuble OU le fait de lire
- Solution : proposer plusieurs options

### 3. **Entités Manquantes**
Certaines entités peuvent ne pas exister dans Wikidata.
- Solution : permettre de créer l'entité

### 4. **Requêtes SPARQL Lentes**
Pour de nombreuses propriétés, cela peut prendre du temps.
- Solution : afficher progressivement les résultats

## Bonnes Pratiques

### 1. **Vérifier les Dates**
Pour les personnes, toujours vérifier que les dates correspondent.

### 2. **Lire les Descriptions**
Les descriptions Wikidata aident à lever les ambiguïtés.

### 3. **Privilégier les Scores Élevés**
En général, les correspondances > 90% sont fiables.

### 4. **Ne Pas Hésiter à Rejeter**
Mieux vaut ne rien ajouter qu'ajouter une mauvaise association.

### 5. **Consulter Wikidata**
Utiliser le lien "Voir dans Wikidata" pour vérifier.

## Conclusion

Le Property Matching est la **clé de la qualité** de l'enrichissement Wikidata :
- ✅ Automatise la recherche fastidieuse
- ✅ Guide l'utilisateur avec des scores
- ✅ Permet une validation granulaire
- ✅ Maintient la qualité des données
- ✅ Ne nécessite pas d'authentification

C'est le maillon essentiel entre l'extraction brute et l'enrichissement validé !
