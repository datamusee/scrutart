"""
but: établir un état des catégories exsitantes, de leur titre et de leur id
? par catégorie entend-on la liste des albums et/ou la liste des tags
"""
import requests
import configPiwigo as cp
import datetime
import json
import time

def getCategoriesInPiwigo():
    username = cp.configPiwigo["login"]
    password = cp.configPiwigo["pass"]
    auth_data = {
        "format": "application/json",
        "method": "pwg.session.login",
        "username": username,
        "password": password,
    }
    # Ouvrir une session avec l'API pour se connecter
    session = requests.Session()  # Crée une session persistante

    # Envoyer la requête de connexion
    piwigo_base_url = "https://galleries.grains-de-culture.fr/ws.php"
    response = session.post(piwigo_base_url, data=auth_data)
    if response.ok:  # and response.json().get("stat") == "ok":
        # print("Connexion réussie!")
        # Authentification et envoi de l'image avec des métadonnées
        payload = {
            "format":"json",
            "fullname": "true",
            "tree_output": "true",
            "recursive": "true",
            "method": "pwg.categories.getList",
        }
        # Construire les données de la requête avec la pièce jointe
        response = session.get(
            piwigo_base_url + "?format=json&method=pwg.categories.getList&recursive=true",
            data=payload,
        )
        # todo ajouter des logs
        if response.status_code == 200:
            return response.json()
        else:
            print("Erreur :", response.status_code, response.text)
            return None

if __name__=="__main__":
    listcat = []
    res = getCategoriesInPiwigo()
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

