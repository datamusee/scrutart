import requests
import configPiwigo as cp
import datetime
import json
import time

def postImageToPiwigo(im):
    image_path = im["image"]
    hh = { 'User-Agent': 'Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)'}
    image_response = requests.get(image_path, headers=hh)
    image_data = image_response.content

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
        # print("Connexion réussie!")
        titre = im["titre_fr"]
        uri = im["uri"]
        qid = uri.replace("http://www.wikidata.org/entity/", "")
        crea = im["createur"]
        creaLab = im["createurLabel"]
        categorie_id = 15  # ID de la catégorie dans laquelle ajouter l'image
        # todo ajouter nom créateur dans description
        # todo gérer description multilingue
        description = f"""Créateur: <a href="{crea}">{creaLab}</a><div>Source Wikimedia Commons <a href='{image_path}'>{image_path}</a></div><div>Elément Wikidata <a href='{uri}'>{qid}</a></div>"""
        tags = ["portrait"]  # Liste des tags à associer à l'image

        # Authentification et envoi de l'image avec des métadonnées
        payload = {
            "image": image_path,
            "method": "pwg.images.addSimple",
            "category": categorie_id,
            "name": titre,
            "comment": description,
            "tags": ",".join(tags),  # Convertir la liste de tags en une chaîne séparée par des virgules
        }
        # Construire les données de la requête avec la pièce jointe
        files = {'image': (image_path, image_data, 'image/jpeg')}
        print(f"L'image '{titre}' va être envoyée !")
        response = session.post(
            piwigo_base_url + "?format=json&method=pwg.images.addSimple",
            data=payload,
            files=files
        )
        # todo ajouter des logs
        if response.status_code == 200:
            print(f"L'image '{titre}' a été téléchargée avec succès et les métadonnées ont été ajoutées !")
            print(datetime.datetime.now())
            return True
        else:
            print("Erreur :", response.status_code, response.text)
            return False

if __name__=="__main__":
    listimagespath = "D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/listeImagesPortrait.json"
    listim = []
    with open(listimagespath, "r", encoding="UTF-8") as fdata:
        data = json.loads(fdata.read())
        listim = data["liste"]
    if listim:
        print(datetime.datetime.now())
        for idx, im in enumerate(listim[77:1007]):
            if not "posted" in im:
                res = postImageToPiwigo(im)
                if res:
                    im["posted"] = True
                    listim[idx] = im
                time.sleep(300)
            with open(listimagespath, "w", encoding="UTF-8") as fdata:
                data["liste"] = listim
                json.dump(data, fdata, ensure_ascii=False)


# La description peut contenir un lien vers l entité source, un lien vers l URL de l image, le copyright
# Il faut limiter l api a n'accepter que certains emetteurs
