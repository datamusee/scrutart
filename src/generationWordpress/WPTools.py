import src.generationWordpress.configPrivee2 as configPrivee
import base64
import requests
import tempfile
import os

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

    def getWPPages(self, page_title=None, status="publish, draft, future", perPage=10, page=0):
        api_url = f"{self.configPrivee.WORDPRESS_O2_API_URL}/pages"

        # Paramètres de requête pour filtrer par titre de la page
        params = {
            # 'search': page_title,
            'page': page,
            'per_page': perPage,
            'status': status,
            "search_columns": "post_title",
            "Authorization": "Bearer" + str({self.configPrivee.WORDPRESS_O2_PASSWORD_APP})
        }
        if page_title:
            params["search"] = page_title
        try:
            # Effectuer la requête GET à l'API REST de WordPress
            response = requests.get(self.api_url_get, params=params, auth=self.auth)
            response.raise_for_status()  # Vérifie si la requête a réussi

            pages = response.json()
            return pages

        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la requête: {e}")
            return None

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

    def upload_image_in_wp_media(self, image_url, titre=None):
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
                        # print(f"Échec de l'envoi, code HTTP : {response.status_code}")
                        # print(f"Détails : {response.text}")
                        return None
                os.remove(temp_image_path)
            except Exception as e:
                # print(f"Erreur lors de l'envoi de l'image : {e}")
                return None
        else:
            return None


    def set_featured_image(self, post_id, image_id):
        """Sets the uploaded image as the featured image of a post."""
        api_url = f"{self.api_url_get}/{post_id}?Authorization=Bearer{self.api_password}"
        username = self.api_username
        password = self.api_password
        # Encode le nom d'utilisateur et le mot de passe en base64 pour l'authentification
        credentials = f"{username}:{password}"
        token = base64.b64encode(credentials.encode())
        headers = {
            "Authorization": f"Basic {token.decode('utf-8')}"
        }
        data = {"featured_media": image_id}
        auth = (self.api_username, self.api_password)
        response = requests.post(api_url, json=data, auth=auth, headers=headers)
        if response.status_code == 200:
            # print(f"Featured image set successfully for post ID: {post_id}")
            pass
        else:
            # print(f"Failed to set featured image: {response.text}")
            pass

    def sendImageAndSetItAsFeaturedImage(self, post_id, image_url):
        image_id = self.upload_image_in_wp_media(image_url)
        if image_id:
            self.set_featured_image(post_id, image_id)
        return image_id

if __name__ == '__main__':
    # Exemple d'utilisation
    wpt = WPTools(configPrivee)
    pages = wpt.getWPPages()

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
