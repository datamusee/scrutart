import logging
import hashlib
import string
from dataclasses import dataclass, field
from typing import Optional
import datetime
import requests
from src.piwigoTools.CPiwigoManager import CPiwigoManager
import SPARQLWrapper as sw


@dataclass
class DCDateCount:
    date: datetime
    count: int

@dataclass
class DCLangLabel:
    lang: str
    label: str

@dataclass
class DCWikidataEntity:
    uri: str
    labels: list[DCLangLabel]
    wtypes: Optional[list[str]] = None
    counts: Optional[list[DCDateCount]] = field(default_factory=list)
    qid: Optional[str] = None

    @staticmethod
    def qidSimple(qid):
        if "http" in qid:
            qid = qid.replace("http://www.wikidata.org/entity/", "")
        return qid

    def __post_init__(self):
        if self.qid is None:
            self.qid = DCWikidataEntity.qidSimple(self.uri)
        if self.wtypes is None:
            self.wtypes = []

    def toTtl(self):
        ttl = ""
        mainEntity = "wd:" + self.qid
        for langlabel in self.labels:
            label = langlabel.label.replace("\"", "'")
            lang = langlabel.lang if langlabel.lang else "fr"
            ttl += f'{mainEntity} rdfs:label """{label}"""@{lang}.\n'
        for wtype in self.wtypes:
            ttl += f"{mainEntity} wdt:P31 {wtype} .\n"
        for count in self.counts:
            countId = f"{self.qid}_icount_reif" # reification compte avec date du compte
            ttl += f"{mainEntity} pgdc:instance_count kgdc:{countId} .\n\n"
            countdate = count.date if count.date else datetime.now()
            if count.count:
                countEntity = f"kgdc:{countId}"
                ttl += f'{countEntity} pgdc:value {count.count} .\n'
                ttl += f"""{countEntity} pgdc:date "{countdate}"^^xsd:date .\n\n"""
        return ttl

@dataclass
class DCWikidataCreator(DCWikidataEntity):
    def __post_init__(self):
        if self.wtypes is None:
            self.wtypes = []
        self.wtypes.append("wd:Q3391743") # artiste visuel ou artiste visuelle
        if self.qid is None:
            self.qid = DCWikidataEntity.qidSimple(self.uri)

@dataclass
class DCImage:
    url: str
    src: Optional[str] = None


@dataclass
class DCWikidataArtwork(DCWikidataEntity):
    creators: Optional[list[DCWikidataCreator]] = None
    images: Optional[list[DCImage]] = None
    sparqlSrc: Optional[str] = None
    artworkType: Optional[str] = None

    @staticmethod
    def generer_chaine_courte(chaine_longue, longueur=None):
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

    @staticmethod
    def buildSparqlUri(uuid):
        return f"kgdc:sparql{uuid}"

    def toTtl(self):
        ttl = super().toTtl()
        for creator in self.creators:
            ttl += f"""wd:{self.qid} wdt:P170 wd:{creator.qid}.\n"""
            ttl += creator.toTtl()
        imagesUrl = [image.url for image in self.images ]
        imagesUrl = list(set(imagesUrl)) # pour éliminer les doublons
        for imageUrl in imagesUrl:
            ttl += f"""wd:{self.qid} wdt:P18 "{imageUrl}".\n"""
        if self.sparqlSrc:
            sparqlUuid = self.generer_chaine_courte(self.sparqlSrc)
            sparqlUri = self.buildSparqlUri(sparqlUuid)
            ttl += f"""wd:{self.qid} pgdc:sparql {sparqlUri} .\n"""
            ttl += f'{sparqlUri} pgdc:sparql_src """{self.sparqlSrc}""".\n'
        return ttl

@dataclass
class DCPiwigoArtwork(DCWikidataArtwork):
    # qid 1:1
    # rdfs:label = titre en 1 ou plusieurs langues
    # type wdt:P31 -> wd:Q838948 oeuvre d'art
    # createur wdt:P170 -> qid createur
    # url image wdt:P18 = url de la source
    # id piwigo de l'image pgdc:piwigo_image : str
    # 0 à n pgdc:piwigo_gallery -> uri de galerie ex:  kgdc:gal17 où 17 est l'id piwigo de la galerie
    # 0 à n pgdc:sparql  -> url d'une requête sparql reifiée qui a permis de trouver cette image
    #             ex: kgdc:sparqlQFQoWpXmMgU8awWwiPODRaH3HnvfcweciiNMns4lAi3 (obtenu en uuid à partir de str sparql)
    posted: bool = False
    post_result: Optional[str] = None
    galery_ids: Optional[list[str]] = field(default_factory=list)
    image_id: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.galery_ids is None:
            self.galery_ids = []

    def toTtl(self):
        ttl = super().toTtl()
        if self.image_id:
            ttl += f"""wd:{self.qid} pgdc:piwigo_image "{self.image_id}".\n"""
        for gal in self.galery_ids:
            galUri =  f"kgdc:gal{gal}"
            ttl += f"""wd:{self.qid} pgdc:piwigo_gallery {galUri}.\n"""
        return ttl

