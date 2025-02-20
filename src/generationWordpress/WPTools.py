import src.generationWordpress.configPrivee2 as configPrivee
import base64
import requests
import tempfile
import os

class WPTools():
    def __init__(self, configPrivee):
        self.configPrivee = configPrivee
        self.wp_site_url = f"{configPrivee.WORDPRESS_O2_BASE_URL}"
        self.api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
        self.api_url_get = f"{configPrivee.WORDPRESS_O2_API_URL}/posts"
        self.api_username = configPrivee.WORDPRESS_O2_API2USERNAME
        self.api_password = configPrivee.WORDPRESS_O2_API2PASSWORD_APP  # Generated from WordPress user profile
        self.auth = (self.api_username, self.api_password)

    def getWPLink(self, title):
        data = {
            "search": title,
            "search_columns": "post_title",
            "Authorization": "Bearer"+str({self.configPrivee.WORDPRESS_O2_PASSWORD_APP})
        }
        response = requests.get(self.api_url_get, params=data, auth=self.auth).json()
        link = None
        if response and "link" in response:
            link = response[0]["link"]
        return link


    def getWPPageUrl(self, page_title, status="publish"):
        api_url = f"{self.configPrivee.WORDPRESS_O2_API_URL}/pages"

        # Paramètres de requête pour filtrer par titre de la page
        params = {
            'search': page_title,
            'status': status,
            "search_columns": "post_title",
            "Authorization": "Bearer" + str({self.configPrivee.WORDPRESS_O2_PASSWORD_APP})
        }

        try:
            # Effectuer la requête GET à l'API REST de WordPress
            response = requests.get(self.api_url_get, params=params, auth=self.auth)
            response.raise_for_status()  # Vérifie si la requête a réussi

            # Analyser les résultats de la requête
            pages = response.json()

            for page in pages:
                # Vérifier si le titre correspond exactement
                if page['title']['rendered'].lower() == page_title.lower():
                    return page['link']  # URL de la page trouvée
            return None  # Aucune page trouvée avec ce titre

        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la requête: {e}")
            return None


    def download_image_to_tempfile(self, url):
        try:
            # Envoyer une requête GET à l'URL de l'image
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Vérifier si la requête a réussi

            # Créer un fichier temporaire
            # TODO tester la nature de l'image et mettre un suffixe approprié
            temp_file = tempfile.NamedTemporaryFile(delete=False,
                                                    suffix=".jpg")  # Ajoutez une extension adaptée à l'image (ex: .jpg, .png)

            # Écrire le contenu de l'image dans le fichier temporaire
            with open(temp_file.name, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return temp_file.name  # Retourne le chemin du fichier temporaire
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors du téléchargement de l'image : {e}")
            return None

    def upload_image(self, image_url, titre=None):
        """Uploads an image to WordPress Media Library and returns the attachment ID."""
        temp_image_path = self.download_image_to_tempfile(image_url)
        if temp_image_path:
            try:
                # Ouvrir l'image temporaire pour l'envoi
                with open(temp_image_path, 'rb') as image_file:
                    upload_url = f"{self.wp_site_url}/wp-json/wp/v2/media"
                    # TODO mettre le MIMETYPE approprié
                    # TODO mettre un titre approprité pour l'image
                    image_info = {'file': (titre if titre else 'image.jpg', image_file, 'image/jpeg')}
                    response = requests.post(upload_url, files=image_info, auth=self.auth)
                    # Vérifier si le POST a réussi
                    if (response.status_code == 200) or (response.status_code == 201):
                        image_id = response.json()["id"]
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

    def set_featured_image(self, post_id, image_id):
        """Sets the uploaded image as the featured image of a post."""
        api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts/{post_id}?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
        # Encode le nom d'utilisateur et le mot de passe en base64 pour l'authentification
        credentials = f"{self.api_username}:{self.api_password}"
        token = base64.b64encode(credentials.encode())
        headers = {
            "Authorization": f"Basic {token.decode('utf-8')}"
        }
        data = {"featured_media": image_id}
        response = requests.post(api_url, json=data, auth=self.auth, headers=headers)
        if response.status_code == 200:
            return True
        else:
            print(f"Failed to set featured image: {response.text}")
        return False

    def sendImageAndSetItAsFeaturedImage(self, post_id, image_url):
        """
        This script helps automate image uploads and setting featured images via the WordPress REST API efficiently.
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
        SSL: If your WordPress site uses HTTPS and there's a certificate error, you may need to set verify=False in the requests call, but this is not recommended for production due to security risks.
        """
        image_id = self.upload_image(image_url)
        if image_id:
            self.set_featured_image(post_id, image_id)
        return image_id

if __name__ == '__main__':
    # Exemple d'utilisation
    import configPrivee
    wpt = WPTools(configPrivee)
    page_titles = [ "Test SVG", "Test bidon", "Où trouver Carolus-Duran dans Wikidata, suivez le guide", "Carolus"]
    # page_titles = [ "Où trouver Carolus-Duran dans Wikidata, suivez le guide" ]

    for title in page_titles:
        page_url = wpt.getWPPageUrl(title)
        if page_url:
            print(f"La page '{title}' est publiée: {page_url}")
        else:
            print(f"La page '{title}' n'est pas publiée")
            page_url = wpt.getWPPageUrl(title, "draft")
            if page_url:
                print(f"La page '{title}' existe comme brouillon: {page_url}")
            else:
                print(f"La page '{title}' n'existe pas.")
        page_url = wpt.getWPPageUrl(title, "publish, draft")
        if page_url:
            print(f"La page '{title}' est publiée ou brouillon: {page_url}")
        else:
            print(f"La page '{title}' n'existe pas")
