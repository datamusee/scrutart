# 📚 Système de Référence Manuelle des Mots-Clés

## Vue d'Ensemble

Le système de référence manuelle permet de **guider et compléter** les associations automatiques de mots-clés avec des entités Wikidata.

### Principe

```
Mot-clé → 1. Référence manuelle (priorité)
          2. Recherche automatique (complément)
          → Combinaison et tri
```

## Fichier de Référence

### Emplacement

```
data/keyword_reference.json
```

Le fichier est créé automatiquement au premier lancement s'il n'existe pas.

### Structure

```json
{
  "mot-clé": [
    {
      "qid": "Q12345",
      "label_fr": "Label français",
      "label_en": "English label",
      "description": "Description de l'entité",
      "confidence": 0.95
    }
  ]
}
```

### Exemple Complet

```json
{
  "lit": [
    {
      "qid": "Q42177",
      "label_fr": "lit",
      "label_en": "bed",
      "description": "meuble sur lequel on se couche pour dormir",
      "confidence": 0.95
    }
  ],
  "scène historique": [
    {
      "qid": "Q742333",
      "label_fr": "peinture d'histoire",
      "label_en": "history painting",
      "description": "genre de peinture historique",
      "confidence": 0.95
    },
    {
      "qid": "Q1358372",
      "label_fr": "scène de genre",
      "label_en": "genre painting",
      "description": "peinture de scènes quotidiennes",
      "confidence": 0.85
    }
  ]
}
```

## Utilisation

### Mode Automatique

Le système utilise automatiquement les références :

```python
from property_matcher import PropertyMatcher

matcher = PropertyMatcher()  # Charge automatiquement le fichier

# Recherche un concept
matches = matcher.search_concept("lit")

# Résultat:
# 1. Référence manuelle (Q42177) - confiance 0.95
# 2. Résultats automatiques complémentaires
```

### Ajouter une Référence Programmée

```python
matcher.add_keyword_reference(
    keyword="épée",
    qid="Q12791",
    label_fr="épée",
    label_en="sword",
    description="arme blanche à lame droite",
    confidence=0.95
)
```

### Outil en Ligne de Commande

```bash
python manage_keyword_reference.py
```

**Menu interactif :**
```
1. Lister les références
2. Ajouter une référence manuellement
3. Rechercher et ajouter
4. Supprimer une référence
5. Exporter les références
0. Quitter
```

## Workflow Complet

### 1. Recherche avec Référence

```python
matcher.search_concept("scène historique")
```

**Étapes :**
1. ✅ Vérifie la référence manuelle
2. 📝 Trouve 2 entités manuelles (Q742333, Q1358372)
3. 🔍 Lance recherche automatique pour compléter
4. 🎯 Combine: manuelles en priorité
5. 📊 Tri par confiance

**Résultat :**
```
✓ Référence manuelle trouvée pour 'scène historique'
→ 2 manuel(s) + 1 auto = 3 résultat(s)

1. Peinture d'histoire (Q742333) [95%] ← Manuel
2. Scène de genre (Q1358372) [85%] ← Manuel
3. Tableau historique (Q...) [70%] ← Auto
```

### 2. Recherche sans Référence

```python
matcher.search_concept("drapeau")
```

**Étapes :**
1. ❌ Pas de référence manuelle
2. 🔍 Recherche automatique uniquement
3. 📊 Tri par confiance

**Résultat :**
```
→ 0 manuel(s) + 5 auto = 5 résultat(s)

1. Drapeau (Q14660) [90%] ← Auto
2. Bannière (Q...) [75%] ← Auto
```

## Stratégie de Priorisation

### Haute Confiance Manuelle

Si 3+ références manuelles avec confiance ≥ 0.9 :
```python
if len(high_confidence_manual) >= 3:
    return manual_matches  # Pas de recherche auto
```

**Économise une requête SPARQL !**

### Complément Automatique

