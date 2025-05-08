# but: établir un processus complet qui va de la création des catégories à leur peuplement par des images
import json

import src.generationWordpress.WikimediaAccess as WikimediaAccess
import os
import time
from repairCategoryImagePiwigo import getCategoryId, getImageId
from CPiwigoManager import CPiwigoManager

wobj = WikimediaAccess.WikimediaAccess(1)

def getImageMuseums(uri, lang="fr"):
    museums = {}
    sparqlQueryMuseumPainting = f"""
        prefix bd: <http://www.bigdata.com/rdf#>
        select ?museum ?museumLabel where
        {{
          <{uri}> wdt:P276 ?museum
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang}, [AUTO_LANGUAGE],mul,en". }}
        }}
    """
    time.sleep(0.1)
    res = wobj.sparqlQuery(sparqlQueryMuseumPainting)
    if res and ("results" in res) and (res["results"])and ("bindings" in res["results"]):
        if res["results"]["bindings"]:
            for mvt in res["results"]["bindings"]:
                museums[mvt["museum"]["value"]] = mvt
                pass
    return museums


def createOrFindCategoriesInPiwigo(selectedCategories):
    existingCategories = {}
    scat = selectedCategories.copy()
    pwg = CPiwigoManager()
    res = pwg.piwigo_image_get_categories()
    if res and ("stat" in res) and (res["stat"]=="ok") and ("result" in res) and ("categories" in res["result"]):
        for cat in res["result"]["categories"]:
            label = cat["name"]
            existingCategories[label] = cat
    for catlabel, catvalue in scat.items():
        if catlabel in existingCategories:
            catdesc = existingCategories[catlabel]
            selectedCategories[catlabel]["catid"] = catdesc["id"]
            selectedCategories[catlabel]["catinfo"] = catdesc
            print("----------> ", catlabel, selectedCategories[catlabel])
        else:
            print(f"""Création de la catégorie {catlabel}""")
            rep = pwg.piwigo_create_category(catlabel, "INSTITUTIONS")
            if (rep.status_code==200):
                newcat = rep.json()
                selectedCategories[catlabel]["catid"] = catdesc["id"]
            pass
    return selectedCategories

def selectTargetCategories():
    sparqlQuery = """
        SELECT ?museum ?museumLabel ?c WHERE {
          VALUES ?type {
            "painter"
          }
          {
            SELECT ?museum (COUNT(DISTINCT ?s) AS ?c) WHERE {
              ?entity wdt:P106 wd:Q1028181.
              ?s wdt:P170 ?entity;
                wdt:P31 wd:Q3305213;
                wdt:P18 ?image;
                 wdt:P17 wd:Q142;
                wdt:P276 ?museum.
              #?museum wdt:P17 wdt:Q142
            }
            GROUP BY ?museum
            HAVING (?c > 10 )
            LIMIT 1000
          }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "fr, [AUTO_LANGUAGE],en". }
        }
        ORDER BY DESC (?c)
    """
    # wobj = WikimediaAccess.WikimediaAccess(1)
    res = wobj.sparqlQuery(sparqlQuery)
    selectedCategories = {}
    if res and ("results" in res) and (res["results"]) and ("bindings" in res["results"]):
        for cat in res["results"]["bindings"]:
            museumLabel = cat["museumLabel"]["value"].capitalize()
            selectedCategories[museumLabel] = cat
    return selectedCategories

def buildAlreadyPostedImagesList():
    postedImages = {}
    directoriesWithLogs = [
        "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250215",
        "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250219",
        "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250222",
        "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250312",
        "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250402",
        "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250403",
        "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250403_1",
        "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250405",
        "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\fusion",
        "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr",
    ]
    postedImagesList = {}
    for dir in directoriesWithLogs:
        dirlist = os.listdir(dir)
        for path in dirlist:
            if "listeImages_Q" in path:
                fullpath = f"""{dir}/{path}"""
                print(fullpath)
                with open(fullpath, encoding="UTF-8") as fList:
                    imagesList = json.load(fList)
                    if "dict" in imagesList:
                        for image, imageVal in imagesList["dict"].items():
                            if "posted" in imageVal:
                                imageVal["imageId"] = getImageId(imageVal["post_result"])
                                postedImagesList[image] = imageVal
                    pass
    # TODO envisager de récupérer la liste des images sur Piwigo
    return postedImagesList

if __name__ == "__main__":
    # déterminer les catégories à créer
    targetCategories = selectTargetCategories()
    # créer les catégories si elles n'existent pas déjà
        # les galeries seront créées comme sous-catégorie de la galerie Galeries par mouvements d'id 853
        # c'est cette position qui permettra de l'identifier comme galerie de mouvement
    selectedTargetCategories = createOrFindCategoriesInPiwigo(targetCategories)
    # pour chaque image déjà dans Piwigo, chercher son mouvement via WDQS et lui ajouter la catégorie correspondante
    ## récupérer la liste d'images déjà dans Piwigo
    # constituer une liste des images déjà traitées en lisant les fichiers listes traités
    # (à l'avenir, il devrait suffire de lire ça dans le graphe scrutart-state)
    postedImagesList = buildAlreadyPostedImagesList()
    # affecter les catégories à chacune de ces images
    pwg = CPiwigoManager()
    trigger = False # "12515"  # permet de sauter toutes les images dont l'id est donné ici
    active = True if not trigger else False
    for image, imageDesc in postedImagesList.items():
        image_id = imageDesc["imageId"]
        if str(image_id)==str(trigger):
            active = True
        else:
            if active:
                imageCats = getImageMuseums(image)
                for cat, catDesc in imageCats.items():
                    museum = catDesc["museumLabel"]["value"].capitalize()
                    if museum in selectedTargetCategories:
                        print(f"""Introduction dans le musee {museum}""")
                        time.sleep(0.1)
                        category_id = selectedTargetCategories[museum]["catid"]
                        crt_cats = pwg.piwigo_image_get_categories(image_id)
                        if image_id and (not crt_cats or (not str(category_id) in crt_cats)):
                            cat = pwg.piwigo_image_set_category(image_id, category_id)
                            print(f"""catégorie {category_id} pour l'image {image_id}""")
                    else:
                        print(f"""Musée {museum} à vérifier""")
                pass

    # constituer/compléter une liste d'image pour chaque catégorie en notant si l'image est déjà postée
    ## si elle n'existe pas, créer une liste vide
    ## compléter la liste existante
    # envoyer les images en traitant chaque liste (et donc pas les images déjà présentes dans Piwigo)
    pass