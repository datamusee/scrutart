import datetime
import json

import CPiwigoManager

if __name__ == "__main__":
    seuil = 600
    listcategoriespath = "D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/listeGenresPeintures.json"
    listcat = []
    with open(listcategoriespath, "r", encoding="UTF-8") as fdata:
        data = json.loads(fdata.read())
        listcat = data
    if listcat:
        print(datetime.datetime.now())
        freqsav = 1
        idxsav = 0
        pwg = CPiwigoManager()
        for cat in listcat:
            if (int(cat["c"]) > seuil):
                catid = json.loads(cat["galerie"])["result"]["id"]
                res, comment = pwg.piwigo_comment_category(cat["entityLabel"], catid)
                if res:
                    cat["idpiwigo"] = catid
                    cat["comment"] = comment
                    idxsav += 1
                    if idxsav >= freqsav:
                        idxsav = 0
                        with open(listcategoriespath, "w", encoding="UTF-8") as fdata:
                            json.dump(listcat, fdata, ensure_ascii=False)
