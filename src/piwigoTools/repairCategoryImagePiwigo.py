import requests
import configPiwigo as cp
import datetime
import json
import time
import re
from CPiwigoManager import CPiwigoManager
import time

def getFilesList(dirToProcess):
    filesList = []
    from os import listdir
    from os.path import isfile, join
    filesList = [join(dirToProcess, f) for f in listdir(dirToProcess) if isfile(join(dirToProcess, f))]
    return filesList

def getImageId(res):
    imId = None
    regex = r"image_id[\\]?\":[\"]?(\d+)"
    match = re.search(regex, res)
    if match:
        imId = match.group(1)
    return imId

def getCategoryId(res):
    catId = None
    regex = r"category\\\/(\d+)"
    match = re.search(regex, res)
    if match:
        catId = match.group(1)
    return catId

def getImageCategory(res):
    image_id = getImageId(res)
    cat_id = getCategoryId(res)
    return cat_id, image_id

if __name__=="__main__":
    dirToProcess = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\fusion"
    filesList = getFilesList(dirToProcess)
    for filepath in filesList:
        if not "listeAlbums" in filepath: continue
        itemsToProcess = []
        # with open("D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\listeAlbumsCreateurs.json",
        with open(filepath, encoding="UTF-8") as albumsItemsFile:
            itemsToProcess = json.load(albumsItemsFile)
        for item in itemsToProcess:
            #### remplacer ces lignes par création de catégorie si elle n'existe pas déjà
            categoryName = item["categoryName"]
            print(f"""Galerie {categoryName} ({item["qid"]})""")
            piwigoCategory = item["piwigoCategory"]
            listimagespath = item["listimagespath"]
            dictim = {}
            with open(listimagespath, "r", encoding="UTF-8") as fdata:
                data = json.loads(fdata.read())
                dictim = data["dict"] if "dict" in data else None
            if dictim:
                print(datetime.datetime.now())
                pwg = CPiwigoManager()
                for uri, im in dictim.items():
                    if "posted" in im:
                        if "post_result" in im:
                            res = im["post_result"]
                            cat_id, image_id = getImageCategory(res)
                            crt_cats = []
                            if image_id:
                                crt_cats = pwg.imageGetCategories(image_id)
                            time.sleep(0.01)
                            if image_id and (not crt_cats or (not cat_id in crt_cats)):
                                cat = pwg.imageSetCategory(image_id, cat_id)
                                print(f"""catégorie {cat_id} pour l'image {image_id}""")
                            pass

# La description peut contenir un lien vers l entité source, un lien vers l URL de l image, le copyright
# Il faut limiter l api a n'accepter que certains emetteurs
