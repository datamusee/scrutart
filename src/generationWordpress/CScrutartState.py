import hashlib
import string
from dataclasses import dataclass, field
from typing import Optional
import datetime
import requests
from src.generationWordpress.tools.scrutartJsonToTtl import ScrutartJsonToTtl
from src.piwigoTools.CPiwigoManager import CPiwigoManager


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
            ttl += f"{mainEntity} wdt:P31 wd:{wtype} .\n"
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
        self.wtypes.append("Q3391743") # artiste visuel ou artiste visuelle
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

    def toTTL(self):
        ttl = super().toTtl()
        if self.image_id:
            ttl += f"""wd:{self.qid} pgdc:piwigo_image "{self.image_id}".\n"""
        for gal in self.galery_ids:
            galUri = self.buildGalleryUri(gal)
            ttl += f"""wd:{self.qid} pgdc:piwigo_gallery {galUri}.\n"""
        return ttl

class CScrutartState():
    # voir http://127.0.0.1:3030/#/dataset/scrutartState/info pour tous les points d'accès
    # au 28/4/2025, il y a 3 types P31 utilisés
    # https://www.wikidata.org/wiki/Q1792379 genre artistique -> 447
    # https://www.wikidata.org/wiki/Q1028181 artiste peintre -> 1319
    # https://www.wikidata.org/wiki/Q838948 oeuvre d'art -> 6556
    # prévoir: au moins un type et un label pour chaque entité
    def __init__(self, urlread="http://127.0.0.1:3030/scrutartState/query", urlwrite=None):
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
        self.sparqlEndpointUpdate = "http://127.0.0.1:3030/scrutartStateTrial/update"
        pass

    def sendTtlToSparqlEndpoint(self, ttl, sparqlEndpointUpdate=None):
        updateEndpoint = sparqlEndpointUpdate if sparqlEndpointUpdate else self.sparqlEndpointUpdate
        # TODO intégrer le code proposé par chatgpt pour l'envoi de ttl à un endpoint
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
        response = requests.post(self.sparqlEndpointUpdate, data=sparql_update)#, headers=headers)

        if response.status_code in (200, 204):
            print("✅ Données RDF envoyées avec token d’accès.")
        else:
            print(f"❌ Erreur {response.status_code} : {response.text}")

        return response

    def getGraphs(self):  # devrait être dans une classe parent
        return {}

    def getArtworks(self, limit=10, offset=0):
        # type P31 http://www.wikidata.org/prop/direct/P31
        # https://www.wikidata.org/wiki/Q838948 oeuvre d'art
        # prévoir d'autres types
        return {}

    def getCreators(self, limit=10, offset=0):
        # type P31 http://www.wikidata.org/prop/direct/P31
        # https://www.wikidata.org/wiki/Q1028181 artiste peintre
        # prévoir d'autres types
        return {}

    def getInstitutions(self, limit=10, offset=0):
        return {}

    def getMovements(self, limit=10, offset=0):
        return {}

    def getGenres(self, limit=10, offset=0):
        # type P31 http://www.wikidata.org/prop/direct/P31
        # https://www.wikidata.org/wiki/Q1792379 genre artistique
        # prévoir d'autres types
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
                artwork = DCPiwigoArtwork(
                    uriWork=jsonArtworkDescription["uri"],
                    posted=jsonArtworkDescription.get("posted", False),
                    creators=[DCWikidataCreator(creatorQid=jsonArtworkDescription.get("createur", None),
                                                creatorLabels=[
                                                    DCLangLabel(lang="fr",
                                                                label=jsonArtworkDescription.get("createurLabel", None))])
                              ],
                    titres=DCLangLabel(lang="fr", label=jsonArtworkDescription.get("titre_fr", None)),
                    images=[DCImage(url=im) for im in jsonArtworkDescription.get("images", None)],
                    sparqlSrc=src.get("sparql", None),
                    image_id=im_id,
                    galery_ids=gal_ids,
                    artworkType=artworkType
                )
        except Exception as e:
            # remplacer le print par un logging
            print(f"""{jsonArtworkDescription} probably doesn't contain necessary field""")
            pass
        return artwork

    def putArtwork(self, artwork):
        ttl = artwork.toTTL()
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
