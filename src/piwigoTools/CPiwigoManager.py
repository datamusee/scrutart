import time
import re
from src.piwigoTools.piwigoConfigPrivee import configPiwigo as cp
import datetime
import logging
import requests

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
            "username": cp["login"],
            "password": cp["pass"],
        }
        try:
            response = session.post(self.PIWIGO_API_URL, data=payload)
            response.raise_for_status()
            return response.ok
        except Exception as e:
            self.logger.error(f"Erreur de connexion à Piwigo : {e}")
            return False

    def piwigo_ensure_category_exists(self, category_name):
        try:
            self.piwigo_open_session()
            response = self.session.get(f"{self.PIWIGO_API_URL}?format=json&method=pwg.categories.getList")
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
            response = self.session.post(self.PIWIGO_API_URL, data=payload)
            response.raise_for_status()
            new_id = response.json()["result"]["id"]
            self.logger.info(f"Catégorie '{category_name}' créée avec l'ID {new_id}")
            return new_id
        except Exception as e:
            self.logger.error(f"Erreur lors de la gestion des catégories : {e}")
            raise Exception(f"Erreur lors de la gestion de la catégorie {category_name} : {e}")

    def piwigo_open_session(self):
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

    def piwigo_post_image(self, artwork_description, category_name="Galerie de tests", lang="fr"):
        try:
            best_image_url, image_data = self.select_image_to_post(artwork_description)
            self.piwigo_open_session()

            # Création ou récupération de la catégorie
            category_id = self.piwigo_ensure_category_exists(self.session, category_name)

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

    def piwigo_image_set_category(self, image_id, category_id):
        # limited wrapper to the setCategory method of the Piwigo API
        try:
            self.piwigo_open_session()
            payload = {
                "method": "pwg.images.setCategory",
                "category_id": category_id,
                "action": "associate",
                "image_id": image_id,
                "pwg_token": self.token
            }
            response = self.session.post(self.PIWIGO_API_URL + "?format=json&method=pwg.images.setCategory", data=payload)
            if response.status_code == 200:
                # print(f"L'image '{image_id}' a été associée à la catégorie {category_id} avec succès! ({datetime.datetime.now()})")
                return response
            else:
                # print("Erreur :", response.status_code, response.text)
                return None
        except Exception as e:
            self.logger.exception(f"Erreur inattendue lors de l'envoi de l'image : {e}")
            return None

    def piwigo_image_get_categories(self, image_id):
        # limited wrapper to the setCategory method of the Piwigo API
        if not image_id:
            self.logger.exception(f"Erreur d'image désignée par un id=None")
            return None
        try:
            self.piwigo_open_session()
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
            self.logger.exception(f"Erreur inattendue lors de la demande des catégories de l'image {image_id}: {e}")
            time.sleep(1)
            return None

    def piwigo_get_categories(self):
        # Authentification et récupération de la liste des catégories
        try:
            self.piwigo_open_session()
            payload = {
                "format": "json",
                "fullname": "true",
                "tree_output": "true",
                "recursive": "true",
                "method": "pwg.categories.getList",
            }
            # Construire les données de la requête avec la pièce jointe
            response = self.session.get(
                self.PIWIGO_API_URL + "?format=json&method=pwg.categories.getList&recursive=true",
                data=payload
            )
            # todo ajouter des logs
            if response.status_code == 200:
                return response.json()
            else:
                print("Erreur :", response.status_code, response.text)
                return None
        except Exception as e:
            self.logger.exception(f"Erreur inattendue lors de la demande de la liste des catégories: {e}")
            time.sleep(1)
            return None

    def piwigo_create_category(self, categoryName="portrait", categoryType="GENRES"):
        username = cp.configPiwigo["login"]
        password = cp.configPiwigo["pass"]
        auth_data = {
            "format": "application/json",
            "method": "pwg.session.login",
            "username": username,
            "password": password,
        }
        # Ouvrir une session avec l'API pour se connecter
        session = requests.Session()  # Crée une session persistante

        # Envoyer la requête de connexion
        piwigo_base_url = "https://galleries.grains-de-culture.fr/ws.php"
        response = session.post(piwigo_base_url, data=auth_data)
        if response.ok:  # and response.json().get("stat") == "ok":
            galeryNaming = {
                "GENRES": f"Galerie de {categoryName}s",
                "CREATORS": f"Galerie {categoryName}",
                "MOVEMENTS": f"{categoryName}",
                "INSTITUTIONS": f" {categoryName}"
            }
            galeryParent = {
                "GENRES": 81,
                "CREATORS": 80,
                "MOVEMENTS": 853,
                "INSTITUTIONS": 854
            }
            # print("Connexion réussie!")
            # todo gérer description multilingue
            # Authentification et envoi de l'image avec des métadonnées
            # nameFormat = "GENRES"
            payload = {
                "status": "private",
                "name": galeryNaming.get(categoryType, f"Galerie - {categoryName}"),
                "parent": galeryParent.get(categoryType, 856),  # 856=En attente
                "method": "pwg.categories.add",
            }
            # Construire les données de la requête avec la pièce jointe
            print(f"La catégorie '{categoryName}' va être envoyée !")
            response = session.post(
                piwigo_base_url + "?format=json&method=pwg.categories.add",
                data=payload,
            )
            # todo ajouter des logs
            if response.status_code == 200:
                print(f"La catégorie '{categoryName}'  a été créée avec succès !")
                print(datetime.datetime.now())
                return response
            else:
                print("Erreur :", response.status_code, response.text)
                return None

    def buildImageComment(self):
        templates = {
            "IMAGE": {
                "fr": f"{name}",
                "en": f"",
            }
        }

    def buildGaleryComment(self, pwgType, name, scrutartpage="https://scrutart.grains-de-culture.fr/"):
        txtTemplates = {
            "GALERY_GENRE": {
                "fr": #f"""<p>Cette galerie présente des peintures du genre '{name}'. Ces images, libres de droit, ont été sélectionnées à partir de données de Wikidata et d'images de Wikimedia Commons.</p>"""+
                      f"""<p>Une analyse de la présence du genre '{name}' dans Wikidata se trouve dans <a href='{scrutartpage}'>ScrutArt</a>.</p>""" if scrutartpage else "",
                "en": #f"""<p>This gallery shows paintings of the genre '{name}'. These royalty-free images have been selected from Wikidata data and images from Wikimedia Commons.</p>"""+
                        f"""<p>An analysis of genre presence '{name}' in Wikidata can be found in <a href='{scrutartpage}'>ScrutArt</a>.</p>""" if scrutartpage else "",
            },
            "GALERY_MOVEMENT": {
                "fr": f"""Cette galerie présente des peintures du mouvement '{name}'. Ces images, libres de droit, ont été sélectionnées à partir de données de Wikidata et d'images de Wikimedia Commons. Une analyse de la présence du genre '{name}' dans Wikidata se trouve dans <a href='https://scrutart.grains-de-culture.fr/'>ScrutArt</a>.""",
                "en": f"""""",
            },
            "GALERY_CREATOR": {
                "fr": #f"""<p>Cette galerie présente des peintures créées par '{name}'. Ces images, libres de droit, ont été sélectionnées à partir de données de Wikidata et d'images de Wikimedia Commons.</p>"""+
                      f"""<p>Une analyse de la présence des oeuvres de '{name}' dans Wikidata se trouve dans <a href='{scrutartpage}'>ScrutArt</a>.</p>""" if scrutartpage else "",
                "en": #f"""<p>This gallery presents paintings created by '{name}'. These royalty-free images have been selected from Wikidata data and images from Wikimedia Commons.</p>"""+
                      f"""<p>An analysis of the presence of works created by '{name}' in Wikidata can be found in <a href='{scrutartpage}'>ScrutArt</a>.</p>""" if scrutartpage else "",
            }
        }
        msg = f"""
         [lang=all]
             <style> .banniere-analyse {{   display: flex;   align-items: center;   gap: 0.5em;   background: #f8f8f8;   border-left: 3px solid #cccccc;   
                            padding: 1em;   margin: 0em 0;   border-radius: 10px;   font-family: sans-serif;   flex-wrap: wrap; }} 
                    .banniere-analyse-icon {{   font-size: 4em;   color: #007acc; }} 
                    .banniere-analyse-text {{   flex: 1;   min-width: 200px; }} 
                    .banniere-analyse-text a {{   color: #007acc;   text-decoration: underline; }} 
                    @media (max-width: 600px) {{   
                        .banniere-analyse {{     flex-direction: column;     align-items: flex-start;   }} 
                    }}
            </style>
            <div class='banniere-analyse'>   
            <div class='banniere-analyse-text'>
        [/lang]
        """
        template = txtTemplates[pwgType]
        for lang, txt in template.items():
            msg += f"""[lang={lang}]{txt}[/lang]"""
        closingtxt = "[lang=all]</div></div>[/lang]"
        msg += closingtxt
        return msg

    def piwigo_comment_category(self, categoryId, comment):
        try:
            self.piwigo_open_session()
            payload = {
                "method": "pwg.categories.setInfo",
                "comment": comment,
                "category_id": categoryId,
                "pwg_token": self.token
            }
            # todo gérer description multilingue
            # Construire les données de la requête avec la pièce jointe
            # print(f"La catégorie '{categoryId}' va être envoyée !")
            response = self.session.post(
                self.PIWIGO_API_URL + "?format=json&method=pwg.categories.setInfo",
                data=payload
            )
            # todo ajouter des logs
            if response.status_code == 200:
                # print(f"La catégorie '{categoryId}'  a été commentée avec succès !")
                # print(datetime.datetime.now())
                return response, payload["comment"]
            else:
                # print("==========>> Erreur :", response.status_code, response.text)
                return None, "Erreur d'envoi de description (comment)"
        except Exception as e:
            self.logger.exception(f"Erreur inattendue lors de l'envoi de commentaire sur la catégorie {categoryId}: {e}")
            time.sleep(1)
            return None

    def getImageId(res):
        imId = None
        regex = r"image_id[\\]?\":[\"]?(\d+)"
        match = re.search(regex, res)
        if match:
            imId = match.group(1)
        return imId

    def getCategoryId(res):
        catId = None
        regex = r"category\\\/(\d+)"
        match = re.search(regex, res)
        if match:
            catId = match.group(1)
        return catId


if __name__=="__main__":
    # micro test temporatire
    pwg = CPiwigoManager()
    comment = pwg.buildGaleryComment("GALERY_CREATOR", "Test")
    test = pwg.piwigo_comment_category(852, comment)
    pass