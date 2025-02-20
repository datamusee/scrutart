'''
objet: chaine de production d'un ensemble d'éléments à partir d'une liste de genres ou d'artistes
portion de la liste complète définie avec 2 seuils (min et max)
* en entrée, prendre une liste d'entités wikidata avec éventuellement leur type
* par celles qui n'ont pas de type interroger wikidata pour obtenir le type
* créer si nécessaire une catégorie (album) dans Piwigo en tenant compte du type d'entité, et la mettre en tant que sous-catégorie de la bonne super-catégorie
* mettre à jour le commentaire des albums créés
* créer la liste des images pour chaque catégorie
* envoyer des images dans les albums créés
* créer ou mettre à jour une page scrutart pour chaque album de genre créé, avec référence à l'album
* ajouter l'album dans une pae de liste d'albums
'''
import requests
import configPiwigo as cp
import datetime
import json
from src.generationWordpress.WikimediaAccess import WikimediaAccess

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

def createCategory():
    pass

def getEntityOccupations(wObj, qid):
    occupations = wObj.getOccupations(qid)
    occupation = "Q1028181" if "Q1028181" in occupations else None
    return occupation

def getEntityType(wObj, qid):
    # peintre, createur, genre, mouvement,institution, ...
    objectTypes = wObj.getTypes(qid)
    entityType = "Q1792379" if "Q1792379" in objectTypes else None # art movement
    if "Q968159" in objectTypes: entityType = "Q968159"  # art genre
    if "Q16743958" in objectTypes: entityType = "Q16743958" # genre of painting
    if "Q5" in objectTypes:
        occupation = getEntityOccupations(wObj, qid)
        entityType = occupation
    return entityType

def getImagesQuery(qid, eType):
    # relation which rely class og entity to works
    typeToRel = {
        "Q1028181": f"""select distinct ?uri ?createur ?createurLabel ?image ?titre_fr where {{ 
                                values ?createur {{ wd:{qid} }}
                                values ?classRel {{ wdt:P31 wdt:P106 }}
                                values ?class {{ wd:{eType} }}
                                values ?rel {{ wdt:P170 }}
                                ?uri wdt:P31 wd:Q3305213;    
                                     ?rel ?createur;    
                                     wdt:P18 ?image.
                                ?createur rdfs:label ?createurLabel .
                                filter(lang(?createurLabel)="fr")
                                ?createur ?classRel ?class    
                                OPTIONAL {{ ?uri wdt:P1476 ?titre_fr. }}  
                                FILTER((LANG(?titre_fr)) = "fr")
                    }}""", # creator
        "Q968159": f"""select distinct ?uri ?createur ?createurLabel ?image ?titre_fr where {{ 
                                values ?qid {{ wd:{qid} }}
                                values ?classRel {{ wdt:P31 }}
                                values ?class {{ wd:{eType} }}
                                values ?rel {{ wdt:P135 }}
                                ?uri ?rel ?qid; wdt:P31  wd:Q3305213 ;
                                    wdt:P170 ?createur ;
                                    wdt:P18 ?image .
                                ?createur rdfs:label ?createurLabel .
                                filter(lang(?createurLabel)="fr")
                                ?qid ?classRel ?class .
                                OPTIONAL {{ ?uri wdt:P1476 ?titre_fr. }}  
                                FILTER((LANG(?titre_fr)) = "fr")
                    }}""", # art movement
        "Q1792379": f"""select distinct ?uri ?createur ?createurLabel ?image ?titre_fr where {{ 
                                values ?qid {{ wd:{qid} }}
                                values ?classRel {{ wdt:P31 }}
                                values ?class {{ wd:{eType} wd:Q16743958 }}
                                values ?rel {{ wdt:P136 }}
                                ?uri ?rel ?qid; ?classRel  wd:Q3305213 ;
                                    wdt:P170 ?createur ;
                                    wdt:P18 ?image .
                                ?qid ?classRel ?class .
                                ?createur rdfs:label ?createurLabel .
                                filter(lang(?createurLabel)="fr")
                                ?qid ?classRel ?class .
                                OPTIONAL {{ ?uri wdt:P1476 ?titre_fr. }}  
                                FILTER((LANG(?titre_fr)) = "fr")
                    }}""", # genre artistique, pictural
        "Q16743958": f"""select distinct ?uri ?createur ?createurLabel ?image ?titre_fr where {{ 
                                values ?qid {{ wd:{qid} }}
                                values ?classRel {{ wdt:P31 }}
                                values ?class {{ wd:{eType} wd:Q16743958 }}
                                values ?rel {{ wdt:P136 }}
                                ?uri ?rel ?qid; ?classRel  wd:Q3305213 ;
                                    wdt:P170 ?createur ;
                                    wdt:P18 ?image .
                                ?qid ?classRel ?class .
                                ?createur rdfs:label ?createurLabel .
                                filter(lang(?createurLabel)="fr")
                                ?qid ?classRel ?class .
                                OPTIONAL {{ ?uri wdt:P1476 ?titre_fr. }}  
                                FILTER((LANG(?titre_fr)) = "fr")
                    }}""", # genre artistique, pictural
    }
    return typeToRel[eType]

