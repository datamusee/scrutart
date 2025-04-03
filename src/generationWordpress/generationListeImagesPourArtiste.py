"""
generer une liste d'images pour des artistes donnés par leur QID
"""

import json
import WikimediaAccess
import argparse

def genereListeImages(creator, sparqltemplate):
    qid = creator["qid"]
    query = sparqltemplate.replace("__QID__", qid)
    listImages = {
        "sparql": query,
        "liste": []
    }
    wobj = WikimediaAccess.WikimediaAccess(qid)
    res = wobj.sparqlQuery(query)
    print(qid, res)
    if res:
        for image in res["results"]["bindings"]:
            imagedesc = {}
            imagedesc["createur"] = image["createur"]["value"] if image.get("createur", None) else None
            imagedesc["createurLabel"] = image["createurLabel"]["value"] if image.get("createurLabel", None) else None
            imagedesc["uri"] = image["uri"]["value"] if image.get("uri", None) else None
            imagedesc["titre_fr"] = image["titre_fr"]["value"] if image.get("titre_fr", None) else None
            imagedesc["image"] = image["image"]["value"] if image.get("image", None) else None
            imagedesc["categories"] = []
            imagedesc["categories"].append({ "catId": creator["piwigoCategory"], "catName": f"""Galerie {creator["name"]}"""} )
            listImages["liste"].append(imagedesc)
    return listImages

if __name__=="__main__":
    parserCmd = argparse.ArgumentParser(description='Process some creators, to build images list.')
    parserCmd.add_argument("listeAlbumsCreateursPath", help='Json path, list of creators, fields {"qid", "categoryName", "piwigoCategory", "listimagespath"')
    args = parserCmd.parse_args()
    listeAlbumsCreateursPath = args.listeAlbumsCreateursPath
    # listeAlbumsCreateursPath = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\listeAlbumsCreateurs.json"
    with open(listeAlbumsCreateursPath, encoding="UTF-8") as albumCreateursFile:
        listeAlbumsCreateurs = json.load(albumCreateursFile)
        qidArtistes = []
        for item in listeAlbumsCreateurs:
            qidArtistes.append({ "name": item["categoryName"], "qid":  item["qid"],
                                 "piwigoCategory": item["piwigoCategory"],
                                 "type": item["type"],
                                 "listimagespath": item["listimagespath"]} )

    sparqlTemplate = """
        select distinct ?uri ?createur ?createurLabel ?image ?titre_fr 
        where {
          values ?createur { wd:Q334200 }
          values ?classRel { wdt:P31 wdt:P106 }
          values ?class { wd:Q1028181 }
          values ?rel { wdt:P170 }
          {
            SELECT ?createur ?createurLabel WHERE {
            values ?createur { wd:Q334200 }
            SERVICE wikibase:label { bd:serviceParam wikibase:language "fr, en, [AUTO_LANGUAGE],mul". }
            }
          }
          ?uri wdt:P31 wd:Q3305213;    
               ?rel ?createur;    
               wdt:P18 ?image.
          ?createur ?classRel ?class   
          {
            SELECT ?uri ?uriLabel WHERE {
              ?uri wdt:P31 wd:Q3305213;    
                 ?rel ?createur;    
                 wdt:P18 ?image.
            SERVICE wikibase:label { bd:serviceParam wikibase:language "fr, en, [AUTO_LANGUAGE],mul". }
            }
          }
          bind( ?uriLabel as ?titre_fr)
        }
    """

    # for creator in qidArtistes:
    for creator in qidArtistes[0:1]:
        listImages = genereListeImages(creator, sparqlTemplate)
        # compactName = creator["name"].replace(" ", "")
        #listFilePath = f"D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr\listeImages{compactName}.json"
        listFilePath = creator["listimagespath"]
        with open(listFilePath, "w", encoding="utf-8") as flist:
            json.dump(listImages, flist, ensure_ascii=False)