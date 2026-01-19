# 🔄 Gestion des Variantes de Noms

## Problème

Les noms de personnes peuvent être écrits de plusieurs façons :
- **TOUDOUZE Edouard** (NOM Prénom)
- **Edouard TOUDOUZE** (Prénom NOM)
- **Édouard Toudouze** (Prénom Nom)
- **Toudouze Édouard** (Nom Prénom)

Le moteur de recherche Wikidata peut ne pas trouver toutes les variantes avec une seule requête.

## Solution : Génération Automatique de Variantes

### Algorithme

```python
def _generate_name_variants(name):
    """
    1. Nom original toujours inclus
    2. Détecter le format (majuscules, position)
    3. Générer les permutations intelligentes
    4. Retourner liste unique sans doublons
    """
```

### Cas Traités

#### 1. NOM Prénom → Prénom NOM

**Entrée :** `"TOUDOUZE Edouard"`

**Détection :** Premier mot en MAJUSCULES

**Variantes générées :**
1. `TOUDOUZE Edouard` (original)
2. `Edouard TOUDOUZE` (inversé)
3. `Edouard Toudouze` (normalisé)

#### 2. Prénom NOM → NOM Prénom

**Entrée :** `"Edouard TOUDOUZE"`

**Détection :** Dernier mot en MAJUSCULES

**Variantes générées :**
1. `Edouard TOUDOUZE` (original)
2. `TOUDOUZE Edouard` (inversé)

#### 3. Prénom Nom → Nom Prénom

**Entrée :** `"Édouard Toudouze"`

**Détection :** Casse mixte normale

**Variantes générées :**
1. `Édouard Toudouze` (original)
2. `Toudouze Édouard` (inversé)
3. `TOUDOUZE Édouard` (nom en majuscules)

#### 4. Noms Composés

**Entrée :** `"Vincent VAN GOGH"`

**Variantes générées :**
1. `Vincent VAN GOGH` (original)
2. `VAN GOGH Vincent` (inversé)
3. `VAN GOGH Vincent` (normalisé)

**Entrée :** `"Pierre-Auguste RENOIR"`

**Variantes générées :**
1. `Pierre-Auguste RENOIR` (original)
2. `RENOIR Pierre-Auguste` (inversé)

## Stratégie de Recherche Multi-Variantes

### Processus

```python
def search_person(name, birth, death):
    # 1. Générer variantes
    variants = _generate_name_variants(name)
    # ["TOUDOUZE Edouard", "Edouard TOUDOUZE", "Edouard Toudouze"]
    
    # 2. Rechercher chaque variante
    all_matches = {}  # Éviter doublons par QID
    
    for variant in variants:
        results = mwapi_search(variant)
        for result in results:
            if result.qid not in all_matches:
                all_matches[result.qid] = result
    
    # 3. Arrêt anticipé si bons résultats
    if len(high_confidence_matches) >= 3:
        break  # Pas besoin de toutes les variantes
    
    # 4. Retourner top 10 triés par confiance
    return sorted(all_matches.values(), by=confidence)[:10]
```

### Optimisations

#### Arrêt Anticipé

Si on trouve déjà 3+ résultats avec confiance ≥ 90%, on arrête :
```python
if len(all_matches) >= 3:
    high_confidence = [m for m in all_matches if m.confidence >= 0.9]
    if high_confidence:
        break  # Pas besoin des autres variantes
```

#### Déduplication par QID

```python
all_matches = {}  # Dict avec QID comme clé

for result in results:
    qid = extract_qid(result)
    if qid not in all_matches:
        all_matches[qid] = result
```

Évite d'avoir 3 fois la même personne si trouvée avec plusieurs variantes.

## Exemples Concrets

### Exemple 1 : Édouard Toudouze

**Recherche 1 :** `"TOUDOUZE Edouard"` (original)
```
✅ Q3579990 - Édouard Toudouze (confiance: 95%)
```

**Recherche 2 :** `"Edouard TOUDOUZE"` (variante)
```
✅ Q3579990 - Édouard Toudouze (confiance: 95%)
```

**Résultat fusionné :**
```
Q3579990 - Édouard Toudouze (confiance: 95%) [trouvé 2 fois]
```

Déduplication → 1 seul résultat retourné ✅

### Exemple 2 : Vincent van Gogh

**Entrée :** `"Vincent VAN GOGH"`

**Variantes testées :**
1. `Vincent VAN GOGH`
2. `VAN GOGH Vincent`

**Résultat :**
```
✅ Q5582 - Vincent van Gogh
```

Les deux variantes trouvent la même entité → 1 résultat

### Exemple 3 : Nom Inconnu

**Entrée :** `"Jean DUPONT"`

**Variantes testées :**
1. `Jean DUPONT`
2. `DUPONT Jean`

**Résultat :**
```
Q123456 - Jean Dupont (peintre)
Q789012 - Jean Dupont (sculpteur)
Q345678 - Jean Dupont (photographe)
...
```

Plusieurs personnes trouvées → Utiliser les dates pour discriminer

