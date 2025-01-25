import logging
import SPARQLWrapper as sw
from urllib.parse import quote
import datetime
import time
from urllib.parse import urlparse
import os
import requests
import json
"""
Tous les accès à des outils Wikimedia devraient passer par un objet de ce type unique
afin de gérer les limites sur ces accès:
- nécessité d'avoir un User-Agent bien défini
- nombre de requêtes par minute
...
Idéalement, je devrais en faire une api et tous les programmes passeraient par cette API
Avec dans l'API, un mécanisme de file d'attente et/ou un mécanisme de type 'ré-essayer plus tard"
par exemple, une requête sparql wdqs est mise en file d'attente et la réponse est juste une url à interroger pour voir si
la réponse est prête et l'obtenir si elle est prête
cela permet aussi de faire au mieux et d'envoyer des requêtes en masse

"""
class WikimediaAccess:
    def __init__(self, qid):
        self.wdqsWrapper = sw.wdqsWrapper2() # ici mettre un manager de webpimanager
        self.setWdqsFormat()
        self.setWdqsEndpoint()
        self.setWdqsAgent()
        pass

    def setWdqsFormat(self, format="JSON"):
        self.wdqsWrapper.returnFormat = format
        return format

    def getWdqsFormat(self):
        return self.wdqsWrapper.returnFormat

    def setWdqsEndpoint(self, endpoint="https://query.wikidata.org/sparql"):
        self.wdqsWrapper.wdqsEndpoint = endpoint
        return endpoint

    def getWdqsEndpoint(self):
        return self.wdqsWrapper.wdqsEndpoint

    def setWdqsAgent(self, agent='Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)'):
        self.wdqsWrapper.agent = agent
        return agent

    def setWdqsAgent(self):
        return self.wdqsWrapper.agent

    def getTypes(self, qid):
        # aller chercher une valeur de instance of (P31) pour le QID donné
        # pour un peintre comme Carolus Duran, son type P31 est 'être humain' (Q5)
        # il faudra alors, dans certains cas, extérieurement, trouver son occupation 'artiste peintre' (Q1028181)
        # pour une peinture, comme Mona Lisa, on aura P31 peinture (Q3305213)
        # pour un genre (P136), on aura P31 'genre artistique' (Q1792379)
        sparqlQuery = """select ?type where {{ wd:{qid} wdt:P31 ?type }}""".format(qid=qid)
        sparqlres = self.sparqlQuery(sparqlQuery)
        objectTypes = []
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                list = sparqlres.bindings
                for elmt in list:
                    objectTypes.append(elmt["type"].value.replace('http://www.wikidata.org/entity/', ''))
        return objectTypes

    def getWObjFct(self, fctname):
        return getattr(WikimediaAccess, fctname, None)

    def getQid(self, sparqlres, qid):
        return qid

    def piwigoLinkFromUrlSrc(self, urlSrc):
        # voir ticket 1800
        endpointScrutartState = "http://127.0.0.1:3030/scrutartState/sparql"
        sparqlFusekiWrapper = sw.wdqsWrapper2(endpointScrutartState)  # implicit JSON format
        queryTemplate = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            prefix wdt: <http://www.wikidata.org/prop/direct/> 
            prefix pgdc: <https://kg.grains-de-culture.fr/prop/> 
            select ?piwigoId ?title ?urlImage
            where {
              ?s wdt:P18 "__URL_IMAGE_SRC__";
                 rdfs:label ?title .
                ?s pgdc:piwigo_image ?piwigoId 
            }
        """
        query = queryTemplate.replace("__URL_IMAGE_SRC__", urlSrc)
        sparqlFusekiWrapper.setQuery(query)
        try:
            res = sparqlFusekiWrapper.queryAndConvert()
            if res and res.bindings:
                piwigoId = res.bindings[0]["piwigoId"].value
                piwigoUrl = f"https://galeries.grains-de-culture.fr/picture.php?/{piwigoId}"
                title = res.bindings[0]["title"].value
                return piwigoUrl, title
            else:
                None, None
        except Exception as e:
            logging.debug(e)
        return None, None # à affiner


    def get_file_extension_query_params(self, url):
        path = urlparse(url).path
        path_without_params, file_extension = os.path.splitext(path.split('?')[0])
        # _, file_extension = os.path.splitext(path_without_params)
        return file_extension

    def getTableBoxes(self, sparqlres, qid):
        # __IMAGES_TABLE_BOXES__
        imageFormats = ['jpg','jpeg','png','gif','webp','tif','tiff', 'eps', 'svg', 'psd', 'ai']
        boxes = ""
        images = [elmt["image"].value for elmt in sparqlres.bindings]
        count = 0
        for image in images:
            extension = self.get_file_extension_query_params(image).replace(".", "")
            if extension in imageFormats:
                piwigoLink, title = self.piwigoLinkFromUrlSrc(image)
                srcLink = image
                if piwigoLink:
                    boxes += f"""<td><a href="{piwigoLink}"><img class="wp-image-710" style="width: 200px;" src="{srcLink}" alt="{title}"></a></td>"""
                else:
                    boxes += f"""<td><a href="{image}"><img class="wp-image-710" style="width: 200px;" src="{image}" alt=""></a></td>"""
                count += 1
                if count>=3: break
        return boxes

    def getGalleryLink(self, sparqlres, qid):
        # __GALLERY_LINK__
        queryTemplate = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            prefix wd: <http://www.wikidata.org/entity/> 
            prefix wdt: <http://www.wikidata.org/prop/direct/> 
            prefix pgdc: <https://kg.grains-de-culture.fr/prop/> 
            select distinct ?galery
            where {
              ?s wdt:P18 ?urlImage;
                 wdt:P170 wd:__QID__;
                 pgdc:piwigo_gallery ?galery;
                 rdfs:label ?title .
                ?s pgdc:piwigo_image ?piwigoId .
                  filter not exists { ?s pgdc:piwigo_gallery <https://kg.grains-de-culture.fr/entity/galNone> }
            }        
            """
        TOKEN = '4444 5555 6666 7777'  # Remplacez par un Token valide
        # En-têtes de la requête
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {TOKEN}'
        }
        query = queryTemplate.replace("__QID__", qid)
        # Corps de la requête
        data = {
            'query': query
        }
        endpointScrutartState = "http://127.0.0.1:5000/query"
        sparqlScrutartWrapper = sw.wdqsWrapper2(endpointScrutartState)  # implicit JSON format
        sparqlScrutartWrapper.setQuery(query)
        link = ""
        try:
            # Envoie la requête POST à l'API
            res = requests.post(endpointScrutartState, headers=headers, json=data)
            if res and res.status_code == 200 and res.text:
                piwigoGaleryId = json.loads(res.text)["results"][0]["galery"].replace("https://kg.grains-de-culture.fr/entity/gal", "")
                galleryName = "Galerie"
                galleryLink = f"https://galeries.grains-de-culture.fr/index.php?/category/{piwigoGaleryId}"
                link = f"""<a href="{galleryLink}">{galleryName}</a>"""
            else:
                None
        except Exception as e:
            logging.debug(e)
        return link

    def getUrlImage(self, sparqlres, qid):
        url = None
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                imageFormats = ['jpg','jpeg','png','gif','webp','tif','tiff', 'eps', 'svg', 'psd', 'ai']
                list = sparqlres.bindings
                for elmt in list:
                    url = elmt["image"].value
                    extension = self.get_file_extension_query_params(url)
                    if extension in imageFormats:
                        break
        return url

    def getWikidataBarGraph(self, sparqlres, qid):
        url = "https://query.wikidata.org/embed.html#"
        url = url + quote(sparqlres)
        return url

    def getWDQSQuery(self, sparql):
        url = "https://query.wikidata.org/index.html#"
        url = url + quote(sparql)
        return url

    def sparqlQuery(self, query, format="json"):
        logging.debug("SPARQLQUERY " + query)
        self.wdqsWrapper.setQuery(query)
        try:
            res = self.wdqsWrapper.queryAndConvert()
            return res
        except Exception as e:
            logging.debug(e)

    def getName(self, sparqlres, qid):
        name = "???"
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                list = sparqlres.bindings
                name = list[0]["qidLabel"].value
        return name

    def getLink(self, sparqlres, qid):
        link = """<a href="">???</a>"""
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                list = sparqlres.bindings
                name = list[0]["qidLabel"].value
                uri = list[0]["qid"].value
                link = """<a href="{uri}">{name}</a>""".format(uri=uri, name=name)
        return link

    def getCurrentDate(self, sparqlres, qid):
        return str(datetime.date.today())

    def getInt(self, sparqlres, qid):
        value = 0
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                list = sparqlres.bindings
                value = list[0]["c"].value
        return int(value)

    def getLen(self, sparqlres, qid):
        value = 0
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                value = len(sparqlres.bindings)
        return int(value)

    def getMainType(self, sparqlres, qid, lang="fr"):
        value = ""
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                list = sparqlres.bindings
                name = list[0]["typeLabel"].value
                uri = list[0]["type"].value
                count = int(list[0]["c"].value)
                if (count > 1) and (lang == "fr"):
                    name += "s"
                value = "{count} {type}".format(count=str(count), type=name)
        return value

    def getOtherTypes(self, sparqlres, qid, lang="fr"):
        value = ""
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                list = sparqlres.bindings
                for type in list[1:]:
                    name = type["typeLabel"].value
                    uri = type["type"].value
                    count = int(type["c"].value)
                    if (count > 1) and (lang == "fr"):
                        name += "s"
                    if (count >= 10):
                        value += "{count} {type}, ".format(count=str(count), type=name)
                value += " et d'autres types d'oeuvres plus exceptionnels"
        return value

    def getValueLimit(self, object_type):
        limits = {
            "Q5": 8,  # humain
            "Q1792379": 5,  # genre artistique
            "Q16743958": 5 # genre pictural
        }
        return limits.get(object_type, 5)

    def getMainProp(selfself, object_type):
        main_props = {
            "Q5": "http://www.wikidata.org/prop/direct/P170",
            "Q1792379": "http://www.wikidata.org/prop/direct/P136", # genre artistique -> genre
            "Q16743958": "http://www.wikidata.org/prop/direct/P136" # genre pictural -> genre
        }
        return main_props.get(object_type, "http://www.wikidata.org/prop/direct/P136") # TODO attention, default douteux

    def getTable(self, sparqlres, qid, lang="fr"):
        value = ""
        entity_type = self.getTypes(qid)[0]
        limit = self.getValueLimit(entity_type)
        main_propuri = self.getMainProp(entity_type)
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                formatelmt = {
                    "http://www.wikidata.org/prop/direct/P571": "{value} ({count}), ",
                    "http://www.wikidata.org/prop/direct/P577": "{value} ({count}), ",
                    "http://www.wikidata.org/prop/direct/P2048": "{value} ({count}), ",  # height
                    "http://www.wikidata.org/prop/direct/P2049": "{value} ({count}), ",  # width
                }
                list = sparqlres.bindings
                for prop in list:
                    name = prop["propLabel"].value
                    propuri = prop["p"].value
                    propid = propuri.replace("http://www.wikidata.org/prop/direct/", "")
                    valuesList = ""
                    sparqlquery = """SELECT DISTINCT ?v ?vLabel ?c WHERE {
                              {
                                SELECT DISTINCT  ?v (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                  ?s <__MAINPROPID__> wd:__QID__;
                                    <__PROPURI__> ?v.
                                }
                                GROUP BY ?v
                                order by desc(?c)
                                LIMIT __LIMIT__ 
                              }
                              SERVICE wikibase:label { bd:serviceParam wikibase:language "fr, en". }
                            }
                            order by desc(?c)""".replace("__QID__", qid).replace("__PROPURI__", propuri).replace("__MAINPROPID__", main_propuri).replace("__LIMIT__", str(limit))
                    valuesList = ""
                    res = self.sparqlQuery(sparqlquery)
                    time.sleep(0.1)
                    if res and hasattr(res, "bindings"):
                        if len(res.bindings):
                            list = res.bindings
                            for elmt in list:
                                valLabel = elmt["vLabel"].value
                                uriVal = elmt["v"].value
                                count = elmt["c"].value
                                formatage = """<a href="{uri}">{value}</a> ({count}), """ if not propid in ["P571",
                                                                                                            "P577",
                                                                                                            "P2048",
                                                                                                            "P2049"] else "{value} ({count}), "

                                valuesList += formatage.format(
                                    uri=uriVal,
                                    value=valLabel if (propid != "P571") and (propid != "P577") else valLabel[0:4],
                                    count=count
                                )
                    value += """<tr><td><a href="{uriprop}">{pid}</a></td><td>{name}</td><td>{values}</td></tr>""".format(
                        name=name,
                        uriprop=propuri,
                        pid=propid,
                        values=valuesList
                    )
            else:
                value = ""
        else:
            value = ""
        return value

    def getItemList(self, sparqlres, qid):
        value = ""
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                list = sparqlres.bindings
                for elmt in list:
                    name = elmt["vLabel"].value
                    uri = elmt["v"].value
                    count = int(elmt["c"].value)
                    value += """      {name}\n""".format(name=name, uri=uri)
                    # value += """      <a href="{uri}">{name}</a>\n""".format(name=name, uri=uri)
        return value

    def getItemListSansMinus(self, sparqlres, qid):  # pas de - pour mermaid
        value = self.getItemList(sparqlres, qid)
        if value!="":
            value = value.replace("-", " ")
        return value

    def getGenreList(self, sparqlres, qid):
        value = self.getItemListSansMinus(sparqlres, qid)
        if value!="":
            value = "    Genres\n"+value
        return value

    def getDepictList(self, sparqlres, qid):
        value = self.getItemListSansMinus(sparqlres, qid)
        if value!="":
            value = "    Depicts\n"+value
        return value

    def getTypeList(self, sparqlres, qid):
        value = self.getItemListSansMinus(sparqlres, qid)
        value = "    Types\n"+value
        return value

    def getCountByLang(self, sparqlres, qid, lang):
        value = 0
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                list = sparqlres.bindings
                for elmt in list:
                    if elmt["lang"].value == lang:
                        value = elmt["c"].value
        return int(value)

    def getCountFr(self, sparqlres, qid):
        value = self.getCountByLang(sparqlres, qid, "fr")
        return value

    def getCountEn(self, sparqlres, qid):
        value = self.getCountByLang(sparqlres, qid, "en")
        return value

    def getEntityType(self, sparqlres, qid):
        type= ""
        return type

    def getExternalLinks(self, sparqlres, qid):
        imageFromBaseUrl = {
            "https://catalogue.bnf.fr/ark:/12148/cb$1": {
              "imageUrl":"https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/10/boutonBnf.svg" ,
              "alt": "link to BNF",
            },
            "https://www.universalis.fr/encyclopedie/$1/": {
              "imageUrl":"https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/10/boutonUniversalis.svg" ,
              "alt": "link to Encyclopedia Universalis",
            },
            "https://viaf.org/viaf/$1/": {
              "imageUrl":"https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/10/boutonViaf.svg",
              "alt": "link to VIAF",
            },
            "https://isni.org/isni/$1":{
              "imageUrl":"https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/10/boutonIsni.svg",
              "alt": "BNF link",
            },
            "http://arts-graphiques.louvre.fr/detail/artistes/1/$1": {
              "imageUrl":"https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/10/boutonLouvre.svg",
              "alt": "link to Louvre",
            },
            "https://www.getty.edu/vow/ULANFullDisplay?find=&role=&nation=&subjectid=$1": {
              "imageUrl":"https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/10/boutonGetty.svg",
              "alt": "link to Getty",
            },
            "https://www.getty.edu/vow/AATFullDisplay?find=&logic=AND&note=&subjectid=$1": {
              "imageUrl":"https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/10/boutonGetty.svg",
              "alt": "link to Getty",
            },
            "https://vocab.getty.edu/page/ulan/$1": {
                "imageUrl": "https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/10/boutonGetty.svg",
                "alt": "link to Getty",
            }
        }
        linkTemplate = """<td><a href="__LINK__"><img class="wp-image-710" style="width: 50px;" src="__IMAGELINK__" alt="__ALTLINK__"></a></td>"""
        externalLinks = ""
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                list = sparqlres.bindings
                for elmt in list:
                    if "link" in elmt:
                        link = elmt["link"].value
                        baseUrl = elmt["baseUrl"].value
                        imageDesc = imageFromBaseUrl.get(
                            baseUrl,
                            {"imageUrl":"https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/05/boutonScrutart-1.svg", "alt":"link"}
                        )
                        imageLink = imageDesc["imageUrl"]
                        imageAlt = imageDesc["alt"]
                        externalLinks += linkTemplate.replace("__LINK__", link).replace("__IMAGELINK__", imageLink).replace("__ALTLINK__",imageAlt)+"""\n"""
        return externalLinks


    