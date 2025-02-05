import json
import re
import scrutartJsonToTtl

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
    """wdt:P31 rdfs:label "nature de l'élément"@fr ."""
]


if __name__ == "__main__":
    converter = scrutartJsonToTtl.ScrutartJsonToTtl()
    ttl = ""
    ttl += "\n".join(converter.prefixList)+"\n\n"
    ttl += "\n".join(converter.labelsWikidataProperties)+"\n"
    srcPath = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr/listeGenresPeintures.json"
    with open(srcPath, encoding="UTF-8") as fsrc:
        genreList = json.load(fsrc)
        for genre in genreList:
            if "http://www.wikidata.org/.well-known" in genre["genre"]: continue
            idpiwigo = None
            if "idpiwigo" in genre:
                idpiwigo = genre["idpiwigo"]
            elif "galerie" in genre:
                regex = r"\{\"stat\":\"ok\",\"result\":\{\"info\":\"Album added\",\"id\":([0-9]*)"
                match = re.search(regex, genre["galerie"])
                if match:
                    idpiwigo = match.group(1)

            ttl += converter.genreTtlDesc(genre["genre"], genre["genreLabel"], galleryId=idpiwigo, genreCount=genre["c"],
                                          genreDate="2024-12-03", lang="fr")
            # introduction de descriptiond e la galerie s'il y en a une
            if idpiwigo:
                ttl += "\n"+converter.galeryTtlDesc(idpiwigo,
                                        title=f"""Galerie de {genre["genreLabel"]}s""",
                                        comment=genre["comment"] if "comment" in genre else None,
                                        lang="fr")

    ttlpath = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data/fr/listeGenresPeintures.ttl"
    with open(ttlpath, "w", encoding="UTF-8") as fttl:
        fttl.write(ttl)
    #print(ttl)
