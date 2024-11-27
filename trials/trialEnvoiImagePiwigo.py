import requests
import configPiwigo as cp
import datetime

# URL de l'image à envoyer
# image_url = "https://www.dutchgrown.fr/cdn/shop/files/Dahlia_Orange_Nugget-1.jpg"
image_path = "Image.jpg"

# Téléchargement de l'image depuis l'URL
# image_response = requests.get(image_url)
# image_data = image_response.content

username = cp.configPiwigo["login"]
password = cp.configPiwigo["pass"]

# Informations d'authentification
auth_data = {
    "format": "application/json",
    "method": "pwg.session.login",
    "username": username,
    "password": password,
}

payload = {
    "format": "application/json",
    "method": "pwg.session.login",
    "username": cp.configPiwigo["login"],
    "password": cp.configPiwigo["pass"],
}

# Ouvrir une session avec l'API pour se connecter
session = requests.Session()  # Crée une session persistante

# Envoyer la requête de connexion
piwigo_base_url = "https://galleries.grains-de-culture.fr/ws.php"
response = session.post(piwigo_base_url, data=auth_data)

# Vérifier si la connexion a réussi
if response.ok: # and response.json().get("stat") == "ok":
    print("Connexion réussie!")

    # Métadonnées de l'image
    titre = "Test avec mon portrait"
    description = "Test description textuelle"
    categorie_id = 15  # ID de la catégorie dans laquelle ajouter l'image
    tags = ["tag1", "tag2", "tag3"]  # Liste des tags à associer à l'image

    # Authentification et envoi de l'image avec des métadonnées
    payload = {
        "image": image_path,
        "method": "pwg.images.addSimple",
        "category": categorie_id,
        "name": titre,
        "comment": description,
        "tags": ",".join(tags),  # Convertir la liste de tags en une chaîne séparée par des virgules
    }
    # Chemin du fichier image à envoyer
    image_path = 'Image.jpg'

    # Ouvrir le fichier en mode binaire
    with open(image_path, 'rb') as img_file:
        # Construire les données de la requête avec la pièce jointe
        files = {'image': (image_path, img_file, 'image/jpeg')}

        # Afficher la réponse du serveur
        print(response.status_code)
        print(response.text)
        # Envoi de la requête avec authentification
        response = session.post(
            piwigo_base_url+"?format=json&method=pwg.images.addSimple",
            data=payload,
            files=files
        )
        # Vérification du succès de l'opération
        if response.status_code == 200:
            print("L'image a été téléchargée avec succès et les métadonnées ont été ajoutées !")
            print(datetime.datetime.now())
        else:
            print("Erreur :", response.status_code, response.text)

# La description peut contenir un lien vers l entité source, un lien vers l URL de l image, le copyright
# Il faut limiter l api a n accepter que certains emetteurs
