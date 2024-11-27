import requests
import configPiwigo as cp

# URL de l'API Piwigo
url = "https://galleries.grains-de-culture.fr/ws.php"

# Données pour l'authentification
auth_data = {
    "username": cp.configPiwigo["login"],
    "password": cp.configPiwigo["pass"]
}

# Paramètres pour créer un album
payload = {
    "method": "pwg.categories.add",
    "name": "Album test",
    "comment": "Album dédié à des tests, notamment d'accès via l'API",
    "parent": "",  # Laissez vide pour un album racine ou indiquez l'ID de l'album parent
    "public": "false"  # true pour public, false pour privé
}

# Envoyer la requête
response = requests.post(url, data={**auth_data, **payload})

# Vérification de la réponse
if response.ok:
    print("Album créé avec succès !")
    print(response.json())  # Affiche les détails de l'album créé
else:
    print("Erreur lors de la création de l'album :", response.text)


# Informations d'authentification
auth_data = {
    "format": "application/json",
    "method": "pwg.session.login",
    "username": cp.configPiwigo["login"],
    "password": cp.configPiwigo["pass"],
}

payload = {
    "format": "json",
    "method": "pwg.session.login",
    "username": cp.configPiwigo["login"],
    "password": cp.configPiwigo["pass"],
}

# Ouvrir une session avec l'API pour se connecter
session = requests.Session()  # Crée une session persistante

# Envoyer la requête de connexion
response = session.post(url, data={**auth_data, **payload})

# Vérifier si la connexion a réussi
if response.ok: # and response.json().get("stat") == "ok":
    print("Connexion réussie!")

    # Maintenant que la session est active, vous pouvez créer un album
    payload = {
        "format":"json",
        "method": "pwg.categories.add",
        "name": "album 2 test via api",
        "comment": "Description de l'album",
        "parent": "",  # Mettre l'ID du parent si souhaité
        "public": "true",
    }

    # Envoyer la requête pour créer l'album
    create_album_response = session.post(url, data=payload)

    if create_album_response.ok:
        print("Album créé avec succès !")
        print(create_album_response.json())  # Affiche les détails de l'album
    else:
        print("Erreur lors de la création de l'album :", create_album_response.text)

else:
    print("Échec de la connexion :", response.text)
