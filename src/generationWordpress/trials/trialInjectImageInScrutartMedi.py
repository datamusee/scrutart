import requests
import base64
import src.generationWordpress.configPrivee as configPrivee

# Configuration de base
site_url = configPrivee.WORDPRESS_O2_BASE_URL
api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
auth = (configPrivee.WORDPRESS_O2_USERNAME, configPrivee.WORDPRESS_O2_PASSWORD_APP)
username = configPrivee.WORDPRESS_O2_USERNAME
password = configPrivee.WORDPRESS_O2_PASSWORD_APP
# Encode le nom d'utilisateur et le mot de passe en base64 pour l'authentification
credentials = f"{username}:{password}"
token = base64.b64encode(credentials.encode())
headers = {
    "Authorization": f"Basic {token.decode('utf-8')}"
}

# Chemin du fichier média à uploader
image_url = "https://upload.wikimedia.org/wikipedia/commons/3/3f/JPEG_example_flower.jpg"
file_name = "Monet.jpg"

# Étape 1 : Télécharger l'image depuis l'URL
image_response = requests.get(image_url)

if image_response.status_code == 200:
    media_data = image_response.json()
    image_size = media_data.get("media_details", {}).get("file", "")

    # Vérification de la taille de l'image
    if "filesize" in media_data and media_data["filesize"] < 512 * 1024 * 1024:  # Taille en octets (512 Mo)
        # Préparer le fichier pour l'upload
        files = {
            "file": (file_name, image_response.content, "image/jpeg")  # Remplacez par le type MIME correct si nécessaire
        }
        api_media_url = f"{site_url}/wp-json/wp/v2/media"
        media_response = requests.post(api_media_url, headers=headers, files=files)

        # Gestion de la réponse
        if media_response.status_code == 201:
            # L'injection a réussi
            print("Média ajouté avec succès !")
            print("URL du média :", media_response.json().get("source_url"))
            media_id = media_response.json().get("id")
            print("Média ajouté avec succès ! ID du média :", media_id)
            # Étape 2 : Mettre à jour la page avec cet ID pour définir l'image "à la une"
            page_id = 770  # Remplacez par l'ID de la page ou de l'article
            api_page_url = f"{site_url}/wp-json/wp/v2/posts/{page_id}"

            # Chargement du média comme image "à la une"
            payload = {
                "featured_media": media_id
            }
            response = requests.patch(api_page_url, headers=headers, json=payload)

            # Vérification de la réponse
            if response.status_code == 200:
                print("Image associée à la page avec succès !")
            else:
                print("Erreur lors de la mise à jour de la page :", response.status_code)
                print("Détails de l'erreur :", response.json())
        else:
            # Erreur lors de l'injection du média
            print("Erreur lors de l'ajout du média :", media_response.status_code)
            print("Détails de l'erreur :", media_response.json())
    else:
        print("Image trop lourde (plus de 512 Mo)")
else:
    print("Erreur lors du téléchargement de l'image :", image_response.status_code)

