import re
import requests
import configPiwigo as cp
import datetime
import json
import time
import SPARQLWrapper as sw
import logging
from src.generationWordpress.wikidataObject import WikidataObject

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

def setPiwigoImageTagsList(session, imageId, tagIds):
    if session:
        piwigo_base_url = "https://galleries.grains-de-culture.fr/ws.php"
        token = get_pwg_token(session, piwigo_base_url)
        payload = {
            "pwg_token": token,
            "imageId": imageId,
            "method": "pwg.images.setInfo",
            "tag_ids": tagIds
        }
        print(f"Les tags existants vont être lus !")
        response = session.post(
            piwigo_base_url + "?format=json&method=pwg.tags.getList",
            data=payload
        )
        return response.status_code == 200

def getPiwigoTagsList(session):
    # récupération de la liste des tags déjà définis dans piwigo
    tagIds = {}
    if session:
        piwigo_base_url = "https://galleries.grains-de-culture.fr/ws.php"
        token = get_pwg_token(session, piwigo_base_url)
        payload = {
            "pwg_token": token,
            "method": "pwg.tags.getAdminList",
        }
        print(f"Les tags existants vont être lus !")
        response = session.post(
            piwigo_base_url + "?format=json&method=pwg.tags.getAdminList",
            data=payload,
        )
        if response.status_code == 200:
            res = json.loads(response.text)
            for tag in res["result"]["tags"]:
                tagIds[tag["name"]] = tag
            print(f"Les tags '{tagIds}' ont été lus avec succès !")
            print(datetime.datetime.now())
            return tagIds
        else:
            print("Erreur :", response.status_code, response.text)
            return None
    return tagIds

def openPiwigoApiSession():
    openedSession = None
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
        openedSession = session
    return openedSession

def addPiwigoTag(session, tagname):
    if session:
        piwigo_base_url = "https://galleries.grains-de-culture.fr/ws.php"
        payload = {
            "name": tagname,
            "method": "pwg.tags.add",
        }
        print(f"Le tag '{tagname}' va être ajouté à Piwigo !")
        response = session.post(
            piwigo_base_url + "?format=json&method=pwg.tags.add",
            data=payload
        )
        # todo ajouter des logs
        if response.status_code == 200:
            print(f"Le tag '{tagname}' a été ajouté avec succès !")
            print(datetime.datetime.now())
            return response
        else:
            print("Erreur :", response.status_code, response.text)
            return None

def addTagsToPiwigoImage(session, tagsId,imageId):
    if session:
        piwigo_base_url = "https://galleries.grains-de-culture.fr/ws.php"
        token = get_pwg_token(session, piwigo_base_url)
        # print("Connexion réussie!")
        # todo gérer description multilingue
        # Authentification et envoi de l'image avec des métadonnées
        payload = {
            "image_id": imageId,
            "tag_ids": ", ".join(tagsId),
            "pwg_token": token,
            "method": "pwg.images.setInfo",
        }
        print(f"Les tags '{tagsId}' vont être ajoutés à l'image {imageId} !")
        response = session.post(
            piwigo_base_url + "?format=json&method=pwg.images.setInfo",
            data=payload,
        )
        # todo ajouter des logs
        if response.status_code == 200:
            print(f"Les tags '{tagsId}' ont été ajoutés avec succès !")
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
    queryTags = """
                    select distinct ?tag ?tagLabel where { 
                      values ?oeuvre { <__ARTWORKENTITY__> } 
                      ?oeuvre wdt:P180 ?tag 
                      SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,mul,en". }
                    }
                """
    with open("D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\listeAlbumsCreateurs.json",
              encoding="UTF-8") as albumsCreatorsFile:
        creatorsToProcess = json.load(albumsCreatorsFile)
    with open("D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/listeGenresPeintures.json",
              encoding="UTF-8") as genresFile:
        listGenres = json.load(genresFile)
        for genre in listGenres:
            genresDict[genre["genre"]] = genre
    session = openPiwigoApiSession()
    existingTags = getPiwigoTagsList(session)
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
                    crtquery = queryTags.replace("__ARTWORKENTITY__", uri)
                    qid = uri.replace("http://www.wikidata.org/entity/", "")
                    wObj = WikidataObject(qid)
                    res = wObj.sparqlQuery(crtquery)
                    if not res: continue
                    tagIds = []
                    wtags = res.bindings
                    for wtag in wtags:
                        label = wtag["tagLabel"].value
                        if not label in existingTags:
                            res = addPiwigoTag(session, label)
                            existingTags = getPiwigoTagsList(session)
                        tagIds.append(existingTags[label]["id"])
                    if tagIds:
                        imId = getImageId(im)
                        if imId:
                            if addTagsToPiwigoImage(session, tagIds, imId):
                                if not "tags" in dictim[uri]: dictim[uri]["tags"]=[]
                                dictim[uri]["tags"].extend(tagIds)
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
