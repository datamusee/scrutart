import json
import os

if __name__=="__main__":
    directorySrc1 = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr/20250403_1/"
    directorySrc2 = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr/"
    directoryTarget = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr/fusion/"
    listSrc1 = os.listdir(directorySrc1)
    listSrc2 = os.listdir(directorySrc2)
    for jsonpath1 in listSrc1:
        if jsonpath1 in listSrc2:
            print(jsonpath1)
            with open("".join((directorySrc2, jsonpath1)), encoding="UTF-8") as f2:
                listimages2 = json.load(f2)
                with open("".join((directorySrc1, jsonpath1)), encoding="UTF-8") as f1:
                    listimages1 = json.load(f1)
                    if ("liste" in listimages1) and listimages1["liste"]:
                        for image in listimages1["liste"]:
                            imageQid = image["uri"]
                            print(imageQid)
                            if ("liste" in listimages2) and not listimages2["liste"]:
                                if (not "dict" in listimages2):
                                    listimages2["dict"] = {}
                            if "dict" in listimages2:
                                if imageQid in listimages2["dict"]:
                                    # je complète la description
                                    print(listimages2["dict"][imageQid])
                                    if listimages2["dict"][imageQid]["createur"]!=image["createur"]: continue
                                    if listimages2["dict"][imageQid]["createurLabel"]!=image["createurLabel"]: continue
                                    if listimages2["dict"][imageQid]["titre_fr"]!=image["titre_fr"]: continue
                                    if listimages2["dict"][imageQid]["uri"]!=image["uri"]: continue
                                    if "categories" in image:
                                        listimages2["dict"][imageQid]["categories"] = image["categories"]
                                    if "images" in listimages2["dict"][imageQid]:
                                        if not image["image"] in listimages2["dict"][imageQid]["images"]:
                                            listimages2["dict"][imageQid]["images"].append(image["image"])
                                    pass
                                else: # j'ajoute la description
                                    listimages2["dict"][imageQid] = image
                                    listimages2["dict"][imageQid]["images"] = []
                                    if "image" in image:
                                        listimages2["dict"][imageQid]["images"].append(image["image"])
                                    pass
                    if "dict" in listimages1:
                        for key, value in listimages1["dict"].items():
                            print("".join((key, ": ", str(value))))
                            pass
                with open("".join((directoryTarget, jsonpath1)), "w", encoding="UTF-8") as ftarget:
                    json.dump(listimages2, ftarget, ensure_ascii=False)
                    pass