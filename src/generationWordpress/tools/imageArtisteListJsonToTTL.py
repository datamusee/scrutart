
import json
import re
from os import listdir
from os.path import isfile, join
from src.generationWordpress.CScrutartState import CScrutartState

# but: mettre des images dans le graphe d'état scrutartStateTrial (plus tard scrutartState local et TPT)
if __name__ == "__main__":
    baseDir = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr/20250507/"
    listFileToConvert =[f for f in listdir(baseDir) if isfile(join(baseDir, f)) and ("listeImages_Q" in f) and (not ".ttl" in f)]
    # fichier texte avec une simple liste de path vers des fichiers de liste d'images
    for fileName in listFileToConvert:
        cs = CScrutartState()
        srcPath = baseDir + fileName
        ttl = ""
        with open(srcPath, encoding="UTF-8") as fsrc:
            print(srcPath)
            src = json.load(fsrc)
            if "dict" in src:
                imageDict = src["dict"]
                for uriWork, imageDesc in imageDict.items():
                    if "http://www.wikidata.org/.well-known" in uriWork: continue
                    artwork = cs.artworkFromJson(imageDesc, src=src)
                    ttl += artwork.toTtl()
                    response = cs.putArtwork(artwork)
            elif "liste" in src:
                for imageDesc in src["liste"]:
                    if "http://www.wikidata.org/.well-known" in imageDesc["uri"]: continue
                    artwork = cs.artworkFromJson(imageDesc, src=src)
                    ttl += artwork.toTtl()
                    response = cs.putArtwork(artwork)
            ttlpath = srcPath.replace(".json", ".ttl")
            with open(ttlpath, "w", encoding="UTF-8") as fttl:
                fttl.write(ttl)
