import datetime
import json

from CPiwigoManager import CPiwigoManager

def getCategoriesList(pwg):
    listcat = []
    res = pwg.piwigo_get_categories()
    result = res["result"]
    categories = result["categories"]
    return categories

if __name__ == "__main__":
    pwg = CPiwigoManager()
    listcat = getCategoriesList(pwg)
    print("liste de catégories artiste pour lesquelles assurer l'existance d'une page scrutart:")
    for cat in listcat:
        if cat["id_uppercat"]=="80": # sous-catégorie de galerie d'artistes
            catid = cat["id"]
            comment = pwg.buildGaleryComment("GALERY_CREATOR", cat["name"].replace("Galerie ", "")) if cat["nb_images"]>=30 else ""
            test = pwg.piwigo_comment_category(catid, comment)
            if comment:
                print(f""""{catid}": "", # {cat["nb_images"]} images""")
