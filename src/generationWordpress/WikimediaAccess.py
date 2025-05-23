import logging
import SPARQLWrapper as sw
from urllib.parse import quote
import datetime
from urllib.parse import urlparse
import os
from WikimediaManagerPackage.configPrivee import config
import time
from urllib.parse import urlencode, urlunsplit
# from WikimediaManagerPackage import configPrivee
import requests
import json
import uuid
import socketio

sio = None

baseurl = "http://127.0.0.1:6000"
#baseurl = "https://webapimanager.grains-de-culture.fr"

def createManager(targetUrls, bearer=None):
    data = {"api_urls": targetUrls }
    headers = {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"} if bearer else {}
    # create manager
    resp = requests.post(f"{baseurl}/api/initialize", json=data, headers=headers)
    jsonrep = json.loads(resp.text)
    manager_id = jsonrep["manager_id"] if "manager_id" in jsonrep else None
    return manager_id

def deleteManager(manager_id, bearer=None):
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    url = f"{baseurl}/api/delete_manager"
    response = requests.delete(f"{url}?manager_id={manager_id}", headers=headers)
    ok = (response.status_code == 200)
    return ok

"""
Tous les accès à des outils Wikimedia devraient passer par un objet de ce type unique
afin de gérer les limites sur ces accès:
- nécessité d'avoir un User-Agent bien défini
- nombre de requêtes par minute
...
Idéalement, je devrais en faire une api et tous les programmes passeraient par cette API
Avec dans l'API, un mécanisme de file d'attente et/ou un mécanisme de type 'ré-essayer plus tard"
(cela se gère normalement en envoyant une erreur 409 pour dire que le serveur d'API refuse la requête pour le moment; peut-être que WDQS envoie des erreurs 409)
par exemple, une requête sparql wdqs est mise en file d'attente et la réponse est juste une url à interroger pour voir si
la réponse est prête et l'obtenir si elle est prête
cela permet aussi de faire au mieux et d'envoyer des requêtes en masse

"""

import socketio

class SocketClient:
    def __init__(self, server_url):
        # Initialize the Socket.IO client
        self.server_url = server_url
        self.sio = socketio.Client()
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        # Set up event handlers
        @self.sio.event
        def connect():
            try:
                print("Connected to server.")
            except Exception as e:
                print(f"Failed to connect in _setup_event_handlers")

        @self.sio.event
        def disconnect():
            print("Disconnected from server.")

        @self.sio.event
        def message(data):
            print(f"Message received: {data}")

    def connect(self):
        # Connect to the server
        try:
            self.sio.connect(self.server_url)
        except Exception as e:
            print(f"Failed to connect to {self.server_url}: {e}")

    def disconnect(self):
        # Disconnect from the server
        self.sio.disconnect()

    def send_message(self, event, data):
        # Send a custom event with data to the server
        if self.sio.connected:
            self.sio.emit(event, data)
        else:
            print("Client is not connected to the server.")

    def on_event(self, event, handler):
        # Dynamically set up a custom event handler
        self.sio.on(event, handler)

# Example usage
if __name__ == "__main__":
    client = SocketClient("http://localhost:5000")

    # Custom handler for a specific event
    def custom_handler(data):
        print(f"Custom event received: {data}")

    # Register custom handler
    client.on_event("custom_event", custom_handler)

    # Connect to the server
    client.connect()

    # Send a custom event
    client.send_message("custom_event", {"message": "Hello, server!"})

    # Wait for a while to handle events (for demonstration)
    import time
    time.sleep(5)

    # Disconnect from the server
    client.disconnect()

class WikimediaAccess:
    def __init__(self, qid, lang="fr"):
        self.qid = qid
        self.lang = lang
        # code serveur generationWordpress\tools\WikimediaManager\WikimediaManagerPackage\apiManager.py
        self.baseurl = "http://127.0.0.1:6000" # ça si local, https://webapimanager.grains-de-culture.fr si o2
        self.bearer = config["admin"]["Bearer"]
        wdqsEndpoint = "https://query.wikidata.org/sparql"
        targetUrls=[ wdqsEndpoint]
        data = {"api_urls": targetUrls}
        self.headers = {"Authorization": f"Bearer {self.bearer}", "Content-Type": "application/json"} if self.bearer else {}
        # create manager
        resp = requests.post(f"{self.baseurl}/api/initialize", json=data, headers=self.headers)
        self.manager_id = json.loads(resp.text)["manager_id"]
        self.setFormat()
        self.setWdqsEndpoint()
        self.setWdqsAgent()
        data = {
            "manager_id": self.manager_id,
            "limit": 1.0/10.0 # un appel toutes les 10 secondes
        }
        # limit est le nombre d'appels par seconde pour ce manager
        lim = requests.post(f"{self.baseurl}/api/set_rate_limit", json=data, headers=self.headers)
        sio = socketio.Client()
        sio.connect(self.baseurl)
        self.sio = sio
        # Créer une instance du client Socket.IO

    def setFormat(self, format="JSON"):
        self.returnFormat = format
        return format

    def getWdqsFormat(self):
        return self.returnFormat

    def setWdqsEndpoint(self, endpoint="https://query.wikidata.org/sparql"):
        self.wdqsEndpoint = endpoint
        return endpoint

    def setWdqsAgent(self, agent='Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)'):
        self.agent = agent
        return agent

    def getWdqsAgent(self):
        return self.agent

    def getOccupations(self, qid):
        sparqlQuery = """select ?occupation where {{ wd:{qid} wdt:P106 ?occupation }}""".format(qid=qid)
        sparqlres = self.sparqlQuery(sparqlQuery)
        occupations = []
        if type(sparqlres)==dict:
            if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
                if len(sparqlres["results"]["bindings"]):
                    list = sparqlres["results"]["bindings"]
                    for elmt in list:
                        occupations.append(elmt["occupation"]["value"].replace('http://www.wikidata.org/entity/', ''))
        else:
            if sparqlres and hasattr(sparqlres, "bindings"):
                if len(sparqlres.bindings):
                    list = sparqlres.bindings
                    for elmt in list:
                        occupations.append(elmt["occupation"].value.replace('http://www.wikidata.org/entity/', ''))
        return occupations

    def getTypes(self, qid):
        # aller chercher une valeur de instance of (P31) pour le QID donné
        # pour un peintre comme Carolus Duran, son type P31 est 'être humain' (Q5)
        # il faudra alors, dans certains cas, extérieurement, trouver son occupation 'artiste peintre' (Q1028181)
        # pour une peinture, comme Mona Lisa, on aura P31 peinture (Q3305213)
        # pour un genre (P136), on aura P31 'genre artistique' (Q1792379)
        sparqlQuery = """select ?type where {{ wd:{qid} wdt:P31 ?type }}""".format(qid=qid)
        sparqlres = self.sparqlQuery(sparqlQuery)
        objectTypes = []
        if type(sparqlres)==dict:
            if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
                if len(sparqlres["results"]["bindings"]):
                    list = sparqlres["results"]["bindings"]
                    for elmt in list:
                        objectTypes.append(elmt["type"]["value"].replace('http://www.wikidata.org/entity/', ''))
        else:
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
        sparqlFusekiWrapper = sw.SPARQLWrapper2(endpointScrutartState)  # implicit JSON format
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
        if type(sparqlres)==dict:
            images = [elmt["image"]["value"] for elmt in sparqlres["results"]["bindings"]]
        else:
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
            select distinct ?gallery
            where {
              ?s wdt:P18 ?urlImage;
                 wdt:P170 wd:__QID__;
                 pgdc:piwigo_gallery ?gallery;
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
        endpointScrutartState = "http://127.0.0.1:3030/scrutartState/query"
        sparqlScrutartWrapper = sw.SPARQLWrapper2(endpointScrutartState)  # implicit JSON format
        sparqlScrutartWrapper.setQuery(query)
        logging.debug("SPARQLQUERY " + query)
        link = ""
        try:
            # Envoie la requête POST à l'API
            # res = requests.get(endpointScrutartState, headers=headers, json=data)
            res = sparqlScrutartWrapper.queryAndConvert()
            if res and res.bindings:
                piwigoGalleryId = res.bindings[0]["gallery"].value.replace("https://kg.grains-de-culture.fr/entity/gal", "")
                galleryName = "Galerie"
                galleryLink = f"https://galeries.grains-de-culture.fr/index.php?/category/{piwigoGalleryId}"
                link = f"""<a href="{galleryLink}">{galleryName}</a>"""
            else:
                None
        except Exception as e:
            logging.debug(e)
        return link

    def getUrlImage(self, sparqlres, qid):
        url = None
        imageFormats = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'tif', 'tiff', 'eps', 'svg', 'psd', 'ai']
        if type(sparqlres)==dict:
            if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
                if len(sparqlres["results"]["bindings"]):
                    list = sparqlres["results"]["bindings"]
                    for elmt in list:
                        url = elmt["image"]["value"]
                        extension = self.get_file_extension_query_params(url)
                        if extension in imageFormats:
                            break
        else:
            if sparqlres and hasattr(sparqlres, "bindings"):
                if len(sparqlres.bindings):
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

    def sparqlQuery(self, query, format=None):
        bearer = config['admin']["Bearer"]
        headers = {f"Authorization": f"Bearer {bearer}"} if bearer else {}
        manager_id = createManager(["https://query.wikidata.org/sparql"], bearer=bearer)
        # limit est le nombre d'appels par seconde pour ce manager
        data = { "manager_id": manager_id, "limit": 0.5 }
        lim = requests.post(f"{baseurl}/api/set_rate_limit", json=data, headers=headers)
        cachedur = 600  # 0;  en secondes
        parameters = {"query": query, "format": format if format else "JSON"}
        encodedquery = urlencode(query=parameters, doseq=True)
        data = {
            "manager_id": manager_id,
            "url": urlunsplit(("https", "query.wikidata.org", "/sparql", encodedquery, "")),
            "method": "GET",
            "cache_duration": cachedur,
            "headers": {
                "User-Agent": "Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)"
            }
        }
        # mise de la requête dans la file d'attente
        req = requests.get(f"{baseurl}/api/request", json=data, headers=headers)
        uuidreq = json.loads(req.text)["uuid"]
        statusUrl = f"{baseurl}{json.loads(req.text)['status_url']}"
        while True:
            stat = requests.get(statusUrl, headers=headers)
            jstat = json.loads(stat.text)
            if "status" in jstat and jstat["status"] == "complete":
                rep = jstat["response"]
                break
            elif "status" in jstat and jstat["status"] == "pending":
                time.sleep(0.3)
            else:
                # print(jstat)
                pass
        deleteManager(manager_id, bearer=bearer)
        # TODO gérer correctement d'autres formats de sortie que JSON
        #if format==None or format== "JSON":
        #    rep = json.loads(rep)
        return rep

    def sparqlQuery2(self, query, format=None):
        logging.debug("SPARQLQUERY " + query)
        parameters = {
            "query": query,
            "format": format if format else self.returnFormat
        }
        encodedquery = urlencode(query=parameters, doseq=True)
        # Générer un client_id unique
        client_id = str(uuid.uuid4())  # Identifiant unique pour ce client
        # Soumettre une requête via /api/request
        cachedur = 600  # 0;  en secondes
        data = {
            "manager_id": self.manager_id,
            "url": urlunsplit(("https", "query.wikidata.org", "/sparql", encodedquery, "")),
            "method": "GET",
            "cache_duration": cachedur,
            "headers": self.headers,
            "client_id": client_id
        }
        req = requests.post(f"{self.baseurl}/api/request", json=data, headers=self.headers)
        uuidreq = json.loads(req.text)["uuid"]
        logging.debug(f"id de requête: {uuidreq}")
        statusUrl = f"{self.baseurl}{json.loads(req.text)['status_url']}"
        logging.debug(f"status url: {req.text}")
        self.sio.wait()
        # res = self.wdqsWrapper.queryAndConvert()
        # return res

    def getName(self, sparqlres, qid):
        name = "???"
        if type(sparqlres)==dict:
            if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
                if len(sparqlres["results"]["bindings"]):
                    list = sparqlres["results"]["bindings"]
        else:
            if sparqlres and hasattr(sparqlres, "bindings"):
                if len(sparqlres.bindings):
                    list = sparqlres.bindings
        name = list[0]["qidLabel"].value if hasattr(list[0]["qidLabel"], "value") else list[0]["qidLabel"]["value"]
        return name

    def getLink(self, sparqlres, qid):
        link = """<a href="">???</a>"""
        if type(sparqlres)==dict:
            if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
                if len(sparqlres["results"]["bindings"]):
                    list = sparqlres["results"]["bindings"]
                    name = list[0]["qidLabel"]["value"]
                    uri = list[0]["qid"]["value"]
                    link = """<a href="{uri}">{name}</a>""".format(uri=uri, name=name)
        else:
            if sparqlres and hasattr(sparqlres, "bindings"):
                if len(sparqlres.bindings):
                    list = sparqlres.bindings
        name = list[0]["qidLabel"].value if hasattr(list[0]["qidLabel"], "value") else list[0]["qidLabel"]["value"]
        uri = list[0]["qid"].value if hasattr(list[0]["qid"], "value") else list[0]["qid"]["value"]
        link = """<a href="{uri}">{name}</a>""".format(uri=uri, name=name)
        return link

    def getCurrentDate(self, sparqlres, qid):
        return str(datetime.date.today())

    def getInt(self, sparqlres, qid):
        value = 0
        list = []
        if type(sparqlres)==dict:
            if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
                if len(sparqlres["results"]["bindings"]):
                    list = sparqlres["results"]["bindings"]
                    value = list[0]["c"]["value"]
        else:
            if sparqlres and hasattr(sparqlres, "bindings"):
                if len(sparqlres.bindings):
                    list = sparqlres.bindings
        value = list[0]["c"].value if hasattr(list, "value") else list[0]["c"]["value"]
        return int(value)

    def getLen(self, sparqlres, qid):
        value = 0
        if sparqlres:
            value = len(sparqlres.bindings) if hasattr(sparqlres, "bindings") else len(sparqlres["results"]["bindings"])
        return int(value)

    def getMainType(self, sparqlres, qid):
        value = ""
        if sparqlres:
            if type(sparqlres)==dict:
                if  "results" in sparqlres and "bindings" in sparqlres["results"]:
                    if len(sparqlres["results"]["bindings"]):
                        list = sparqlres["results"]["bindings"]
                        name = list[0]["typeLabel"]["value"]
                        uri = list[0]["type"]["value"]
                        count = int(list[0]["c"]["value"])
                        if (count > 1) and (self.lang == "fr"):
                            name += "s"
                        value = "{count} {type}".format(count=str(count), type=name)
            else:
                if len(sparqlres.bindings):
                    list = sparqlres.bindings
                    name = list[0]["typeLabel"].value
                    uri = list[0]["type"].value
                    count = int(list[0]["c"].value)
                    if (count > 1) and (self.lang == "fr"):
                        name += "s"
                    value = "{count} {type}".format(count=str(count), type=name)
        return value

    def getOtherTypes(self, sparqlres, qid):
        value = ""
        list = []
        if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
            if len(sparqlres["results"]["bindings"]):
                list = sparqlres["results"]["bindings"]
        else:
            if sparqlres and hasattr(sparqlres, "bindings"):
                if len(sparqlres.bindings):
                    list = sparqlres.bindings
        for type in list[1:]:
            name = type["typeLabel"].value  if hasattr(type["typeLabel"], "value") else type["typeLabel"]["value"]
            uri = type["type"].value  if hasattr(type["type"], "value") else type["type"]["value"]
            count = int(type["c"].value  if hasattr(type["c"], "value") else type["c"]["value"])
            if (count > 1) and (self.lang == "fr"):
                name += "s"
            if (count >= 10):
                value += "{count} {type}, ".format(count=str(count), type=name)
        otherTypes = {
            "fr":" et d'autres types d'oeuvres plus exceptionnels.",
            "en": " and other more exceptional types of work.",
            "es": " y otros tipos de trabajo más excepcionales.",
        }
        value += otherTypes[self.lang]
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

    def getTable(self, sparqlres, qid):
        value = ""
        entity_type = self.getTypes(qid)[0]
        limit = self.getValueLimit(entity_type)
        main_propuri = self.getMainProp(entity_type)
        formatelmt = {
            "http://www.wikidata.org/prop/direct/P571": "{value} ({count}), ",
            "http://www.wikidata.org/prop/direct/P577": "{value} ({count}), ",
            "http://www.wikidata.org/prop/direct/P2048": "{value} ({count}), ",  # height
            "http://www.wikidata.org/prop/direct/P2049": "{value} ({count}), ",  # width
        }
        list = []
        if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
            if len(sparqlres["results"]["bindings"]):
                list = sparqlres["results"]["bindings"]
        else:
            if sparqlres and hasattr(sparqlres, "bindings"):
                if len(sparqlres.bindings):
                    list = sparqlres.bindings
        value = ""
        for prop in list:
            name = prop["propLabel"].value if hasattr(prop["propLabel"], "value") else prop["propLabel"]["value"]
            propuri = prop["p"].value if hasattr(prop["p"], "value") else prop["p"]["value"]
            propid = propuri.replace("http://www.wikidata.org/prop/direct/", "")
            valuesList = ""
            sparqlquery = f"""SELECT DISTINCT ?v ?vLabel ?c WHERE {{
                      {{
                        SELECT DISTINCT  ?v (COUNT(DISTINCT ?s) AS ?c) WHERE {{
                          ?s <__MAINPROPID__> wd:__QID__;
                            <__PROPURI__> ?v.
                        }}
                        GROUP BY ?v
                        order by desc(?c)
                        LIMIT __LIMIT__ 
                      }}
                      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{self.lang}, en". }}
                    }}
                    order by desc(?c)""".replace("__QID__", qid).replace("__PROPURI__", propuri).replace("__MAINPROPID__", main_propuri).replace("__LIMIT__", str(limit))
            valuesList = ""
            res = self.sparqlQuery(sparqlquery)
            time.sleep(0.1)
            listval = []
            if res and "results" in res and "bindings" in res["results"]:
                if len(res["results"]["bindings"]):
                    listval = res["results"]["bindings"]
            else:
                if res and hasattr(res, "bindings"):
                    if len(res.bindings):
                        listval = res.bindings
            for elmt in listval:
                valLabel = elmt["vLabel"].value  if hasattr(elmt["vLabel"], "value") else elmt["vLabel"]["value"]
                uriVal = elmt["v"].value  if hasattr(elmt["v"], "value") else elmt["v"]["value"]
                count = elmt["c"].value  if hasattr(elmt["c"], "value") else elmt["c"]["value"]
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
        return value

    def getItemList(self, sparqlres, qid):
        value = ""
        if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
            if len(sparqlres["results"]["bindings"]):
                list = sparqlres["results"]["bindings"]
                for elmt in list:
                    name = elmt["vLabel"]["value"]
                    uri = elmt["v"]["value"]
                    count = int(elmt["c"]["value"])
                    value += """      {name}\n""".format(name=name, uri=uri)
                    # value += """      <a href="{uri}">{name}</a>\n""".format(name=name, uri=uri)
        else:
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
            branch = {
                "fr": "    Genres\n",
                "en": "    Genres\n",
                "es": "    Genres\n",
            }
            value = branch[self.lang] + value
        return value

    def getDepictList(self, sparqlres, qid):
        value = self.getItemListSansMinus(sparqlres, qid)
        if value!="":
            branch = {
                "fr": "    Illustre\n",
                "en": "    Depicts\n",
                "es": "    Representa\n",
            }
            value = branch[self.lang]+value
        return value

    def getTypeList(self, sparqlres, qid):
        value = self.getItemListSansMinus(sparqlres, qid)
        if value!="":
            branch = {
                "fr": "    Types\n",
                "en": "    Types\n",
                "es": "    Tipos\n",
            }
            value = branch[self.lang] + value
        return value

    def getCountByLang(self, sparqlres, qid, lang):
        value = 0
        if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
            if len(sparqlres["results"]["bindings"]):
                list = sparqlres["results"]["bindings"]
                for elmt in list:
                    if elmt["lang"]["value"] == lang:
                        value = elmt["c"]["value"]
        else:
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
        if type(sparqlres)==dict:
            if sparqlres and "results" in sparqlres and "bindings" in sparqlres["results"]:
                if len(sparqlres["results"]["bindings"]):
                    list = sparqlres["results"]["bindings"]
                    for elmt in list:
                        if "link" in elmt:
                            link = elmt["link"]["value"]
                            baseUrl = elmt["baseUrl"]["value"]
                            imageDesc = imageFromBaseUrl.get(
                                baseUrl,
                                {
                                    "imageUrl": "https://scrutart.grains-de-culture.fr/wp-content/uploads/2024/05/boutonScrutart-1.svg",
                                    "alt": "lien interne scrutart"
                                }
                            )
                            imageLink = imageDesc["imageUrl"]
                            imageAlt = imageDesc["alt"]
                            externalLinks += linkTemplate.replace("__LINK__", link).replace("__IMAGELINK__",
                                                                                            imageLink).replace(
                                "__ALTLINK__", imageAlt) + """\n"""
        else:
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


    