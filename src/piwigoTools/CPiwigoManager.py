from piwigoConfigPrivee import configPiwigo
import datetime
import logging
import requests
import configPiwigo as cp  # Assure-toi que ce module est bien défini

class CPiwigoManager():
    def __init__(self, url="https://galeries.grains-de-culture.fr"):
        self.session = None
        self.url = url
        # --- Configuration ---
        self.PIWIGO_API_URL = "https://galleries.grains-de-culture.fr/ws.php"
        self.USER_AGENT = 'Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)'

        # --- Logging ---
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.token = None
        pass

    # --- Fonctions utilitaires ---

    def select_best_image(self, image_urls):
        """Choisit la meilleure image en se basant sur la taille (Content-Length)."""
        best_url = None
        best_size = 0
        headers = {'User-Agent': self.USER_AGENT}

        for url in image_urls:
            try:
                response = requests.head(url, headers=headers, allow_redirects=True)
                size = int(response.headers.get("Content-Length", 0))
                if size > best_size:
                    best_size = size
                    best_url = url
            except Exception as e:
                self.logger.warning(f"Erreur lors de la vérification de {url} : {e}")
        return best_url or (image_urls[0] if image_urls else None)

    def build_description(self, image_url, creator_url, creator_label, wikidata_uri, lang="fr"):
        qid = wikidata_uri.replace("http://www.wikidata.org/entity/", "")
        if lang == "en":
            return (
                f"Creator: <a href='{creator_url}'>{creator_label}</a>"
                f"<div>Source: Wikimedia Commons <a href='{image_url}'>{image_url}</a></div>"
                f"<div>Wikidata item <a href='{wikidata_uri}'>{qid}</a></div>"
            )
        else:
            return (
                f"Créateur: <a href='{creator_url}'>{creator_label}</a>"
                f"<div>Source Wikimedia Commons <a href='{image_url}'>{image_url}</a></div>"
                f"<div>Élément Wikidata <a href='{wikidata_uri}'>{qid}</a></div>"
            )

    def piwigo_login(self, session):
        payload = {
            "format": "json",
            "method": "pwg.session.login",
            "username": cp.configPiwigo["login"],
            "password": cp.configPiwigo["pass"],
        }
        try:
            response = session.post(self.PIWIGO_API_URL, data=payload)
            response.raise_for_status()
            return response.ok
        except Exception as e:
            self.logger.error(f"Erreur de connexion à Piwigo : {e}")
            return False

    def ensure_category_exists(self, session, category_name):
        try:
            response = session.get(f"{self.PIWIGO_API_URL}?format=json&method=pwg.categories.getList")
            response.raise_for_status()
            categories = response.json().get("result", {}).get("categories", [])

            for cat in categories:
                if cat.get("name") == category_name:
                    return cat.get("id")

            # Sinon, on la crée
            payload = {
                "method": "pwg.categories.add",
                "name": category_name,
                "format": "json"
            }
            response = session.post(self.PIWIGO_API_URL, data=payload)
            response.raise_for_status()
            new_id = response.json()["result"]["id"]
            self.logger.info(f"Catégorie '{category_name}' créée avec l'ID {new_id}")
            return new_id
        except Exception as e:
            self.logger.error(f"Erreur lors de la gestion des catégories : {e}")
            raise Exception(f"Erreur lors de la gestion de la catégorie {category_name} : {e}")

    def openSession(self):
        if not self.session:
            self.session = requests.Session()
            if not self.piwigo_login(self.session):
                self.session = None
                self.logger.error("Échec de la connexion à Piwigo.")
                raise Exception("Sorry, fails to connect to Piwigo.")
            else:
                payload = {
                    "method": "pwg.session.getStatus",
                    "format": "json"
                }
                res = self.session.get(self.PIWIGO_API_URL + "?format=json&method=pwg.session.getStatus", data=payload)
                res.raise_for_status()
                self.token = res.json().get("result", None).get("pwg_token", None)
                pass

    # --- Fonction principale ---

    def select_image_to_post(self, artwork_description):
        image_urls = artwork_description.get("images", [])
        if not image_urls:
            self.logger.error("Aucune image trouvée.")
            raise Exception("Pas trouvé d'image à envoyer.")

        best_image_url = self.select_best_image(image_urls)
        self.logger.info(f"Image sélectionnée : {best_image_url}")

        headers = {'User-Agent': self.USER_AGENT}  # useful for Wikimedia Commons
        image_response = requests.get(best_image_url, headers=headers)
        image_response.raise_for_status()
        image_data = image_response.content
        return best_image_url, image_data

    def post_image_to_piwigo(self, artwork_description, category_name="Galerie de tests", lang="fr"):
        try:
            best_image_url, image_data = self.select_image_to_post(artwork_description)
            self.openSession()

            # Création ou récupération de la catégorie
            category_id = self.ensure_category_exists(self.session, category_name)

            titre = artwork_description.get("titre_" + lang, artwork_description.get("titre_fr", "Sans titre"))
            uri = artwork_description.get("uri", "")
            crea = artwork_description.get("createur", "#")
            crea_label = artwork_description.get("createurLabel", "Créateur inconnu")

            description = self.build_description(best_image_url, crea, crea_label, uri, lang)

            payload = {
                "method": "pwg.images.addSimple",
                "category": category_id,
                "name": titre,
                "comment": description,
                "tags": category_name,
            }

            files = {'image': (best_image_url.split("/")[-1], image_data, 'image/jpeg')}

            self.logger.info(f"Envoi de l'image '{titre}' à Piwigo...")
            response = self.session.post(f"{self.PIWIGO_API_URL}?format=json", data=payload, files=files)

            if response.ok:
                self.logger.info(f"L'image '{titre}' a été envoyée avec succès ! - {response.text}")
                return response
            else:
                self.logger.error(f"Erreur lors de l'envoi : {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.exception(f"Erreur inattendue lors de l'envoi de l'image : {e}")
            return None

    def imageSetCategory(self, image_id, category_id):
        # limited wrapper to the setCategory method of the Piwigo API
        try:
            self.openSession()
            payload = {
                "method": "pwg.images.setCategory",
                "category_id": category_id,
                "action": "associate",
                "image_id": image_id,
                "pwg_token": self.token
            }
            response = self.session.post(self.PIWIGO_API_URL + "?format=json&method=pwg.images.setCategory", data=payload)
            if response.status_code == 200:
                print(f"L'image '{image_id}' a été associée à la catégorie {category_id} avec succès! ({datetime.datetime.now()})")
                return response
            else:
                print("Erreur :", response.status_code, response.text)
                return None
        except Exception as e:
            self.logger.exception(f"Erreur inattendue lors de l'envoi de l'image : {e}")
            return None

    def imageGetCategories(self, image_id):
        # limited wrapper to the setCategory method of the Piwigo API
        if not image_id:
            self.logger.exception(f"Erreur d'image désignée par un id=None")
            return None
        try:
            self.openSession()
            payload = {
                "method": "pwg.images.getInfo",
                "image_id": image_id,
                "pwg_token": self.token
            }
            response = self.session.get(self.PIWIGO_API_URL + f"?format=json&method=pwg.images.getInfo&image_id={image_id}", data=payload)
            if response.status_code == 200:
                data = response.json().get("result")
                categories = None
                if data and ("categories" in data):
                    categories = [ str(cat["id"])  for cat in data["categories"] ]
                    print(f"L'image '{image_id}' est associée aux catégories {categories}. ({datetime.datetime.now()})")
                return categories
            else:
                print("Erreur :", response.status_code, response.text)
                return None
        except Exception as e:
            self.logger.exception(f"Erreur inattendue lors de l'envoi de l'image : {e}")
            return None
