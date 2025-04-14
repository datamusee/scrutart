# but: établir un processus complet qui va de la création des catégories à leur peuplement par des images
import json

import src.generationWordpress.WikimediaAccess as WikimediaAccess
from piwigoCategoriesState import getCategoriesInPiwigo
from piwigoCategoriesCreations import createCategoryInPiwigo
import os
import time
from repairCategoryImagePiwigo import getCategoryId, getImageId
from CPiwigoManager import CPiwigoManager

wobj = WikimediaAccess.WikimediaAccess(1)

def getImageMovements(uri, lang="fr"):
    movements = {}
    sparqlQueryMvtPainting = f"""
        prefix bd: <http://www.bigdata.com/rdf#>
        select ?movement ?movementLabel where
        {{
          <{uri}> wdt:P135 ?movement
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang}, [AUTO_LANGUAGE],mul,en". }}
        }}
    """
    sparqlQueryMvtCreator = f"""
        prefix bd: <http://www.bigdata.com/rdf#>
        select ?movement ?movementLabel where
        {{
          <{uri}> wdt:P170 ?creator .
          ?creator wdt:P135 ?movement
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang}, [AUTO_LANGUAGE],mul,en". }}
        }}
    """
    time.sleep(0.1)
    res = wobj.sparqlQuery(sparqlQueryMvtPainting)
    if res and ("results" in res) and (res["results"])and ("bindings" in res["results"]):
        if res["results"]["bindings"]:
            for mvt in res["results"]["bindings"]:
                movements[mvt["movement"]["value"]] = mvt
        else: # pas de mvt associé à cette peinture, je cherche su le créateur n'a qu'un mvt
            res = wobj.sparqlQuery(sparqlQueryMvtCreator)
            if res and ("results" in res) and (res["results"])and ("bindings" in res["results"]):
                if len(res["results"]["bindings"])==1:
                    mvt = res["results"]["bindings"][0]
                    movements[mvt["movement"]["value"]] = mvt
                    pass
    return movements


def createOrFindCategoriesInPiwigo(selectedCategories):
    existingCategories = {}
    scat = selectedCategories.copy()
    res = getCategoriesInPiwigo()
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
            rep = createCategoryInPiwigo(catlabel, "MOVEMENTS")
            if (rep.status_code==200):
                newcat = rep.json()
                selectedCategories[catlabel]["catid"] = catdesc["id"]
            pass
    return selectedCategories

def selectTargetCategories():
    sparqlQuery = """
        select  ?movement ?movementLabel ?c
        {
          values ?type { "painter" }
          {
            select ?movement (count(distinct ?s) as ?c)
            where
            {
              ?entity wdt:P106 wd:Q1028181 . # P106=occupation; Q1028181= painter
              ?s wdt:P170 ?entity .
              ?s wdt:P31 wd:Q3305213 .
              ?s wdt:P18 ?image .
              ?s wdt:P135 ?movement
            }
            group by ?movement
            having (?c>50)
            limit 1000
          }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "fr, [AUTO_LANGUAGE],en". }
        }
        order by desc(?c)
    """
    # wobj = WikimediaAccess.WikimediaAccess(1)
    res = wobj.sparqlQuery(sparqlQuery)
    selectedCategories = {}
    if res and ("results" in res) and (res["results"]) and ("bindings" in res["results"]):
        for cat in res["results"]["bindings"]:
            movementLabel = cat["movementLabel"]["value"].capitalize()
            selectedCategories[movementLabel] = cat
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
    trigger = "15953" # permet de sauter toutes les images dont l'id est donné ici
    active = False
    for image, imageDesc in postedImagesList.items():
        image_id = imageDesc["imageId"]
        if str(image_id)==str(trigger):
            active = True
        else:
            if active:
                imageCats = getImageMovements(image)
                for cat, catDesc in imageCats.items():
                    mvt = catDesc["movementLabel"]["value"].capitalize()
                    if mvt in selectedTargetCategories:
                        print(f"""Introduction dans le mouvement {mvt}""")
                        time.sleep(0.1)
                        category_id = selectedTargetCategories[mvt]["catid"]
                        crt_cats = pwg.imageGetCategories(image_id)
                        if image_id and (not crt_cats or (not str(category_id) in crt_cats)):
                            cat = pwg.imageSetCategory(image_id, category_id)
                            print(f"""catégorie {category_id} pour l'image {image_id}""")
                    else:
                        print(f"""Mouvement {mvt} à vérifier""")
                pass

    # constituer/compléter une liste d'image pour chaque catégorie en notant si l'image est déjà postée
    ## si elle n'existe pas, créer une liste vide
    ## compléter la liste existante
    # envoyer les images en traitant chaque liste (et donc pas les images déjà présentes dans Piwigo)
    pass