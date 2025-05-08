"""
but: établir un état des catégories existantes, de leur titre et de leur id
la liste des albums est la liste des catégories piwigo
"""
import json
import CPiwigoManager

if __name__=="__main__":
    listcat = []
    pwg = CPiwigoManager.CPiwigoManager()
    res = pwg.piwigo_get_categories() # getCategoriesInPiwigo()
    if res:
        print(res)
        # save categories as TTL for scrutart state
        ### Modele
        # "https://kg.grains-de-culture.fr/entity/gal17","http://www.w3.org/2000/01/rdf-schema#label","Galerie de nus"
        # "https://kg.grains-de-culture.fr/entity/gal17","https://kg.grains-de-culture.fr/prop/comment","Cette galerie présente des peintures du genre 'nu'. Ces images, libres de droit, ont été sélectionnées à partir de données de Wikidata et d'images de Wikimedia Commons. Une analyse de la présence du genre 'nu' dans Wikidata se trouve dans <a href='https://scrutart.grains-de-culture.fr/'>ScrutArt</a>. Au 22/11/2024, Wikidata contenait 2051 peintures de ce genre."
        # "https://kg.grains-de-culture.fr/entity/gal17","https://kg.grains-de-culture.fr/prop/id_piwigo","17"
        # "https://kg.grains-de-culture.fr/entity/gal17","http://www.w3.org/1999/02/22-rdf-syntax-ns#type","https://kg.grains-de-culture.fr/entity/GALLERY"
        prefixes = {
            "wdt": "http://www.wikidata.org/prop/direct/",
            "wd": "http://www.wikidata.org/entity/",
            "kgdc": "https://kg.grains-de-culture.fr/entity/",
            "pgdc": "https://kg.grains-de-culture.fr/prop/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        }
        listcatTTLFile = "listCategories.ttl"
        with open(listcatTTLFile, "w", encoding="UTF-8") as catFile:
            for pref, uri in prefixes.items():
                catFile.write(f"""@prefix {pref}: <{uri}>.\n""")
            for cat in res["result"]["categories"]:
                catFile.write(f"""kgdc:gal{cat["id"]} pgdc:id_piwigo {cat['id']} .\n""")
                catFile.write(f"""kgdc:gal{cat["id"]} rdfs:label "{cat['name']}"@fr .\n""")
                if "comment" in cat:
                    catFile.write(f"""kgdc:gal{cat["id"]} pgdc:comment "{cat["comment"]}"@fr .\n""")
                catFile.write(f"""kgdc:gal{cat["id"]} a  kgdc:GALLERY .\n""")
                pass
        listcatJsonFile = "listCategories.json"
        with open(listcatJsonFile, "w", encoding="UTF-8") as catFile:
            catFile.write(json.dumps(res, ensure_ascii=False))
            pass

