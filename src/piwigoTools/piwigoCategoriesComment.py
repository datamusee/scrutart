import datetime
import json

from CPiwigoManager import CPiwigoManager

def findCategoriesInPiwigo(pwg):
    existingCategories = {}
    res = pwg.piwigo_get_categories()
    if res and ("stat" in res) and (res["stat"]=="ok") and ("result" in res): # and ("categories" in res["result"]):
        for cat in res["result"]: #["categories"]:
            label = cat["name"].strip().lower() # strip ' ' de début et de fin, et minuscules pour variations écriture noms propres
            existingCategories[label] = cat
            if "sub_categories" in cat:
                for subcat in cat["sub_categories"]:
                    label = subcat["name"].strip().lower()  # strip ' ' de début et de fin, et minuscules pour variations écriture noms propres
                    existingCategories[label] = subcat
                    pass
    return existingCategories

if __name__ == "__main__":
    pwg = CPiwigoManager()
    listcat = findCategoriesInPiwigo(pwg)
    print("liste de catégories artiste pour lesquelles assurer l'existance d'une page scrutart:")
    for catlabel, catdesc in listcat.items():
        if catdesc["id_uppercat"]=="80": # sous-catégorie de galerie d'artistes
            catid = catdesc["id"]
            # TODO mettre un vrai lien vers un article dans scrutart
            # et ne publier le commentaire que si cet article existe
            comment = pwg.build_gallery_comment("GALERY_CREATOR", catdesc["name"].replace("Galerie ", "")) if catdesc["nb_images"]>=30 else ""
            test = pwg.piwigo_comment_category(catid, comment)
            if comment:
                print(f""""{catid}": "", # {catdesc["nb_images"]} images""")
