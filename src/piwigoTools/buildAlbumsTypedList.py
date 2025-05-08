import json
import argparse
from memorize import Memorize
from src.generationWordpress.WikimediaAccess import WikimediaAccess
from src.generationWordpress.entitiesList import entitiesList
from src.generationWordpress.tools.scrutartJsonToTtl import ScrutartJsonToTtl
# from piwigoCategoriesCreations import createCategoryInPiwigo
import CPiwigoManager

@Memorize
def getCreatorName(qid, query):
    wObj = WikimediaAccess(qid)
    res = wObj.sparqlQuery(query)  # interrogation de WDQS
    if res:
        name = res["results"]["bindings"][0]["creatorLabel"]["value"]  # recupération du label associé au qid
        return name
    return None

# filterEntities = entitiesList
# filterEntities = [  "Q239394" ]
entityFilePath = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\wikidataSignificantPaintersTicket1527.json"
with open(entityFilePath, encoding="UTF-8") as fListTypes:
    types = json.load(fListTypes)
    filterEntities = [elmt["entity"].replace("http://www.wikidata.org/entity/", "") for elmt in
                      types]  # ligne à enlever si je ne veux pas tout traiter et tenir compte du filtre

filterEntities = [
    "Q237911" #  Louise Abbéma
]

if __name__ == "__main__":
    entityClassTargets = [ "CREATORS", "GENRES", "MOVEMENTS"]
    parserCmd = argparse.ArgumentParser(description='Process some entities, to build a list of Piwigo gategories associated with path of images lists.')
    parserCmd.add_argument("-t", "--entityType", type=str, help='CREATORS or GENRES')
    parserCmd.add_argument("-lc", "--listeAlbumsPath", type=str, help='Json path, list of creators, fields {"qid", "categoryName", "piwigoCategory", "listimagespath"')
    args = parserCmd.parse_args()
    listeAlbumsPath = args.listeAlbumsPath
    # exemple: "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr/20250312/listeAlbumsGenres.json"
    # exemple: "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr/20250312/listeAlbumsCreateurs.json"
    # entityTypeTarget = "CREATORS"
    entityClassTarget = args.entityType
    entityClassTarget = "CREATORS"
    if not entityClassTarget in entityClassTargets:
        print("Choisir la classe cible dans les classes possibles définies dans entityClassTargets")
        exit(0)
    catCorrector = ScrutartJsonToTtl().stringCorrector # correcteur de mise au pluriel brute en français
    # template de query pour récupérer le label français ou anglais d'une entité
    queryTemplate = """select distinct ?creatorLabel where {
          values ?creator {wd:__QID__}
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],fr,en". }
          }"""
    # dictionnaire de créateurs en cours de création
    creators = {}
    for qid in filterEntities: # [275:276]: # pour chaque qid pris dans la liste filterEntities (ou une sous-partie)
        query = queryTemplate.replace("__QID__", qid) # query sparql pour l'entité qid
        res = None
        print(f"access to {qid}")
        # wObj = WikimediaAccess(qid)
        name = getCreatorName(qid, query)
        # res = wObj.sparqlQuery(query) # interrogation de WDQS
        if name: # res:
            # name = res["results"]["bindings"][0]["creatorLabel"]["value"] # recupération du label associé au qid
            creators[name] = {"name": name, "qid": qid} # injection dans le dictionnaire avec pour clé le label
            print(f"---> {creators[name]}")


    if entityClassTarget=="GENRES":
        # s'il s'agit de genres à traiter, chargement d'une liste de genres connus
        genresFile = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\listeGenresPeintures.json"
        with open(genresFile, encoding="UTF-8") as gList:
            genresList = json.load(gList)
    # existingCategoryList = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250215\categoryList.json"

    # chemin vers une liste de catégories Piwigo (albums) existantes, obtenue grâce à l'API piwigo
    # TODO devrait être créé dynamiquement ici en interrogeant Piwigo
    existingCategoryList = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\piwigoTools\listCategories.json"

    with open(existingCategoryList, encoding="UTF-8") as catFile:
        catCreatorList = []
        catGenreList = []
        catFileContent = json.loads(catFile.read())
        for cat in catFileContent["result"]["categories"]:
            if not "Galerie d" in cat["name"]:  # indice que c'est une galerie d'artiste
                if entityClassTarget=="CREATORS":
                    for crea, creaval in creators.items():
                        compactedName = crea.replace(" ", "")
                        if cat["name"] == f"""Galerie {crea}""":
                            if "id" in cat: # il y a une categorie Piwigo
                                creators[crea]["piwigoCategory"] = cat["id"] # l'associer au créateur
                                # ajouter un créateur dans la liste de créateurs avec catégorie
                                # avec son qid, son label, sa catégorie Piwigo et un chemin pour créer la liste d'images
                                qid = creaval["qid"]
                                catCreatorList.append(
                                    {
                                        "type": "painter",
                                        "qid": creaval["qid"],
                                        "categoryName": crea,
                                        "piwigoCategory": cat["id"],
                                        "listimagespath": f"""D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/20250403_1/listeImages_{qid}_{compactedName}.json"""
                                    }
                                )
            elif "Cette galerie présente des peintures du genre" in cat["comment"]: # indice qu'il s'agit d'une catégorie de genre
                # mettre dans une liste de genres à traiter sur le modèle de listeAlbumsCréateurs
                # donc en constituant une liste d'images de chaque genre
                # comme D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\fr\20250215\listeImages_Q16743958_nocturne.json construit avec
                # D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\piwigoTools\piwigoCategoryChain.py
                if entityClassTarget=="GENRES":
                    for genre in genresList:
                        if int(genre["c"])<10: continue
                        #if gLabel.startswith("art"):
                        #    galeriePossibleName = galeriePossibleName.replace("de art", "d'art")
                        #    galeriePossibleName = galeriePossibleName[0:-1]
                        #if gLabel.startswith("peinture"):
                        #    galeriePossibleName = galeriePossibleName.replace("peinture", "peintures")
                        gLabel = genre["entityLabel"]
                        galeriePossibleName = f"""Galerie de {gLabel}s"""
                        galeriePossibleName = catCorrector.get(galeriePossibleName, galeriePossibleName)
                        if cat["name"] == galeriePossibleName:
                            print("OK", gLabel, galeriePossibleName, cat["id"])
                            compactedName = gLabel.replace(" ", "")
                            qid = genre["entity"].replace("http://www.wikidata.org/entity/", "")
                            catGenreList.append(
                                {
                                    "count": genre["c"],
                                    "qid": qid,
                                    "categoryName": gLabel,
                                    "piwigoCategory": cat["id"],
                                    "piwigoCategoryName": galeriePossibleName,
                                    "piwigoGategoryComment": genre["comment"] if "comment" in genre else "",
                                    "listimagespath": f"""D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/20250403_1/listeImages_{qid}_{compactedName}.json"""
                                }
                            )
                        else:
                            # print("---->PB: ", gLabel, galeriePossibleName, cat["id"])
                            pass
                pass
    pwg = CPiwigoManager.CPiwigoManager()
    if entityClassTarget=="CREATORS":
        for crea, creaVal in creators.items():
            if not "piwigoCategory" in creaVal: # si le créateur n'a pas de catégorie piwigo associée, la créer
                res = pwg.piwigo_create_category(crea, entityClassTarget)
                if res:
                    compactedName = crea.replace(" ", "")
                    qid = creaval["qid"],
                    catCreatorList.append(
                        {
                            "type": "painter",
                            "qid": creaval["qid"],
                            "categoryName": crea,
                            "piwigoCategory": res.json()["result"]["id"],
                            "listimagespath": f"""D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/20250403_1/listeImages_{qid}_{compactedName}.json"""
                        }
                    )
                    print(f"""Catégorie créée pour {crea}""")
                else:
                    print(f"""Problème pour créer la catégorie pour {crea}""")
            else:
                print(f"""Catégorie {creaVal["piwigoCategory"]} existe déjà pour {crea}""")
        # créer le fichier json de liste de créateurs avec les information qid, label, id piwigo et path de fichier de liste d'images
        createursAlbumsList = listeAlbumsPath # "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\listeAlbumsCreateurs.json"
        with open(createursAlbumsList, "w", encoding="UTF-8") as albumsFile:
            albumsFile.write(json.dumps(catCreatorList, ensure_ascii=False))
    if entityClassTarget=="GENRES":
        genresAlbumsList = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\listeAlbumsGenres.json"
        with open(genresAlbumsList, "w", encoding="UTF-8") as genresFile:
            genresFile.write(json.dumps(catGenreList, ensure_ascii=False))
