import json
import re

prefixList = [
    "@prefix wdt: <http://www.wikidata.org/prop/direct/> .",
    "@prefix wd: <http://www.wikidata.org/entity/> .",
    "@prefix kgdc: <https://kg.grains-de-culture.fr/entity/> .",
    "@prefix pgdc: <https://kg.grains-de-culture.fr/prop/> .",
    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
    "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> ."
]

labelsWikidataProperties = [
    """wdt:P136 rdfs:label "genre"@fr .""",
    """wdt:P31 rdfs:label "nature de l'élément"@fr .""",
    """wdt:P170 rdfs:label "créateur"@fr .""",
    """wdt:P18 rdfs:label "image"@fr ."""
]

"""
kgdc:sparql_uuid1 # uuid1 à remplacer par un uuid calculé avec la requête sparql
    kgdc:sparql "ici requête sparql utilisée pour générer des choses" .

kgdc:Q17491676
    pgdc:sparql_gen kgdc:sparql_uuid1;
    pgdc:uri wd:Q17491676;
    wdt:P170 wd:Q665818;
    rdfs:label "Idylle"@fr;
    wdt:P18 "http://commons.wikimedia.org/wiki/Special:FilePath/Idylle-Jean-Jacques%20Henner-Orsay.jpg";
    pgdc:piwigo_image "https://galeries.grains-de-culture.fr/picture.php?/829/category/17" .
"""
"""
    "http://www.wikidata.org/entity/Q17491676": {
      "uri": "http://www.wikidata.org/entity/Q17491676",
      "createur": "http://www.wikidata.org/entity/Q665818",
      "createurLabel": "Jean-Jacques Henner",
      "titre_fr": "Idylle",
      "images": [
        "http://commons.wikimedia.org/wiki/Special:FilePath/Idylle-Jean-Jacques%20Henner-Orsay.jpg",
        "http://commons.wikimedia.org/wiki/Special:FilePath/Idylle-Jean-Jacques%20Henner-Orsay.jpg"
      ],
      "post_result": "{\"stat\":\"ok\",\"result\":{\"image_id\":829,\"url\":\"https:\\/\\/galleries.grains-de-culture.fr\\/picture.php?\\/829\\/category\\/17\"}}",
      "posted": true
"""

if __name__ == "__main__":
    ttl = ""
    ttl += "\n".join(prefixList)
    ttl += "\n".join(labelsWikidataProperties)
    srcPath = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\tools\imageNuListJsonToTTL.py"
    with open(srcPath, encoding="UTF-8") as fsrc:
        imageDict = json.load(fsrc)
        for uriWork, imageDesc in imageDict.items():
            if "http://www.wikidata.org/.well-known" in uriWork: continue
            idpiwigo = None
            if ("posted" in imageDesc) and ("post_result" in imageDesc):
                regex = r"\{\"stat\":\"ok\",\"result\":{\"image_id\":([0-9]*),\"url\":\"https:\\/\\/galleries.grains-de-culture.fr\\/picture.php?\\/([0-9]*)\\/category\\/([0-9]*)\"\}\}"
                match = re.search(regex, imageDesc["post_result"])
                if match:
                    idImagePiwigo = match.group(1)
                    idGaleryPiwigo = match.group(3)
            qid = uriWork.replace("http://www.wikidata.org/entity/", "")
            mainEntity = "wd:"+qid
            ttl += "\n"+mainEntity+"\n"
            ttl += f"""\trdfs:label "{genre["genreLabel"]}"@fr;\n"""
            ttl += "\twdt:P31 wdt:P136 ;\n"
            ttl += f"\tpgdc:instance_count kgdc:{qid}_icount_reif .\n\n"

            # introduction du compte d'instances réifié (compte, date)
            ttl += f"kgdc:{qid}_icount_reif\n"
            if "c" in genre:
                ttl += f'\tpgdc:value {genre["c"]} ;\n'
                ttl += """\tpgdc:date "2024-12-03"^^xsd:date .\n\n"""

            # introduction de descriptiond e la galerie s'il y en a une
            if idpiwigo:
                ttl += f"kgdc:gal{idpiwigo}\n"
                ttl += f"""\trdfs:label "Galerie de {genre["genreLabel"]}"@fr ;\n"""
                if "comment" in genre:
                    ttl += f"""\tpgdc:comment "{genre["comment"]}";\n"""
                ttl += f"\tpgdc:id_piwigo {idpiwigo} .\n"

    ttlpath = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr/listeGenresPeintures.ttl"
    with open(ttlpath, "w", encoding="UTF-8") as fttl:
        fttl.write(ttl)
    #print(ttl)

"""
kgdc:gal24
    rdfs:label "Galerie de scènes de genre"@fr;
    pgdc:id_piwigo 24;
    pgdc:comment "Cette galerie présente des peintures du genre 'scène de genre'. Ces images, libres de droit, ont été sélectionnées à partir de données de Wikidata et d'images de Wikimedia Commons. Une analyse de la présence du genre 'scène de genre' dans Wikidata se trouve dans <a href='https://scrutart.grains-de-culture.fr/'>ScrutArt</a>. Au 22/11/2024, Wikidata contenait 16045 peintures de ce genre."@fr .
"""
