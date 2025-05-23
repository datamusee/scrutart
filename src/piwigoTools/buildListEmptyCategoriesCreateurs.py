import json

if __name__ == "__main__":
    creatorsFilePath = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\wikidataSignificantPaintersTicket1527.json"
    with open(creatorsFilePath, encoding="UTF-8") as creatorsSelectionFile:
        creators = json.load(creatorsSelectionFile)
        creatorsNameDict = {}
        creatorsQidDict = {}
        for crea in creators:
            qid = crea["entity"].replace("http://www.wikidata.org/entity/","")
            entityName = crea["entityLabel"]
            type = "painter"
            newelmt = {
                "qid": qid,
                "entityName": entityName,
                "type": type
            }
            creatorsNameDict[entityName] = newelmt
            creatorsQidDict[qid] = newelmt
        pass
    emptycats = []
    with open("listCategories.2025.03.json", encoding="UTF-8") as catlistfile:
        data = json.load(catlistfile)
        catlist = data["result"]["categories"]
        for cat in catlist:
            if cat["nb_images"]==0:
                emptycatdesc = {}
                entityName = cat["name"].replace("Galerie ", "")
                crea = creatorsNameDict.get(entityName, None)
                if crea and crea["type"]=="painter":
                    qid = crea["qid"]
                    emptycatdesc["type"] = crea["type"]
                    emptycatdesc["qid"] = qid
                    emptycatdesc["categoryName"] = entityName
                    compactName = entityName.replace(" ", "")
                    emptycatdesc["piwigoCategory"] = cat["id"]
                    emptycatdesc["listimagespath"] = \
                        f"D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/20250312/listeImages_{qid}_{compactName}.json"
                    emptycats.append(emptycatdesc)
            pass
    with open("listeAlbumsEntities.json", "w", encoding="UTF-8") as albumsFile:
        json.dump(emptycats, albumsFile, ensure_ascii=False)

    # ouverture d'une liste de liens scrutart/createur créée avec WPPostsList
    with open("D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\dumps\creatorsPostsDict2025-05-20.json", encoding="UTF-8") as postsCreatorFile:
        scCreators = json.load(postsCreatorFile)
        pass

    # ici, j'ai une liste de galeries d'artiste et une liste de posts scrutart associés à une partie de ces artistes
    # je peux:
    # * m'assurer que chaque post référence la bonne galerie
    # * créer les articles scrutart qui n'existent pas pour une galerie existante
    # * m'assurer que chaque galerie référence l'article scrutart correspondant et donc renvoyer les descriptions de galeries
    # avec une référence à l'article scrutart ad-hoc
