# je pense que ce processus sert à associer des images aux galeries correspondant à leur genre
# donc, ça prend des images déjà dans piwigo, par exemple parce qu'elles ont été associées à un artiste
# et on cherche leur genre et on les associe à la galerie/categorie corres pondante dans piwigo
import re
import requests
import configPiwigo as cp
import datetime
import json
import time
import SPARQLWrapper as sw
import logging
from src.generationWordpress.WikimediaAccess import WikidataObject

def sparqlQuery(endpoint, query, format="json"):
    sparql = sw.SPARQLWrapper2(endpoint)  # implicit JSON format
    logging.debug("SPARQLQUERY " + query)
    sparql.setQuery(query)
    try:
        res = sparql.queryAndConvert()
        return res
    except Exception as e:
        logging.debug(e)

def get_pwg_token(session, urlpiwigo):
    payload = {
        "method": "pwg.session.getStatus",
        "format": "application/json"
    }
    # Authentification et envoi de l'image avec des métadonnées
    status_response = session.post(
        urlpiwigo + "?format=json&method=pwg.images.setCategory",
        data=payload,
    )
    json_response = json.loads(status_response.text)
    token = json_response.get("result", {}).get("pwg_token")
    if status_response.status_code == 200:
        return status_response, token
    else:
        print("Erreur :", status_response.status_code, status_response.text)
        return None, "Erreur de récupération "

def addCategoryToPiwigoImage(categoryId,imageId):
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
        token = get_pwg_token(session, piwigo_base_url)
        # print("Connexion réussie!")
        # todo gérer description multilingue
        # Authentification et envoi de l'image avec des métadonnées
        payload = {
            "category_id": categoryId,
            "image_id": imageId,
            "pwg_token": token,
            "method": "pwg.images.setCategory",
        }
        # Construire les données de la requête avec la pièce jointe
        print(f"La catégorie '{categoryId}' va être ajoutée à l'image {imageId} !")
        response = session.post(
            piwigo_base_url + "?format=json&method=pwg.images.setCategory",
            data=payload,
        )
        # todo ajouter des logs
        if response.status_code == 200:
            print(f"La catégorie '{categoryId}'  a été ajoutée avec succès !")
            print(datetime.datetime.now())
            return response
        else:
            print("Erreur :", response.status_code, response.text)
            return None


def getImageId(im):
    imId = None
    if "pwImId" in im: return im["pwImId"]
    if "post_result" in im:
        if """{"stat":"ok","result":{"image_id":""" in im["post_result"]:
            regex = r"\"image_id\":(\d+)"
            match = re.search(regex, im["post_result"])
            if match:
                imId = match.group(1)
    return imId

if __name__=="__main__":
    sleep = 2
    creatorsToProcess = []
    genresDict = {}
    genreThreshold = 50 # ne pas tenir compte des genres qui ont moins de 50 images
    queryGenres = "select distinct ?genre where { values ?oeuvre { <__ARTWORKENTITY__>} ?oeuvre wdt:P136 ?genre }"
    with open("D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\listeAlbumsCreateurs.json",
              encoding="UTF-8") as albumsCreatorsFile:
        creatorsToProcess = json.load(albumsCreatorsFile)
    with open("D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/listeGenresPeintures.json",
              encoding="UTF-8") as genresFile:
        listGenres = json.load(genresFile)
        for genre in listGenres:
            genresDict[genre["genre"]] = genre
    for creator in creatorsToProcess:
        categoryName = creator["categoryName"]
        piwigoCategory = creator["piwigoCategory"]
        listimagespath = creator["listimagespath"]
        dictim = {}
        with open(listimagespath, "r", encoding="UTF-8") as fdata:
            data = json.loads(fdata.read())
            if (not "version" in data) or (data["version"]=="1.0.1"):
                continue
            dictim = data["dict"]
        if dictim:
            freqsav = 5
            idxsav = 0
            change = False
            for uri, im in dictim.items():
                if ("posted" in im) and (im["posted"]):
                    # find genre(s) avec label in wikidata for the image
                    print(uri)
                    crtquery = queryGenres.replace("__ARTWORKENTITY__", uri)
                    qid = uri.replace("http://www.wikidata.org/entity/", "")
                    wObj = WikidataObject(qid)
                    res = wObj.sparqlQuery(crtquery)
                    if not res: continue
                    genres = [ gr["genre"].value for gr in res.bindings]
                    for genre in genres:
                        if genre in genresDict:
                            if int(genresDict[genre]["c"])>=genreThreshold:
                                #     créer la catégorie si elle n'existe pas et qu'elle est significative? (>=genreThreshold)
                                # ou seulement l'utiliser si elle existe déjà et plutot utiliser categoriesCreations.py pour la créer
                                if "idpiwigo" in  genresDict[genre]:
                                    category_id = genresDict[genre]["idpiwigo"]
                                    imId = getImageId(im)
                                    if imId:
                                        if (not "genres" in im) or (not genre in im["genres"]):
                                            if addCategoryToPiwigoImage(category_id, imId):
                                                if not "genres" in dictim[uri]: dictim[uri]["genres"]=[]
                                                dictim[uri]["genres"].append(genre)
                    time.sleep(sleep)
                    if idxsav>=freqsav:
                        idxsav = 0
                        with open(listimagespath, "w", encoding="UTF-8") as fdata:
                            data["dict"] = dictim
                            json.dump(data, fdata, ensure_ascii=False)
            if change:
                with open(listimagespath, "w", encoding="UTF-8") as fdata:
                    change = False
                    data["dict"] = dictim
                    json.dump(data, fdata, ensure_ascii=False)


# La description peut contenir un lien vers l entité source, un lien vers l URL de l image, le copyright
# Il faut limiter l api a n'accepter que certains emetteurs
