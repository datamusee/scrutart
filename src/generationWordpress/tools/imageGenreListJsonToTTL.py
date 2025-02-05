
import json
import re
import scrutartJsonToTtl

prefixList = [
    "@prefix wdt: <http://www.wikidata.org/prop/direct/> .",
    "@prefix wd: <http://www.wikidata.org/entity/> .",
    "@prefix kgdc: <https://kg.grains-de-culture.fr/entity/> .",
    "@prefix pgdc: <https://kg.grains-de-culture.fr/prop/> .",
    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
    "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> ."
]

labelsWikidataProperties = [
    """wdt:P136 rdfs:label "genre"@fr .""",
    """wdt:P31 rdfs:label "nature de l'élément"@fr .""",
    """wdt:P170 rdfs:label "créateur"@fr .""",
    """wdt:P18 rdfs:label "image"@fr ."""
]


if __name__ == "__main__":
    converter = scrutartJsonToTtl.ScrutartJsonToTtl()
    baseDir = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr/"
    listFileToConvert = []
    with open("listeJsonImagesGenre.json") as flistsrc:
        listFileToConvert = json.load(flistsrc)
    for fileName in listFileToConvert:
        ttl = ""
        ttl += "\n".join(prefixList) + "\n" + "\n"
        ttl += "\n".join(labelsWikidataProperties) + "\n"
        srcPath = baseDir + fileName
        with open(srcPath, encoding="UTF-8") as fsrc:
            print(srcPath)
            src = json.load(fsrc)
            imageDict = src["dict"]
            for uriWork, imageDesc in imageDict.items():
                if "http://www.wikidata.org/.well-known" in uriWork: continue
                idImagePiwigo= idGaleryPiwigo = None
                if ("posted" in imageDesc) and ("post_result" in imageDesc):
                    regex = r'"image_id":(\d+).*?category\\\/(\d+)'
                    match = re.search(regex, imageDesc["post_result"])
                    if match:
                        idImagePiwigo = match.group(1)
                        idGaleryPiwigo = match.group(2)
                qid = uriWork.replace("http://www.wikidata.org/entity/", "")
                ttl += "\n"+converter.imageTtlDesc(uriWork, images=imageDesc["images"], piwigoImageId=idImagePiwigo,
                                              piwigoCategoryId=idGaleryPiwigo,
                                              createur=imageDesc["createur"],
                                              createurLabel=imageDesc["createurLabel"],
                                              titreImage=imageDesc["titre_fr"],
                                              sparql=src["sparql"],
                                              lang="fr")

        ttlpath = srcPath.replace(".json", ".ttl")
        with open(ttlpath, "w", encoding="UTF-8") as fttl:
            fttl.write(ttl)