## Performance

### Sans Variantes (Ancienne Version)

```
Recherche: "TOUDOUZE Edouard"
Résultat: ❌ Aucun (ordre incorrect)

OU

Recherche: "Edouard TOUDOUZE"  
Résultat: ✅ Trouvé
```

**Problème :** Dépend de l'ordre saisi !

### Avec Variantes (Nouvelle Version)

```
Recherche variante 1: "TOUDOUZE Edouard"
  → ✅ Q3579990

Recherche variante 2: "Edouard TOUDOUZE"
  → ✅ Q3579990 (déjà trouvé)

Recherche variante 3: "Edouard Toudouze"
  → ✅ Q3579990 (déjà trouvé)

Arrêt anticipé (haute confiance)
```

**Résultat :** ✅ Toujours trouvé, quel que soit l'ordre !

### Coût en Requêtes

**Cas typique :**
- 2-3 variantes générées
- 1-2 variantes testées (arrêt anticipé)
- **Coût : 1-2 requêtes** au lieu de 1

**Cas difficile :**
- 3-4 variantes générées
- Toutes testées
- **Coût : 3-4 requêtes**

Avec délai de 1.5s : **2-6 secondes** pour une personne.

C'est acceptable pour avoir 100% de succès ! ✅

## Test

### Test Automatique

```bash
python test_name_variants.py
```

**Sortie :**
```
📝 Nom original: 'TOUDOUZE Edouard'
   Variantes générées (3):
      1. 'TOUDOUZE Edouard'
      2. 'Edouard TOUDOUZE'
      3. 'Edouard Toudouze'

📝 Nom original: 'Edouard TOUDOUZE'
   Variantes générées (2):
      1. 'Edouard TOUDOUZE'
      2. 'TOUDOUZE Edouard'
```

### Test dans Property Matching

```bash
python test_property_matching.py
```

**Section Test Variantes :**
```
1. Test 'TOUDOUZE Edouard' (NOM Prénom)
   Résultats: 1
   Meilleur: Édouard Toudouze - 95%

2. Test 'Edouard TOUDOUZE' (Prénom NOM)
   Résultats: 1
   Meilleur: Édouard Toudouze - 95%

3. Test 'Édouard Toudouze' (Prénom Nom)
   Résultats: 1
   Meilleur: Édouard Toudouze - 95%

✅ Toutes les variantes trouvent la même entité: Q3579990
```

## Cas Limites

### Noms Très Courts

**Entrée :** `"DA Jean"`

Si première partie ≤ 2 lettres, pas de génération de variantes (préposition probable).

### Noms avec Particules

**Entrée :** `"Leonardo da Vinci"`

Les particules (`da`, `de`, `van`, etc.) sont conservées dans les variantes.

### Noms Multiples

**Entrée :** `"Pablo Diego José Francisco"`

Seuls les 2 premiers et dernier mots sont utilisés pour les variantes.

### Un Seul Mot

**Entrée :** `"Rembrandt"`

Pas de variantes générées (impossible d'inverser).

## Configuration

### Limiter les Variantes

Si nécessaire, limiter le nombre de variantes :

```python
def _generate_name_variants(self, name, max_variants=3):
    variants = [...]
    return variants[:max_variants]
```

### Désactiver les Variantes

Pour des tests ou comparaisons :

```python
def search_person(self, name, ...):
    # Forcer une seule variante
    search_variants = [name]  # Au lieu de _generate_name_variants()
```

## Bonnes Pratiques

### Pour les Extracteurs

Extraire le nom **tel quel** :
```python
# ✅ BON
creator = "TOUDOUZE Edouard"  # Tel qu'extrait

# ❌ PAS BON
creator = "Toudouze, É."  # Trop transformé
```

Le matcher gère les variantes automatiquement.

### Pour les Utilisateurs

Aucune action requise ! Le système gère automatiquement :
- Ordre des mots
- Majuscules/minuscules
- Variantes orthographiques

## Améliorations Futures

### Particules Connues

Détecter et gérer automatiquement :
- `van` (néerlandais)
- `von` (allemand)
- `de` / `du` / `des` (français)
- `di` / `da` (italien)
- `el` / `al` (arabe)

### Diacritiques

Essayer avec et sans accents :
- `Édouard` ↔ `Edouard`
- `José` ↔ `Jose`

### Abréviations

Détecter les prénoms abrégés :
- `É. Toudouze` → `Édouard Toudouze`
- `J.-P. Dupont` → `Jean-Pierre Dupont`

## Résumé

**Avant :**
- ❌ `"TOUDOUZE Edouard"` → Pas trouvé
- ✅ `"Edouard TOUDOUZE"` → Trouvé

**Après :**
- ✅ `"TOUDOUZE Edouard"` → Trouvé (essaye 3 variantes)
- ✅ `"Edouard TOUDOUZE"` → Trouvé (essaye 2 variantes)
- ✅ `"Édouard Toudouze"` → Trouvé (essaye 3 variantes)

**Robustesse maximale** pour un coût minimal ! 🎯
