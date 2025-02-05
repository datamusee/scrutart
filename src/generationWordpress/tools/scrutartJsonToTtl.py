import hashlib
import string

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
            """wdt:P31 rdfs:label "nature de l'élément"@fr .""",
            """wdt:P170 rdfs:label "créateur"@fr .""",
            """wdt:P18 rdfs:label "image"@fr ."""
        ]
        self.stringCorrector = {
            "Galerie de art naïfs": "Galerie d'art naïf",
            "Galerie de peinture de fleurss":"Galerie de peintures de fleurs",
            "Galerie de peinture de fruitss":"Galerie de peintures de fruits",
            "Galerie de peinture de personnages":"Galerie de peintures de personnage",
            "Galerie de peinture de batailles":"Galerie de peintures de bataille",
            "Galerie de autoportraits":"Galerie d'autoportraits",
            "Galerie de nature mortes":"Galerie de natures mortes",
            "Galerie de scène de genres":"Galerie de scènes de genre",
            "Galerie de peinture mythologiques":"Galerie de peintures mythologiques",
            "Galerie de paysage urbains":"Galerie de paysages urbains",
            "Galerie de peinture d'histoires":"Galerie de peintures d'histoire",
            "Galerie de allégories":"Galerie d'allégories",
            "Galerie de art animaliers":"Galerie d'art animalier",
            "Galerie de art abstraits":"Galerie d'art abstrait",
            "Galerie de peinture d'architectures":"Galerie de peintures d'architecture",
            "Galerie de portrait de groupes":"Galerie de portraits de groupe",
            "Galerie de intérieur d'églises":"Galerie d'intérieurs d'église",
            "Galerie de scène d'intérieurs":"Galerie de scènes d'intérieur",
            "Galerie de portrait de familles":"Galerie de portraits de famille",
            "Galerie de portrait équestres":"Galerie de portraits équestres",
            "Galerie de double portraits":"Galerie de doubles portraits",
            "Galerie de vue d'architectures":"Galerie de vues d'architecture",
            "Galerie de portrait historiés":"Galerie de portraits historiés",
            "Galerie de art militaires":"Galerie d'art militaire",
            "Galerie de art figuratifs":"Galerie d'art figuratif",
            "Galerie de trompe-l'œils":"Galerie de trompe-l'œil",
            "Galerie de peinture Paharis":"Galerie de peintures Pahari",
            "Galerie de art populaires":"Galerie d'art populaire",
            "Galerie de art sacrés":"Galerie d'art sacré",
        }

    def qidSimple(self, qid):
        if "http" in qid:
            qid = qid.replace("http://www.wikidata.org/entity/", "")
        return qid

    def entityTtlDesc(self, qid, wtype=None, label=None, count=None, date=None, lang="fr"):
        ttl = ""
        if not qid: return ttl
        qid = self.qidSimple(qid)
        if wtype or label or count:
            mainEntity = "wd:" + qid
            if label:
                label = label.replace("\"", "'")
                ttl += f'{mainEntity} rdfs:label """{label}"""@{lang}.\n'
            if wtype:
                ttl += f"{mainEntity} wdt:P31 wd:{wtype} .\n"
            if count:
                countId = f"{qid}_icount_reif" # reification compte avec date du compte
                ttl += f"{mainEntity} pgdc:instance_count kgdc:{countId} .\n\n"
                ttl += self.countTtlDesc(countId, count=count, date=date)
        return ttl

    def countTtlDesc(self, idstate, count=None, date=None):
        # introduction du compte d'instances réifié (compte, date)
        ttl = ""
        countEntity =  f"kgdc:{idstate}"
        if count:
            ttl += f'{countEntity} pgdc:value {count} .\n'
            if not date: date="2024-12-03"
            ttl += f"""{countEntity} pgdc:date "{date}"^^xsd:date .\n\n"""
        return ttl

    def genreTtlDesc(self, qid, genreLabel, galleryId= None, genreCount=None, genreDate=None, lang="fr"):
        ttl = ""
        qid = self.qidSimple(qid)
        ttl += "\n"+self.entityTtlDesc(qid, label=genreLabel, wtype="Q1792379",
                                  count=genreCount, date=genreDate, lang=lang)
        if galleryId:
            galUri = self.buildGaleryUri(galleryId)
            ttl += f"""wd:{qid} pgdc:piwigo_gallery {galUri}.\n"""
        return ttl

    def buildSparqlUri(self, uuid):
        return f"kgdc:sparql{uuid}"


    def generer_chaine_courte(self, chaine_longue, longueur=None):
        # Caractères pour l'encodage en Base62
        BASE62 = string.ascii_letters + string.digits  # 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        BASE = len(BASE62)  # 62
        # Crée un hachage SHA-256 de la chaîne longue
        hash_object = hashlib.sha256(chaine_longue.encode())
        # Convertit le hachage en un entier
        hash_int = int(hash_object.hexdigest(), 16)

        # Convertit l'entier en une chaîne Base62
        chaine_courte = ""
        while hash_int > 0:
            hash_int, i = divmod(hash_int, BASE)
            chaine_courte = BASE62[i] + chaine_courte
        if not longueur: longueur = len(chaine_courte)

        # Tronque la chaîne à la longueur souhaitée
        return chaine_courte[:longueur]

    def sparqlTtlDesc(self, sparqluri, sparql):
        ttl = ""
        ttl += f'{sparqluri} pgdc:sparql_src """{sparql}""".\n'
        return ttl

    def imageTtlDesc(self, qid, images, piwigoImageId, piwigoCategoryId, createur, createurLabel, titreImage, lang="fr",
                     sparql=None):
        ttl = ""
        qid = self.qidSimple(qid)
        ttl += self.entityTtlDesc(qid, wtype="Q838948", label=titreImage, lang=lang)
        ttl += f"""wd:{qid} wdt:P170 wd:{self.qidSimple(createur)}.\n"""
        images = list(set(images))
        for imageUrl in images:
            ttl += f"""wd:{qid} wdt:P18 "{imageUrl}".\n"""
        ttl += f"""wd:{qid} pgdc:piwigo_image "{piwigoImageId}".\n"""
        galUri = self.buildGaleryUri(piwigoCategoryId)
        ttl += f"""wd:{qid} pgdc:piwigo_gallery {galUri}.\n"""
        if sparql:
            sparqlUuid = self.generer_chaine_courte(sparql)
            sparqlUri = self.buildSparqlUri(sparqlUuid)
            ttl += f"""wd:{qid} pgdc:sparql {sparqlUri} .\n"""
            ttl += "\n"+self.sparqlTtlDesc(sparqlUri, sparql)
        ttl += "\n"+self.entityTtlDesc(createur, wtype="Q1028181", label=createurLabel, lang=lang)
        return ttl

    def buildGaleryUri(self, idpiwigo):
        return f"kgdc:gal{idpiwigo}"

    def galeryTtlDesc(self, idpiwigo, title=None, comment=None, lang="fr"):
        # description ttl d'une galerie
        ttl = ""
        if idpiwigo:
            entity = self.buildGaleryUri(idpiwigo)
            if title:
                correctedTitle = self.stringCorrector.get(title, title)
                ttl += f'{entity} rdfs:label """{correctedTitle}"""@{lang} .\n'
            if comment:
                ttl += f'{entity} pgdc:comment """{comment}"""@{lang} .\n'
            ttl += f"""{entity} pgdc:id_piwigo "{idpiwigo}" .\n"""
        return ttl