class CScrutartState():
    # voir http://127.0.0.1:3030/#/dataset/scrutartState/info pour tous les points d'accès
    # au 28/4/2025, il y a 3 types P31 utilisés
    # https://www.wikidata.org/wiki/Q1792379 genre artistique -> 447
    # https://www.wikidata.org/wiki/Q1028181 artiste peintre -> 1319
    # https://www.wikidata.org/wiki/Q838948 oeuvre d'art -> 6556
    # prévoir: au moins un type et un label pour chaque entité
    def __init__(self, urlread="http://127.0.0.1:3030/scrutartStateTrial/query",
                    urlwrite="http://127.0.0.1:3030/scrutartStateTrial/update"):
        self.prefixes = {
            "wdt": "http://www.wikidata.org/prop/direct/",
            "wd": "http://www.wikidata.org/entity/",
            "kgdc": "https://kg.grains-de-culture.fr/entity/",
            "pgdc": "https://kg.grains-de-culture.fr/prop/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        }
        self.common_labels = {
            "wdt:P136": {"fr": "genre", "en": "genre"},
            "wdt:P31": {"fr": "nature de l'élément"},
            "wdt:P170": {"fr": "créateur", "en": "creator"},
            "wdt:P18": {"fr": "image", "en": "image"}
        }
        self.sparqlEndpointUpdate = urlwrite
        self.sparqlEndpointQuery = urlread
        check = self.checkIfSparqlScrutartStateEndpointIsAvailable(urlread)
        pass

    def checkIfSparqlScrutartStateEndpointIsAvailable(self, urlendpoint=None):
        if urlendpoint==None:
            urlendpoint=self.sparqlEndpointQuery
        query = """select distinct ?s            where {              ?s ?p ?o            } LIMIT 1        """
        sparqlScrutartWrapper = sw.SPARQLWrapper2(urlendpoint)  # implicit JSON format
        sparqlScrutartWrapper.setQuery(query)
        try:
            res = sparqlScrutartWrapper.queryAndConvert()
            return True if res and res.bindings else False
        except Exception as e:
            print(
                    f"le serveur scrutart state (au 12/2/2025, {urlendpoint} (D:\Outils\Semantic/apache-jena-fuseki-4.8.0/fuseki-server) doit avoir été lancé avant de lancer cette application")
            exit(7777)
            return False

    def sparqlQuery(self, query):
        sparqlFusekiWrapper = sw.SPARQLWrapper2(self.sparqlEndpointQuery)  # implicit JSON format
        sparqlFusekiWrapper.setQuery(query)
        try:
            res = sparqlFusekiWrapper.queryAndConvert()
            return res
        except Exception as e:
            logging.debug(e)
        return None # à affiner

    def sendTtlToSparqlEndpoint(self, ttl, sparqlEndpointUpdate=None):
        updateEndpoint = sparqlEndpointUpdate if sparqlEndpointUpdate else self.sparqlEndpointUpdate
        # TODO intégrer le code proposé par chatgpt pour sécuriser l'endpoint
        access_token = "TOTOTATATUTU"
        sparql_update = ""
        sparql_update += "".join([f"""\nprefix {pref}: <{value}>""" for pref, value in self.prefixes.items()])
        #     """wdt:P136 rdfs:label "genre"@fr .""",
        ttlcommons = ""
        for uri, labels in self.common_labels.items():
            for lang, label in labels.items():
                ttlcommons += f"""\n{uri} rdfs:label "{label}"@{lang} ."""
        sparql_update += f"""
        INSERT DATA {{
            {ttlcommons}
            {ttl}
        }}
        """
        headers = {
            # "Authorization": f"Bearer {access_token}",
            # "Content-Type": "application/sparql-update"
        }
        response = requests.post(updateEndpoint, data=sparql_update.encode(encoding="utf-8"))#, headers=headers)
        if response.status_code in (200, 204):
            print(f"✅ Données RDF envoyées : {ttl} .")
        else:
            print(f"❌ Erreur {response.status_code} : {response.text}")
        return response

    def getGraphs(self):  # devrait être dans une classe parrent
        query = """select distinct ?graph { graph ?graph { ?s ?p [] }}"""
        res = self.sparqlQuery(query)
        return {}

    def getArtworks(self, limit=10, offset=0):
        # https://www.wikidata.org/wiki/Q838948 oeuvre d'art
        # prévoir d'autres types
        query = """select distinct ?graph {  
                ?artwork <http://www.wikidata.org/prop/direct/P31>  <https://www.wikidata.org/wiki/Q838948> 
            } """ + f"""limit {limit}""" if limit>0 else "" + f""" offset {offset}"""
        res = self.sparqlQuery(query)
        return {}

    def getCreators(self, limit=10, offset=0):
        # https://www.wikidata.org/wiki/Q1028181 artiste peintre
        # prévoir d'autres types
        query = """select distinct ?graph {  
                ?creator <http://www.wikidata.org/prop/direct/P31>  <https://www.wikidata.org/wiki/Q1028181> 
            } """ + f"""limit {limit}""" if limit>0 else "" + f""" offset {offset}"""
        res = self.sparqlQuery(query)
        return {}

    def getInstitutions(self, limit=10, offset=0):
        return {}

    def getMovements(self, limit=10, offset=0):
        return {}

    def getGenres(self, limit=10, offset=0):
        # https://www.wikidata.org/wiki/Q1792379 genre artistique
        # prévoir d'autres types
        query = """select distinct ?graph {  
                ?creator <http://www.wikidata.org/prop/direct/P31>  <https://www.wikidata.org/wiki/Q1792379> 
            } """ + f"""limit {limit}""" if limit>0 else "" + f""" offset {offset}"""
        res = self.sparqlQuery(query)
        return {}

    def getGalleries(self, limit=10, offset=0):
        return {}

    def artworkFromJson(self, jsonArtworkDescription, src=None, artworkType="wd:Q838948", version="2.0.0"):
        artwork = None
        try:
            if version == "2.0.0":
                im_id = None
                gal_ids = None
                if (("post_result" in jsonArtworkDescription) and ("ok" in jsonArtworkDescription["post_result"])):
                    im_id = CPiwigoManager.getImageId(jsonArtworkDescription["post_result"])
                    gal_ids = [
                        CPiwigoManager.getCategoryId(jsonArtworkDescription["post_result"])
                    ]
                if ("image" in jsonArtworkDescription) and (type(jsonArtworkDescription["image"]) is list):
                    images = [DCImage(url=im) for im in jsonArtworkDescription.get("image", None)]
                else:  # supposed string
                    images = [DCImage(url=jsonArtworkDescription.get("image", None))]
                if ("images" in jsonArtworkDescription) and (type(jsonArtworkDescription["images"]) is list):
                    images = [DCImage(url=im) for im in jsonArtworkDescription.get("images", None)]
                sparql= src.get("sparql", None) if src else None
                artwork = DCPiwigoArtwork(
                    uri=jsonArtworkDescription["uri"],
                    posted=jsonArtworkDescription.get("posted", False),
                    creators=[DCWikidataCreator(uri=jsonArtworkDescription.get("createur", None),
                                                labels=[
                                                    DCLangLabel(lang="fr",
                                                                label=jsonArtworkDescription.get("createurLabel", None))])
                              ],
                    labels=[DCLangLabel(lang="fr", label=jsonArtworkDescription.get("titre_fr", None))],
                    images= images,
                    image_id=im_id,
                    galery_ids=gal_ids,
                    sparqlSrc=sparql,
                    wtypes=[ artworkType ]
                )
                pass
        except Exception as e:
            # remplacer le print par un logging
            print(f"""{jsonArtworkDescription} probably doesn't contain necessary field""")
            pass
        return artwork

    def putArtwork(self, artwork):
        ttl = artwork.toTtl()
        response = self.sendTtlToSparqlEndpoint(ttl)
        return response

    def putCreator(self, creatordesc=None):
        # un créateur a au moins un label en français
        return {}

    def putGallery(self, gallerydesc=None):
        # une galerie a au moins un label en français et un commentaire
        # elle a un id piwigo
        return {}

    def putGenre(self, genredesc=None):
        # envisager d'introduire des genres sans QID ou des qid 'à moi' formés différemment des QID wikidata
        # modèle { version": "0.1.0", "qid": str, "labels": [ { "label":str, "lang":str}], {"count":int, "date": date}}
        # optionnellement, il peut y avoir une galerie associée au genre
        if genredesc:
            pass
        return {}

    def getPublicationInfo(self, qid=None):
        # article(s) scrutart associés au QID, galerie(s) associées au QID, nombre d'images...
        return {}

    def getScrutartAssociatedImages(self, qid=None):
        # liste de: { source, url image source, id piwigo, id media wp, titre }
        return {}

    #####################
    ########
    # methods to inforce quality of the graph
    ########
    #####################
    def forceGalleriesType(self):
        # object of the property https://kg.grains-de-culture.fr/prop/piwigo_gallery must be a gallery
        # and a gallery must have the type (P31) Q1007870 (galerie d'art)
        updatequery = """insert { ?gal <http://www.wikidata.org/prop/direct/P31> <https://www.wikidata.org/entity/Q1007870> }
                        where {  [] <https://kg.grains-de-culture.fr/prop/piwigo_gallery> ?gal } 
            """
        response = requests.post(self.sparqlEndpointUpdate, data=updatequery.encode(encoding="utf-8"))#, headers=headers)
        if response.status_code in (200, 204):
            print(f"Garantie que les objets galerie sont typés")
        else:
            print(f"❌ Erreur {response.status_code} : {response.text}")

    def applyQualityRules(self):
        rules = [
            { "method": self.forceGalleriesType() }
        ]
        for r in rules:
            r["method"]()


