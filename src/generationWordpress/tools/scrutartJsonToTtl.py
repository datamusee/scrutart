import json
import re

class ScrutartJsonToTtl:
    def __init__(self):
        self.prefixList = [
            "@prefix wdt: <http://www.wikidata.org/prop/direct/> .",
            "@prefix wd: <http://www.wikidata.org/entity/> .",
            "@prefix kgdc: <https://kg.grains-de-culture.fr/entity/> .",
            "@prefix pgdc: <https://kg.grains-de-culture.fr/prop/> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> ."
        ]
        self.labelsWikidataProperties = [
            """wd:Q1792379 rdfs:label "genre artistique"@fr .""",
            """wdt:P31 rdfs:label "nature de l'élément"@fr ."""
            """wdt:P170 rdfs:label "créateur"@fr .""",
            """wdt:P18 rdfs:label "image"@fr ."""
        ]

    def entityTtlDesc(self, qid, wtype=None, label=None, count=None, date=None, lang="fr"):
        ttl = ""
        if not qid: return ttl
        if "http" in qid:
            qid = qid.replace("http://www.wikidata.org/entity/", "")
        if wtype or label or count:
            mainEntity = "wd:" + qid
            if label:
                ttl += f"""{mainEntity} rdfs:label "{label}"@{lang}.\n"""
            if wtype:
                ttl += f"{mainEntity} wdt:P31 wd:{wtype} .\n"
            if count:
                countId = f"{qid}_icount_reif" # reification compte avec date du compte
                ttl += f"{mainEntity} pgdc:instance_count kgdc:{countId} .\n\n"
                self.countTtlDesc(countId, count=count, date=date)
        return ttl

    def countTtlDesc(self, idstate, count=None, date=None):
        # introduction du compte d'instances réifié (compte, date)
        ttl = ""
        countEntity =  f"kgdc:{idstate}\n"
        if count:
            ttl += f'{countEntity} pgdc:value {genre["c"]} .\n'
            if not date: date="2024-12-03"
            ttl += f"""{countEntity} pgdc:date {date}^^xsd:date .\n\n"""
        return ttl

    def imageTtlDesc(self):
        ttl = ""
        return ttl

    def galeryTtlDesc(self, idpiwigo, title=None, comment=None, lang="fr"):
        # description ttl d'une galerie
        ttl = ""
        if idpiwigo:
            entity = f"kgdc:gal{idpiwigo}\n"
            if title:
                ttl += f"""{entity} rdfs:label {title}"@{lang} .\n"""
            if comment:
                ttl += f"""{entity} pgdc:comment "{comment}"{lang} .\n"""
            ttl += f"{entity} pgdc:id_piwigo {idpiwigo} .\n"
        return ttl
