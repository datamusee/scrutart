import requests
import configPiwigo as cp
import datetime
import json
import time

def commentCategoryInPiwigo(catName, categoryId, catFreq):
    strCatFreq = str(catFreq)
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
            "category_id": categoryId,
            "comment": f"Cette galerie présente des peintures du genre '{catName}'. Ces images, libres de droit, ont été sélectionnées à partir de données de Wikidata et d'images de Wikimedia Commons. Une analyse de la présence du genre '{catName}' dans Wikidata se trouve dans <a href='https://scrutart.grains-de-culture.fr/'>ScrutArt</a>. Au 22/11/2024, Wikidata contenait {strCatFreq} peintures de ce genre.",
            "method": "pwg.categories.setInfo",
        }
        # Construire les données de la requête avec la pièce jointe
        print(f"La catégorie '{categoryId}' va être envoyée !")
        response = session.post(
            piwigo_base_url + "?format=json&method=pwg.categories.setInfo",
            data=payload,
        )
        # todo ajouter des logs
        if response.status_code == 200:
            print(f"La catégorie '{categoryId}'  a été commentée avec succès !")
            print(datetime.datetime.now())
            return response, payload["comment"]
        else:
            print("Erreur :", response.status_code, response.text)
            return None, "Erreur d'envoir de description (comment)"

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
            if (int(cat["c"])>seuil):
                catid = json.loads(cat["galerie"])["result"]["id"]
                res, comment = commentCategoryInPiwigo(cat["genreLabel"], catid, cat["c"])
                if res:
                    cat["idpiwigo"] = catid
                    cat["comment"] = comment
                    idxsav += 1
                    if idxsav>=freqsav:
                        idxsav = 0
                        with open(listcategoriespath, "w", encoding="UTF-8") as fdata:
                            json.dump(listcat, fdata, ensure_ascii=False)


