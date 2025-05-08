class CScrutartState():
    # voir http://127.0.0.1:3030/#/dataset/scrutartState/info pour tous les points d'accès
    # au 28/4/2025, il y a 3 types P31 utilisés
    # https://www.wikidata.org/wiki/Q1792379 genre artistique -> 447
    # https://www.wikidata.org/wiki/Q1028181 artiste peintre -> 1319
    # https://www.wikidata.org/wiki/Q838948 oeuvre d'art -> 6556
    # prévoir: au moins un type et un label pour chaque entité
    def __init__(self, urlread="http://127.0.0.1:3030/scrutartState/query", urlwrite=None):
        prefixes = {
            "wdt": "http://www.wikidata.org/prop/direct/",
            "wd": "http://www.wikidata.org/entity/",
            "kgdc": "https://kg.grains-de-culture.fr/entity/",
            "pgdc": "https://kg.grains-de-culture.fr/prop/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        }
        common_labels = {
            "wdt:P136": { "fr": "genre", "en": "genre" },
            "wdt:P31": { "fr": "nature de l'élément" },
            "wdt:P170": { "fr": "créateur", "en": "creator"},
            "wdt:P18": { "fr": "image", "en": "image" }
        }
        pass

    def getGraphs(self): # devrait être dans une classe parent
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

    def addArtWork(self, artworkdesc=None):
        # artworkdesc has:
        # qid 1:1
        # rdfs:label = titre en 1 ou plusieurs langues
        # type wdt:P31 -> wd:Q838948 oeuvre d'art
        # createur wdt:P170 -> qid createur
        # url image wdt:P18 = url de la source
        # id piwigo de l'image pgdc:piwigo_image : str
        # 0 à n pgdc:piwigo_gallery -> uri de galerie ex:  kgdc:gal17 où 17 est l'id piwigo de la galerie
        # 0 à n pgdc:sparql  -> url d'une requête sparql reifiée qui a permis de trouver cette image
        #             ex: kgdc:sparqlQFQoWpXmMgU8awWwiPODRaH3HnvfcweciiNMns4lAi3 (obtenu en uuid à partir de str sparql)
        return {}

    def addGallery(self, gallerydesc=None):
        # une galerie a au moins un label en français et un commentaire
        # elle a un id piwigo
        return {}

    def addGenre(self, genredesc=None):
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