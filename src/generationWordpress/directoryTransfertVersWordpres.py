"""
prévu pour transférer des pages générées, par exemple avec
D:\wamp64\www\givingsense.eu\datamusee\python\datamusee\generationDocuments\generationWordpress\injectWordpressPages.py,
vers un wordpress
"""
import os
import logging
import json
import time

import orjson
import requests
import configPrivee
import SPARQLWrapper as sw
from dataConfig import dataConfig
import datetime


#api_url = f"{configPrivee.WORDPRESS_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_PASSWORD_APP}"
#auth = (configPrivee.WORDPRESS_USERNAME, configPrivee.WORDPRESS_PASSWORD_APP)
api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
api_url_get = f"{configPrivee.WORDPRESS_O2_API_URL}/posts"
auth = (configPrivee.WORDPRESS_O2_USERNAME, configPrivee.WORDPRESS_O2_PASSWORD_APP)
data = {
    "title": "Article de test d'automation 3",
    "content": "Article 3 injecté avec injectWordpressPages.py",
    "status": "draft",
    "slug": "article-test-automation",
    "lang":"fr"
}

def nettoyageContenu(page):
    if "<p><strong>0 pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>" in page:
        page = page.replace(
            "<p><strong>0 pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>",
            "Je n'ai trouvé aucune page dans Wikipedia associée à ces oeuvres")
        page = page.replace("<p>Dont 0 dans le Wikipedia anglophone et 0 dans le Wikidata francophone.</p>",
                     "Et bien sûr, il n'y a de page pour ces oeuvres ni dans le Wikipedia francophone, ni dans l'anglophone")
        page = page.replace("<p>L'ensemble des <strong>pages</strong> concerne <strong>0 œuvres</strong>.</p>",
                     "Et aussi, aucune de ces oeuvres n'est concernée par une page de Wikipedia.")
    if "<p>Il y a <strong>0 images</strong> dans Wikimedia Commons associées à ces œuvres.</p>" in page:
        page = page.replace("<p>Il y a <strong>0 images</strong> dans Wikimedia Commons associées à ces œuvres.</p>",
                     "Il n'a aucune image dans Wikimedia Commons associée à ces oeuvres.")
        pass
    return page

def sparqlQuery(endpoint, query, format="json"):
    sparql = sw.SPARQLWrapper2(endpoint)  # implicit JSON format
    logging.debug("SPARQLQUERY " + query)
    sparql.setQuery(query)
    try:
        res = sparql.queryAndConvert()
        return res
    except Exception as e:
        logging.debug(e)

def getName(sparqlres, qid):
    name = "???"
    if sparqlres and hasattr(sparqlres, "bindings"):
        if len(sparqlres.bindings):
            list = sparqlres.bindings
            name = list[0]["qidLabel"].value
    return name

def getTitle(qid):
    endpoint = "https://query.wikidata.org/sparql"
    sparqlquery = """select distinct ?qid ?qidLabel where { values ?qid { <http://www.wikidata.org/entity/__QID__> }  
                    SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],fr,en". } }""".replace("__QID__", qid)
    time.sleep(5)
    res = sparqlQuery(endpoint, sparqlquery)
    title = None
    name = getName(res, qid)
    if name!="???":
        # title = "Où trouver __NOMCREATEUR__ dans Wikidata, suivez le guide".replace("__NOMCREATEUR__", name)
        title = dataConfig["__TITRE_TEMPLATE__"]["template"].replace("__NOMCREATEUR__", name)
    return title

def getLogTransfert(path):
    jsonlist = []
    with open(path, "r", encoding="utf-8") as logfile:
        txt = logfile.read()
        if len(txt):
            jsonlist = [json.loads(jline) for jline in txt.splitlines()]
    return jsonlist

if __name__ == '__main__':
    # contents prohibited
    filtersBlackList = [
        "<strong>0 pages</strong>",
        " 0 dans",
        "<strong>0 œuvres</strong>",
        "<strong>0 images</strong>",
        """<figure class="wp-block-image size-large"><img src="None"""
    ]
    # contents necessary
    filtersWhiteList = [
        "processParams"
    ]
    srcdir = "./pages"
    listfiles = os.listdir(srcdir)
    logsfile = "./logs/logTransfertScrutart.jsonl"
    logs = getLogTransfert(logsfile)
    for file in listfiles:
        if ".wp" in file:
            with open(srcdir+"/"+file, "r", encoding="UTF-8") as page:
                qid = file.replace(".wp", "")
                title = getTitle(qid)
                if not title:
                    print(qid, " nom pas accessible")
                    continue
                content = page.read()
                skip = False
                content = nettoyageContenu(content)
                for filt in filtersBlackList: # filtrage de pages avec un contenu à améliorer
                    if filt in content:
                        print(file)
                        skip = True
                        continue
                for filt in filtersWhiteList:
                    if not filt in content:
                        skip = True
                        continue
                if not skip:
                    # ici envoyer vers Wordpress
                    print("---> envoyer ", file)
                    data = {
                        "title": title,
                        "content": content,
                        "categories": [8, 31, 29],
                        "status": "draft", # publish
                        # "slug": "article-test-automation",
                        "lang": "fr"
                    }
                    for log in logs:
                        if not type(log) == dict:
                            continue
                        if log["qid"]!=qid:
                            continue
                        statusOK = ["201", "200"]
                        if "idwordpress" in log and log["status"] in statusOK:
                            data["id"] = log["idwordpress"]
                    if "id" in data:
                        response = requests.post(api_url.replace("v2/posts", "v2/posts/{id}".format(id=data["id"])), json=data, auth=auth)
                    else:
                        response = requests.post(api_url, json=data, auth=auth)
                    with open(logsfile, "a+", encoding="UTF-8") as flog:
                        # il y a des \n dans le contenu => ça ne se prête pas à lire du json-line
                        # json.dump({ "qid": qid, "content": response.content.decode("utf-8") }, flog, ensure_ascii=False)
                        content = json.loads(response.content.decode("utf-8"))
                        json.dump({ "qid": qid, "title": title, "idwordpress": content["id"],
                                    "status": str(response.status_code), "date": str(datetime.datetime.now()) }, flog, ensure_ascii=False)
                        flog.write("\n")