Si < 3 références manuelles :
```python
# Chercher automatiquement
auto_matches = search_automatic(keyword)

# Combiner sans doublons
combined = manual + [a for a in auto if a.qid not in manual_qids]
```

## Cas d'Usage

### 1. Corriger des Associations Problématiques

**Problème :** "lit" trouve Lituanie en premier

**Solution :**
```json
{
  "lit": [
    {
      "qid": "Q42177",
      "label_fr": "lit",
      "description": "meuble pour dormir",
      "confidence": 0.95
    }
  ]
}
```

**Résultat :** Lit (meuble) toujours en premier ✅

### 2. Gérer les Ambiguïtés

**Problème :** "rose" = fleur ou couleur ?

**Solution :**
```json
{
  "rose": [
    {
      "qid": "Q47461",
      "label_fr": "rose",
      "description": "fleur",
      "confidence": 0.95
    },
    {
      "qid": "Q3142",
      "label_fr": "rose",
      "description": "couleur",
      "confidence": 0.90
    }
  ]
}
```

**Résultat :** Les deux proposés, utilisateur choisit

### 3. Genres Artistiques

**Problème :** "scène historique" trouve des tableaux, pas le genre

**Solution :**
```json
{
  "scène historique": [
    {
      "qid": "Q742333",
      "label_fr": "peinture d'histoire",
      "description": "genre pictural",
      "confidence": 0.95
    }
  ]
}
```

### 4. Termes Techniques

**Problème :** "dais" (baldaquin) mal compris

**Solution :**
```json
{
  "dais": [
    {
      "qid": "Q201564",
      "label_fr": "baldaquin",
      "description": "dais portatif ou fixe",
      "confidence": 0.95
    }
  ]
}
```

## Gestion Interactive

### Lister les Références

```bash
python manage_keyword_reference.py
# Choix: 1
```

**Affichage :**
```
📌 'lit' (1 entité) :
   → Q42177 - lit
      EN: bed
      Confiance: 95%
      meuble sur lequel on se couche...

📌 'scène historique' (2 entités) :
   → Q742333 - peinture d'histoire
   → Q1358372 - scène de genre
```

### Rechercher et Ajouter

```bash
python manage_keyword_reference.py
# Choix: 3
```

**Workflow :**
```
Mot-clé à rechercher : épée

🔍 Recherche de 'épée' dans Wikidata...

3 résultat(s) trouvé(s) :

1. Épée (Q12791)
   Confiance: 90%
   arme blanche à lame droite...

2. Sabre (Q12791)
   ...

Numéro de l'entité à ajouter : 1

📝 Ajouter 'épée' → Q12791 (Épée) ?
Confirmer (o/n) : o

✅ Référence ajoutée: 'épée' → Q12791 (Épée)
```

### Supprimer une Référence

```bash
python manage_keyword_reference.py
# Choix: 4
```

### Exporter

```bash
python manage_keyword_reference.py
# Choix: 5
```

**Crée :** `keyword_reference_export.txt`

```
RÉFÉRENCES MANUELLES WIKIDATA
==================================================

Mot-clé: lit
--------------------------------------------------
  QID: Q42177
  Label FR: lit
  Label EN: bed
  Description: meuble sur lequel on se couche...
  Confiance: 95%
  URL: https://www.wikidata.org/wiki/Q42177
```

## Maintenance

### Enrichir Progressivement

```python
# Après chaque property matching, noter les mots-clés problématiques
# Les ajouter manuellement au fichier de référence
```

**Stratégie :**
1. Lancer property matching
2. Noter les associations incorrectes
3. Ajouter les bonnes via `manage_keyword_reference.py`
4. Relancer → associations correctes

### Versionner le Fichier

```bash
git add data/keyword_reference.json
git commit -m "Ajout références: épée, couronne, ange"
```

**Avantage :** Historique des modifications

### Partager entre Projets

