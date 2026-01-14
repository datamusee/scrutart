# Exemples de descriptions d'images pour Piwigo

Pour que l'outil puisse détecter les doublons, les descriptions de vos images dans Piwigo doivent contenir le nom du créateur.

## ✅ Formats valides

### Format simple
```
Créateur: Jean Dupont
```

### Format avec deux-points et espace
```
Créateur : Marie Martin
```

### Format dans une description plus longue
```
Belle photo de paysage au coucher du soleil.
Créateur: Pierre Durant
Prise en juillet 2025.
```

### Format avec d'autres informations
```
Titre: Montagne enneigée
Créateur: Sophie Leblanc
Lieu: Alpes françaises
Date: 15/12/2024
```

## ❌ Formats non reconnus

### Sans le mot "Créateur"
```
Auteur: Jean Dupont  ❌ (ne sera pas détecté)
Par: Marie Martin    ❌ (ne sera pas détecté)
```

### Mal orthographié
```
Createur: Pierre     ❌ (manque l'accent)
Creator: Sophie      ❌ (en anglais)
```

## 🎯 Recommandations

1. **Utilisez toujours "Créateur:"** (avec ou sans espace après les deux-points)
2. **Soyez cohérent** dans l'orthographe des noms de créateurs
3. **Un créateur par image** (l'outil prend le premier trouvé)
4. **Titre identique** pour que deux images soient considérées comme doublons

## 📝 Exemple complet de doublon

### Image 1
- **Titre**: `Coucher de soleil`
- **Description**: `Créateur: Jean Dupont`

### Image 2
- **Titre**: `Coucher de soleil`
- **Description**: `Créateur: Jean Dupont`

👉 Ces deux images seront détectées comme doublons car :
- Même créateur : "Jean Dupont"
- Même titre : "Coucher de soleil"

## 🔄 Mise à jour en masse

Pour ajouter le champ "Créateur" à plusieurs images :

1. Dans Piwigo, allez dans "Gestion des photos"
2. Sélectionnez plusieurs photos
3. Utilisez "Édition unitaire" ou "Édition par lot"
4. Ajoutez "Créateur: [Nom]" dans la description
5. Sauvegardez

## 💡 Astuce

Si vos créateurs sont déjà stockés ailleurs (dans les tags, le nom de fichier, etc.), vous pouvez créer un script pour extraire cette information et l'ajouter automatiquement dans les descriptions via l'API Piwigo.

---

**Bon formatage ! 📝**
