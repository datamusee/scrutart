import requests
import base64
import src.generationWordpress.configPrivee2 as configPrivee
import mimetypes

# Configuration de base
site_url = configPrivee.WORDPRESS_O2_API2_URL
api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
auth = (configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP)
api_endpoint = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
username = configPrivee.WORDPRESS_O2_API2USERNAME
password = configPrivee.WORDPRESS_O2_API2PASSWORD_APP
# Encode le nom d'utilisateur et le mot de passe en base64 pour l'authentification
credentials = f"{username}:{password}"
token = base64.b64encode(credentials.encode())

# Chemin du fichier média à uploader
image_url = "https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/12/Monet.jpg"
file_name = "Flower"
#image_url = "https://commons.wikimedia.org/wiki/File:Monet_-_Impression,_Sunrise.jpg" # image issue de commons
#file_name = "Impression, soleil levant"
#image_url = "https://upload.wikimedia.org/wikipedia/commons/1/1d/Dance_Dance_Revolution_Extreme_%28Katsucon_2005%29.tif"
#file_name = "Dance.tif"
hh = {'User-Agent': 'Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)'}

# Étape 1 : Télécharger l'image depuis l'URL
image_response = requests.get(image_url, headers=hh)

if image_response.status_code == 200:
    # media_data = image_response.json()
    # image_size = media_data.get("media_details", {}).get("file", "")

    # Vérification de la taille de l'image
    if True:
    #if "filesize" in media_data and media_data["filesize"] < 512 * 1024 * 1024:  # Taille en octets (512 Mo)
        # Préparer le fichier pour l'upload
        acceptedImageFormats = ['jpg','jpeg','png','gif','webp','tif','tiff', 'eps', 'svg', 'psd', 'ai']
        filetype = mimetypes.guess_type(image_url)[0]
        extension = mimetypes.guess_extension(filetype).replace(".", "")
        if extension in acceptedImageFormats:
            files = {
                "file": (file_name, image_response.content)  # Remplacez par le type MIME correct si nécessaire
            }
            headers = {
                "Content-Type": f"{filetype}",
                # "Content-Type": "image/jpeg",
                "Content-Disposition": f"attachment; filename={file_name}",
            }
            api_media_url = f"{configPrivee.WORDPRESS_O2_API_URL}/media"
            media_response = requests.post(
                api_media_url,
                auth=(configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP),
                headers=headers,
                data=image_response.content
            )

            # Gestion de la réponse
            if media_response.status_code == 201:
                # L'injection a réussi
                print("Média ajouté avec succès !")
                print("URL du média :", media_response.json().get("source_url"))
                media_id = media_response.json().get("id")
                print("Média ajouté avec succès ! ID du média :", media_id)
                # Étape 2 : Mettre à jour la page avec cet ID pour définir l'image "à la une"
                page_id = 770  # Remplacez par l'ID de la page ou de l'article
                api_page_url = f"{configPrivee.WORDPRESS_O2_BASE_URL}/wp-json/wp/v2/posts/{page_id}"

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
            print("Format d'image pas accepté par Piwigo")
    else:
        print("Image trop lourde (plus de 512 Mo)")
else:
    print("Erreur lors du téléchargement de l'image :", image_response.status_code)