```bash
cp data/keyword_reference.json /autre/projet/data/
```

Le fichier est portable et réutilisable.

## Performance

### Impact sur les Requêtes

| Scénario | Requêtes SPARQL | Temps |
|----------|-----------------|-------|
| 3+ références manuelles | 0 | 0.1s |
| 1-2 références | 1 | 1.0s |
| 0 référence | 1 | 1.0s |

**Gain :** Économie de requêtes pour termes courants

### Taille du Fichier

- 10 mots-clés : ~2 KB
- 100 mots-clés : ~20 KB
- 1000 mots-clés : ~200 KB

**Impact :** Négligeable (chargé une fois au démarrage)

## Exemples de Référence

### Objets Courants

```json
{
  "épée": [{"qid": "Q12791", "label_fr": "épée", "confidence": 0.95}],
  "couronne": [{"qid": "Q170977", "label_fr": "couronne", "confidence": 0.95}],
  "livre": [{"qid": "Q571", "label_fr": "livre", "confidence": 0.95}],
  "cheval": [{"qid": "Q726", "label_fr": "cheval", "confidence": 0.98}]
}
```

### Genres Artistiques

```json
{
  "portrait": [{"qid": "Q134307", "label_fr": "portrait", "confidence": 0.95}],
  "paysage": [{"qid": "Q191163", "label_fr": "paysage", "confidence": 0.95}],
  "nature morte": [{"qid": "Q170593", "label_fr": "nature morte", "confidence": 0.95}]
}
```

### Concepts Religieux

```json
{
  "ange": [{"qid": "Q235113", "label_fr": "ange", "confidence": 0.95}],
  "croix": [
    {"qid": "Q40953", "label_fr": "croix chrétienne", "confidence": 0.95},
    {"qid": "Q40933", "label_fr": "croix", "confidence": 0.90}
  ],
  "saint": [{"qid": "Q43115", "label_fr": "saint", "confidence": 0.95}]
}
```

### Personnages Historiques

```json
{
  "napoléon": [{"qid": "Q517", "label_fr": "Napoléon Bonaparte", "confidence": 0.98}],
  "louis xiv": [{"qid": "Q7742", "label_fr": "Louis XIV", "confidence": 0.98}]
}
```

## Bonnes Pratiques

### 1. Confiance Appropriée

- 0.98 : Évidence absolue (Napoléon, cheval)
- 0.95 : Très haute confiance (lit, épée)
- 0.90 : Haute confiance (variantes acceptables)
- 0.85 : Confiance moyenne (ambiguïté mineure)

### 2. Descriptions Claires

```json
// ✅ BON
"description": "meuble sur lequel on se couche pour dormir"

// ❌ PAS BON
"description": "lit"  // Pas informatif
```

### 3. Labels Bilingues

```json
{
  "label_fr": "épée",
  "label_en": "sword"  // Aide pour recherches anglaises
}
```

### 4. Ordre de Préférence

```json
{
  "croix": [
    {"qid": "Q40953", "confidence": 0.95},  // Spécifique (chrétienne)
    {"qid": "Q40933", "confidence": 0.90}   // Générique (forme)
  ]
}
```

## Limitations

### 1. Maintenance Manuelle

Nécessite mise à jour humaine → charge de travail

**Solution :** Enrichir progressivement

### 2. Contexte Limité

Même référence pour tous contextes

**Futur :** Références contextuelles (peinture religieuse vs laïque)

### 3. Pas de Versioning Automatique

Modifications écrasent l'ancien contenu

**Solution :** Versionner avec Git

## Conclusion

Le système de référence manuelle :
- ✅ **Corrige** les associations problématiques
- ✅ **Accélère** le matching (moins de requêtes)
- ✅ **Améliore** la qualité des résultats
- ✅ **Capitalise** sur l'expérience humaine
- ✅ **Partage** entre projets

C'est le **complément parfait** à la recherche automatique ! 🎯