def getListOfPaintings(wobj, query):
    res = wobj.sparqlQuery(query)
    dictImages = {
        "sparql": f"{query}",
        "liste":[],
    }
    if "results" in res and "bindings" in res["results"] and len(res["results"]["bindings"]):
        for elmt in res["results"]["bindings"]:
            dictImages["liste"].append({
                "uri": elmt["uri"]["value"],
                "createur": elmt["createur"]["value"],
                "createurLabel":elmt["createurLabel"]["value"],
                "titre_fr":elmt["titre_fr"]["value"],
                "image":elmt["image"]["value"]
            })
    return dictImages

if __name__=="__main__":
    # EN COURS D ECRITURE
    entitySample = {
        # "Q187506": { "label": "Honoré Daumier"},
        # "Q301": { "label": "Le Greco"},
        # "Q40415": { "label":"impressionisme" },
        "Q7046534": {"label": "nocturne"},
    }
    with open("D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\listeAlbumsGenres.json",encoding="UTF-8") as genreFile:
        genreList = json.loads(genreFile.read())
        for genre in genreList:
            entitySample[genre["qid"]] = { "label": genre["categoryName"]}
    for item, value in entitySample.items():
        wObj = WikimediaAccess(item)
        entityType = getEntityType(wObj, item)
        imagesQuery = getImagesQuery(item, entityType)
        # print(entityType, usefulRelation)
        listOfPaintings = getListOfPaintings(wObj, imagesQuery)
        compactName = value["label"].replace(" ", "")
        filePath = f"D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr\listeImages_{item}_{compactName}.json"
        with open(filePath, "w", encoding="UTF-8") as imagesListFile:
            imagesListFile.write(json.dumps(listOfPaintings, ensure_ascii=False))

    seuilMin = 50
    seuilMax = 600
    listcategoriespath = "D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/listeGenresPeintures.json"
    listcat = []
    with open(listcategoriespath, "r", encoding="UTF-8") as fdata:
        data = json.loads(fdata.read())
        listcat = data
    if listcat:
        print(datetime.datetime.now())
        freqsav = 1
        idxsav = 0

        # * créer si nécessaire une catégorie (album) dans Piwigo

        # * mettre à jour le commentaire des albums créés
        # EN COURS D ECRITURE
        for cat in listcat:
            if (int(cat["c"])>=seuilMin) and (int(cat["c"])<=seuilMax):
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

        # * créer la liste des images pour chaque catégorie
        ## faire un appel à WDQS pour récupérer une liste json
        ## construire un dict json avec la clé "sparql" pour mettre la requête et la clé "liste" pour mettre le résultat

        # * envoyer des images dans les albums créés
        ## utiliser le code de envoiImagePiwigo


        # * créer ou mettre à jour une page scrutart pour chaque genre pour lequel un album est créé, avec référence à l'album
        ## utiliser le page builder de genre, qu'il faut mettre à jour avec le bloc de référence à l'album