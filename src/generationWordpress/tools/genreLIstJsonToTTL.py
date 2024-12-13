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
    """wdt:P31 rdfs:label "nature de l'élément"@fr ."""
]


"""
    "galerie": "{\"stat\":\"ok\",\"result\":{\"info\":\"Album added\",\"id\":24}}",
    "idpiwigo": 24,
    "comment": "Cette galerie présente des peintures du genre 'scène de genre'. Ces images, libres de droit, ont été sélectionnées à partir de données de Wikidata et d'images de Wikimedia Commons. Une analyse de la présence du genre 'scène de genre' dans Wikidata se trouve dans <a href='https://scrutart.grains-de-culture.fr/'>ScrutArt</a>. Au 22/11/2024, Wikidata contenait 16045 peintures de ce genre."
  },
"""


if __name__ == "__main__":
    ttl = ""
    ttl += "\n".join(prefixList)
    ttl += "\n".join(labelsWikidataProperties)
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
            qid = genre["genre"].replace("http://www.wikidata.org/entity/", "")
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
