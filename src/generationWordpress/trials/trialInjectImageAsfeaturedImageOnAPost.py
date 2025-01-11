import src.generationWordpress.configPrivee2 as configPrivee
import base64
import requests
import tempfile
import os

"""
How the Code Works
Upload the Image: The upload_image function:
Downloads the image from the given URL.
Uploads it to the WordPress Media Library using the REST API.
Returns the attachment ID of the uploaded image if successful.
Set the Featured Image: The set_featured_image function:

Uses the attachment ID from the upload step to set the featured image for the specified post.
Makes a POST request to update the post's featured_media field.
Authentication: The script uses Basic Authentication with an Application Password. You can generate one from your WordPress profile under Users → Your Profile → Application Passwords.

Important Notes
Security: Avoid hardcoding your credentials in the script for production. Use environment variables or secure vaults instead.
Permissions: Ensure your WordPress user has permissions to upload media and update posts.
SSL: If your WordPress site uses HTTPS and there's a certificate error, you may need to set verify=False in the requests call, but this is not recommended for production due to security risks.
This script helps automate image uploads and setting featured images via the WordPress REST API efficiently.
"""

# Replace with your WordPress site URL and credentials
WP_SITE_URL = "https://scrutart.grains-de-culture.fr"
USERNAME = configPrivee.WORDPRESS_O2_API2USERNAME
APP_PASSWORD = configPrivee.WORDPRESS_O2_API2PASSWORD_APP  # Generated from WordPress user profile

# Post and image details
POST_ID = 770  # post test general
IMAGE_URL = "https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/12/The_Sacrifice_of_Isaac_MET_LC-71_28-11-scaled-e1733824766994-1024x738.jpg"  # URL of the image you want to use

api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
auth = (configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP)

# WordPress site details
wordpress_site_url = "https://scrutart.grains-de-culture.fr"
api_endpoint = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
# api_endpoint = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"

username = configPrivee.WORDPRESS_O2_API2USERNAME
password = configPrivee.WORDPRESS_O2_API2PASSWORD_APP


def download_image_to_tempfile(url):
    try:
        # Envoyer une requête GET à l'URL de l'image
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Vérifier si la requête a réussi

        # Créer un fichier temporaire
        temp_file = tempfile.NamedTemporaryFile(delete=False,
                                                suffix=".jpg")  # Ajoutez une extension adaptée à l'image (ex: .jpg, .png)

        # Écrire le contenu de l'image dans le fichier temporaire
        with open(temp_file.name, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Image téléchargée avec succès dans : {temp_file.name}")
        return temp_file.name  # Retourne le chemin du fichier temporaire
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors du téléchargement de l'image : {e}")
        return None




def upload_image(image_url, wp_site_url, username, app_password):
    """Uploads an image to WordPress Media Library and returns the attachment ID."""
    image_url = "https://scrutart.grains-de-culture.fr/wp-content/uploads/2025/01/Rafael20-20Retrato20de20Pietro20Perugino1-scaled.jpg"
    temp_image_path = download_image_to_tempfile(image_url)
    if temp_image_path:
        try:
            # Ouvrir l'image temporaire pour l'envoi
            with open(temp_image_path, 'rb') as image_file:
                upload_url = f"{wp_site_url}/wp-json/wp/v2/media"
                auth = (configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP)
                # image_info = {'file': image_data_file}
                image_info = {'file': ('image.jpg', image_file, 'image/jpeg')}
                response = requests.post(upload_url, files=image_info, auth=auth)
                # Vérifier si le POST a réussi
                if (response.status_code == 200) or (response.status_code == 201):
                    print("Image envoyée avec succès !")
                    image_id = response.json()["id"]
                    print(f"Image uploaded successfully! Attachment ID: {image_id}")
                    return image_id
                else:
                    print(f"Échec de l'envoi, code HTTP : {response.status_code}")
                    print(f"Détails : {response.text}")
                    return None
            os.remove(temp_image_path)
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'image : {e}")
    else:
        return None

def set_featured_image(post_id, image_id, wp_site_url, username, app_password):
    """Sets the uploaded image as the featured image of a post."""
    site_url = configPrivee.WORDPRESS_O2_BASE_URL
    api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts/{post_id}?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
    username = configPrivee.WORDPRESS_O2_API2USERNAME
    password = configPrivee.WORDPRESS_O2_PASSWORD_APP
    # Encode le nom d'utilisateur et le mot de passe en base64 pour l'authentification
    credentials = f"{username}:{password}"
    token = base64.b64encode(credentials.encode())
    headers = {
        "Authorization": f"Basic {token.decode('utf-8')}"
    }
    data = {"featured_media": image_id}

    auth = (configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP)

    response = requests.post(api_url, json=data, auth=auth, headers=headers)
    # response = requests.post(update_url, json=data, auth=HTTPBasicAuth(username, app_password))

    if response.status_code == 200:
        print(f"Featured image set successfully for post ID: {post_id}")
    else:
        print(f"Failed to set featured image: {response.text}")

# Main logic
def sendImageAndSetItAsFeaturedImage(post_id, image_url, wp_site_url, user, pwd):
    image_id = upload_image(image_url, wp_site_url, user, pwd)
    if image_id:
        set_featured_image(post_id, image_id, wp_site_url, user, pwd)

if __name__ == "__main__":
    sendImageAndSetItAsFeaturedImage(POST_ID, IMAGE_URL, WP_SITE_URL, USERNAME, APP_PASSWORD)
