import json

from src.generationWordpress.WikimediaAccess import WikimediaAccess
from src.generationWordpress.entitiesList import entitiesList
from src.generationWordpress.tools.scrutartJsonToTtl import ScrutartJsonToTtl

filterEntities = entitiesList

if __name__ == "__main__":
    entityClassTargets = [ "CREATORS", "GENRES", "MOVEMENTS"]
    entityClassTarget = "TOTO"
    if not entityClassTarget in entityClassTargets:
        print("Choisir la classe cible dans les classes possibles définies dans entityClassTargets")
        exit(0)
    catCorrector = ScrutartJsonToTtl().stringCorrector
    queryTemplate = """select distinct ?creatorLabel where {
          values ?creator {wd:__QID__}
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],fr,en". }
          }"""
    creators = {}
    for qid in entitiesList:
        query = queryTemplate.replace("__QID__", qid)
        res = None
        # tempo wObj = WikimediaAccess(qid)
        # tempo res = wObj.sparqlQuery(query)
        if res:
            name = res["results"]["bindings"][0]["creatorLabel"]["value"]
            creators[name] = {"name": name, "qid": qid}
    if entityClassTarget=="GENRES":
        genresFile = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\listeGenresPeintures.json"
        with open(genresFile, encoding="UTF-8") as gList:
            genresList = json.load(gList)
    existingCategoryList = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250215\categoryList.json"
    with open(existingCategoryList, encoding="UTF-8") as catFile:
        catCreatorList = []
        catGenreList = []
        catFileContent = json.loads(catFile.read())
        for cat in catFileContent["result"]["categories"]:
            if not "Galerie d" in cat["name"]:  # indice que c'est une galerie d'artiste
                if entityClassTarget=="CREATORS":
                    for crea in creators:
                        if cat["name"] == f"""Galerie {crea}""":
                            compactedName = crea.replace(" ", "")
                            catCreatorList.append(
                                {
                                    "categoryName": crea,
                                    "piwigoCategory": cat["id"],
                                    "listimagespath": f"""D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/listeImages{compactedName}.json"""
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
                        gLabel = genre["genreLabel"]
                        galeriePossibleName = f"""Galerie de {gLabel}s"""
                        galeriePossibleName = catCorrector.get(galeriePossibleName, galeriePossibleName)
                        if cat["name"] == galeriePossibleName:
                            print("OK", gLabel, galeriePossibleName, cat["id"])
                            compactedName = gLabel.replace(" ", "")
                            qid = genre["genre"].replace("http://www.wikidata.org/entity/", "")
                            catGenreList.append(
                                {
                                    "count": genre["c"],
                                    "qid": qid,
                                    "categoryName": gLabel,
                                    "piwigoCategory": cat["id"],
                                    "piwigoCategoryName": galeriePossibleName,
                                    "piwigoGategoryComment": genre["comment"] if "comment" in genre else "",
                                    "listimagespath": f"""D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/listeImages_{qid}_{compactedName}.json"""
                                }
                            )
                        else:
                            # print("---->PB: ", gLabel, galeriePossibleName, cat["id"])
                            pass
                pass
    if entityClassTarget=="CREATORS":
        createursAlbumsList = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\listeAlbumsCreateurs.json"
        with open(createursAlbumsList, "w", encoding="UTF-8") as albumsFile:
            albumsFile.write(json.dumps(catCreatorList, ensure_ascii=False))
    if entityClassTarget=="GENRES":
        genresAlbumsList = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\listeAlbumsGenres.json"
        with open(genresAlbumsList, "w", encoding="UTF-8") as genresFile:
            genresFile.write(json.dumps(catGenreList, ensure_ascii=False))
