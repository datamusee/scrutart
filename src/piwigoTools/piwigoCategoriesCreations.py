import requests
import configPiwigo as cp
import datetime
import json
import time

def createCategoryInPiwigo(categoryName="portrait", categoryType="GENRES"):
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
            "INSTITUTIONS":f" {categoryName}"
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
        #nameFormat = "GENRES"
        payload = {
            "status": "private",
            "name": galeryNaming.get(categoryType, f"Galerie - {categoryName}"),
            "parent": galeryParent.get(categoryType, 856),# 856=En attente
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
    seuilMin = 50
    seuilMax = 600
    # listcategoriespath = "D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/listeGenresPeintures.json"
    listcategoriespath = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\wikidataSignificantPaintersTicket1527.json"
    listcat = []
    with open(listcategoriespath, "r", encoding="UTF-8") as fdata:
        data = json.loads(fdata.read())
        listcat = data
    if listcat:
        print(datetime.datetime.now())
        freqsav = 1
        idxsav = 0
        for cat in listcat:
            if (not "galerie" in cat) and (int(cat["c"])>=seuilMin)  and (int(cat["c"])<=seuilMax):
                res = createCategoryInPiwigo(cat["entityLabel"])
                if res:
                    cat["galerie"] = res.text
                    idxsav += 1
                    if idxsav>=freqsav:
                        idxsav = 0
                        with open(listcategoriespath, "w", encoding="UTF-8") as fdata:
                            json.dump(listcat, fdata, ensure_ascii=False)


