import requests
import configPiwigo as cp
import datetime
import json
import time

def createCategoryInPiwigo(categoryName="portrait"):
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
        # todo gérer description multilingue
        # Authentification et envoi de l'image avec des métadonnées
        payload = {
            "status": "private",
            "name": f"Galerie de {categoryName}s",
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

if __name__=="__main__":
    seuil = 600
    listcategoriespath = "D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/listeGenresPeintures.json"
    listcat = []
    with open(listcategoriespath, "r", encoding="UTF-8") as fdata:
        data = json.loads(fdata.read())
        listcat = data
    if listcat:
        print(datetime.datetime.now())
        freqsav = 1
        idxsav = 0
        for cat in listcat:
            if (not "galerie" in cat) and (int(cat["c"])>seuil):
                res = createCategoryInPiwigo(cat["genreLabel"])
                if res:
                    cat["galerie"] = res.text
                    idxsav += 1
                    if idxsav>=freqsav:
                        idxsav = 0
                        with open(listcategoriespath, "w", encoding="UTF-8") as fdata:
                            json.dump(listcat, fdata, ensure_ascii=False)


