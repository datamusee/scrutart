"""
generer une liste d'images pour des artistes donnés par leur QID
"""

import json
import WikimediaAccess

def genereListeImages(qid, sparqltemplate):
    query = sparqltemplate.replace("__QID__", qid)
    listImages = {
        "sparql": query,
        "liste": []
    }
    wobj = WikimediaAccess.WikimediaAccess(qid)
    res = wobj.sparqlQuery(query)
    if res:
        for image in res.bindings:
            imagedesc = {}
            imagedesc["createur"] = image["createur"].value if image.get("createur", None) else None
            imagedesc["createurLabel"] = image["createurLabel"].value if image.get("createurLabel", None) else None
            imagedesc["uri"] = image["uri"].value if image.get("uri", None) else None
            imagedesc["titre_fr"] = image["titre_fr"].value if image.get("titre_fr", None) else None
            imagedesc["image"] = image["image"].value if image.get("image", None) else None
            listImages["liste"].append(imagedesc)
    return listImages

if __name__=="__main__":
    qidArtistes = [
        {"name": "Anders Zorn", "qid": "Q206820"},
        {"name": "Bruno Liljefors", "qid": "Q730008"},
        {"name": "Carl Larsson", "qid": "Q187310"},
        {"name": "José de Ribera", "qid": "Q297238"},
    ]

    sparqlTemplate = """
        SELECT DISTINCT ?uri ?createur ?createurLabel ?image ?titre_fr WHERE {
          VALUES ?createur {
            wd:__QID__
          }
          ?uri wdt:P31 wd:Q3305213;
            wdt:P170 ?createur;
            wdt:P18 ?image
               .
          ?createur rdfs:label ?createurLabel.
          FILTER((LANG(?createurLabel)) = "fr")
          ?uri rdfs:label ?titre_fr .
          FILTER(((LANG(?titre_fr)) = "fr")||((LANG(?titre_fr)) = "en"))
        } 
    """

    for creator in qidArtistes:
        listImages = genereListeImages(creator["qid"], sparqlTemplate)
        compactName = creator["name"].replace(" ", "")
        listFilePath = f"D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr\listeImages{compactName}.json"
        with open(listFilePath, "w", encoding="utf-8") as flist:
            json.dump(listImages, flist, ensure_ascii=False)