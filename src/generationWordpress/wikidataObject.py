import logging
import SPARQLWrapper as sw
from urllib.parse import quote
import datetime
import time

class WikidataObject:
    associatedEndpoint = "https://query.wikidata.org/sparql" # default is WDQS
    sparqlWrapper = sw.SPARQLWrapper2(associatedEndpoint)  # implicit JSON format
    sparqlWrapper.agent = 'Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)'

    def __init__(self, qid):
        self.qid = qid
        pass

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
        return getattr(WikidataObject, fctname, None)

    def getQid(self, sparqlres, qid):
        return qid
    def getUrlImage(self, sparqlres, qid):
        url = None
        if sparqlres and hasattr(sparqlres, "bindings"):
            if len(sparqlres.bindings):
                list = sparqlres.bindings
                for elmt in list:
                    url = elmt["image"].value
                    if (".jpg" in url) or (".png" in url):
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
        self.sparqlWrapper.setQuery(query)
        try:
            res = self.sparqlWrapper.queryAndConvert()
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