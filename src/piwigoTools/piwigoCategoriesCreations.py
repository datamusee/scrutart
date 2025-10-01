import requests
import configPiwigo as cp
import datetime
import json
import CPiwigoManager

if __name__=="__main__":
    seuilMin = 50
    seuilMax = 600
    # chemin d'un fichier qui liste des catégories
    # seul les éléments de la liste qui ont
    # un champ "galerie", un champ "entityLabel" et un champ "c" vont être traités (avec champ c entier qui respecte les seuils
    # listcategoriespath = "D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/listeGenresPeintures.json"
    listcategoriespath = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\wikidataSignificantPaintersTicket1527.json"

    listcat = []
    pwg = CPiwigoManager()
    with open(listcategoriespath, "r", encoding="UTF-8") as fdata:
        data = json.loads(fdata.read())
        listcat = data
    # listcat doit contenir une liste de catégories
    if listcat:
        print(datetime.datetime.now())
        freqsav = 1
        idxsav = 0
        for cat in listcat:
            if (not "galerie" in cat) and (int(cat["c"])>=seuilMin)  and (int(cat["c"])<=seuilMax):
                res = pwg.piwigo_create_category(cat["entityLabel"])
                if res:
                    cat["galerie"] = res.text
                    idxsav += 1
                    if idxsav>=freqsav:
                        idxsav = 0
                        with open(listcategoriespath, "w", encoding="UTF-8") as fdata:
                            json.dump(listcat, fdata, ensure_ascii=False)


