# 🔍 Guide de Débogage - Détection des Doublons

## Problème : Aucun doublon n'est détecté

Si l'application ne trouve aucun doublon alors que vous savez qu'il y en a, suivez ce guide pas à pas.

## Étape 1 : Vérifier le format des descriptions

### Ce que recherche l'application

L'application cherche dans la description de chaque image :

1. Le mot "**Créateur**" (avec ou sans accent, majuscules/minuscules)
2. Suivi de "**:**" ou "**:**" (deux-points avec ou sans espace)
3. Puis une balise `<a>` contenant le nom, OU le nom en texte simple

### Formats reconnus ✅

```html
Créateur: <a href="#">Jean Dupont</a>
Créateur : <a href="/tag/123">Marie Martin</a>
Créateur: <a>Pierre Durant</a>
Créateur: Sophie Leblanc
```

### Formats NON reconnus ❌

```html
Auteur: Jean Dupont          (mauvais mot-clé)
Creator: Marie Martin        (en anglais)
Par Jean Dupont              (pas de mot-clé)
createur: Pierre             (sans accent)
Créateur Jean Dupont         (manque les deux-points)
```

## Étape 2 : Utiliser les outils de débogage

### Outil 1 : test_api.py

Exporte les données réelles de votre Piwigo pour les analyser.

```bash
python test_api.py
```

**Ce qu'il fait :**
1. Vous connecte à votre Piwigo
2. Liste vos albums
3. Vous permet de choisir un album
4. Exporte toutes les images dans un fichier JSON
5. Affiche les 5 premières images avec leurs descriptions complètes

**Résultat :** Un fichier `album_XXX_images.json` contenant toutes les données.

### Outil 2 : debug_duplicates.py

Analyse les données et montre exactement ce qui est détecté.

```bash
python debug_duplicates.py
```

**Ce qu'il fait :**
1. Teste l'extraction du créateur avec différents formats
2. Teste avec des données d'exemple
3. Vous demande le fichier JSON à analyser (celui créé par test_api.py)
4. Affiche pour chaque image :
   - Le titre
   - La description complète
   - Le créateur extrait
   - La clé de groupement utilisée
   - Pourquoi elle est ignorée (si c'est le cas)

**Exemple de sortie :**

```
=== Analyse de 10 images ===

Image ID: 123
  Titre: 'Coucher de soleil'
  Description: Créateur: <a href="#">Jean Dupont</a>
  Créateur extrait: 'Jean Dupont'
  Clé de groupement: ('jean dupont', 'coucher de soleil')

Image ID: 124
  Titre: 'Coucher de soleil'
  Description: Belle photo
  Créateur extrait: 'None'
  ⚠️  Ignorée (créateur ou titre manquant)

=== Résumé ===
Images analysées: 10
Groupes créés: 5
Groupes avec doublons: 1

Groupe 1: 2 images
  Titre: 'Coucher de soleil'
  Créateur: 'Jean Dupont'
  IDs: [123, 125]
```

## Étape 3 : Cas courants et solutions

### Cas 1 : Le créateur est dans un format non supporté

**Symptôme :** L'outil montre "Créateur extrait: 'None'"

**Solution :**
1. Regardez la description complète dans la sortie de debug_duplicates.py
2. Vérifiez le format exact
3. Modifiez les descriptions dans Piwigo pour utiliser un format supporté

### Cas 2 : Les titres ne sont pas exactement identiques

**Symptôme :** Les clés de groupement sont différentes

**Exemple :**
- Image 1 : `'coucher de soleil'`
- Image 2 : `'coucher de soleil '` (espace à la fin)
- Image 3 : `'Coucher De Soleil'` (majuscules différentes)

**Solution :** L'application normalise déjà les espaces et la casse, mais vérifiez qu'il n'y a pas de caractères invisibles ou de différences subtiles.

### Cas 3 : Les créateurs ne sont pas exactement identiques

**Symptôme :** Les clés de groupement montrent des créateurs différents

**Exemple :**
- Image 1 : `'Jean Dupont'`
- Image 2 : `'Jean  Dupont'` (double espace)
- Image 3 : `'Jean DUPONT'`

**Solution :** L'application normalise les espaces et la casse, mais vérifiez l'orthographe exacte.

### Cas 4 : Le créateur est dans les tags, pas dans la description

**Symptôme :** La description est vide ou ne contient pas "Créateur:"

**Solution :** Dans Piwigo, ajoutez le créateur dans la description :
1. Allez dans "Gestion des photos"
2. Sélectionnez les photos concernées
3. Utilisez "Édition unitaire" ou un script
4. Ajoutez `Créateur: <a href="#">[Nom]</a>` dans la description

## Étape 4 : Modifier les descriptions en masse

Si vous avez beaucoup d'images à corriger, vous pouvez :

### Option A : Via l'interface Piwigo
1. Gestion → Photos
2. Filtrer par album
3. Sélection multiple
4. Édition par lot
5. Ajouter le texte dans la description

### Option B : Via un script Python (avancé)

```python
import requests

session = requests.Session()
url = "https://votre-site.com/piwigo/ws.php?format=json"

# Se connecter
session.post(url, data={
    'method': 'pwg.session.login',
    'username': 'admin',
    'password': 'votre_mot_de_passe'
})

# Récupérer le token
response = session.post(url, data={'method': 'pwg.session.getStatus'})
token = response.json()['result']['pwg_token']

# Mettre à jour une image
session.post(url, data={
    'method': 'pwg.images.setInfo',
    'image_id': 123,
    'comment': 'Créateur: <a href="#">Nom du Créateur</a>',
    'pwg_token': token
})
```

## Étape 5 : Vérifier dans l'application

1. Relancez l'application Flask : `python app.py`
2. Rechargez la page dans le navigateur
3. Scannez à nouveau l'album
4. Regardez les logs dans le terminal Python pour voir les messages de debug

## Logs de debug dans le terminal

Quand vous scannez un album, le terminal Python affiche :

```
=== Analyse de 50 images ===
Image 123: 'Coucher de soleil' par 'Jean Dupont'
Image 124: 'Montagne' par 'Marie Martin'
...

=== 3 groupes de doublons trouvés ===
Groupe 1: 2 images - 'Coucher de soleil' par 'Jean Dupont'
Groupe 2: 3 images - 'Plage' par 'Sophie Leblanc'
Groupe 3: 2 images - 'Forêt' par 'Pierre Durant'
```

Si aucun message n'apparaît ou si les créateurs sont "None", c'est qu'il y a un problème de format.

## Support supplémentaire

Si après toutes ces étapes vous ne trouvez toujours pas vos doublons :

1. Créez un fichier avec 2-3 exemples d'images problématiques (copier-coller depuis le JSON)
2. Vérifiez manuellement que ces images ont :
   - Le même titre EXACT
   - Le même créateur EXACT
   - "Créateur:" dans la description

3. Si tout semble correct mais ça ne fonctionne pas, il peut y avoir :
   - Des caractères invisibles (caractères unicode spéciaux)
   - Un encodage de caractères différent
   - Des balises HTML imbriquées non supportées

Dans ce cas, contactez-moi avec un exemple de données (anonymisées si nécessaire).

---

**Bon débogage ! 🔧**
