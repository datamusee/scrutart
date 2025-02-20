# but: générer des contenus prêts à être intégrés dans un wordpress
# part d'un template basé sur le billet
# https://datamusee.wp.imt.fr/fr/2024/01/12/paul-gauguin-dans-wikidata/
# récupération de la source de cette page comme base de template
# ce source est copié de generationWordpress\generationCreateursFrAnalysesWikidata.py
# et doit être modifié pour traiter des mouvements au lieu des créateurs
# cela nécessite notamment de modifier le template
# il parait souhaitable d'homogénéiser le code pour les différentes langues et les différents thèmes
import json
import logging
import SPARQLWrapper as sw
import time
import datetime
from urllib.parse import quote
import os

def getUrlImage(sparqlres, qid):
    url = None
    if sparqlres and hasattr(sparqlres, "bindings"):
        if len(sparqlres.bindings):
            list = sparqlres.bindings
            for elmt in list:
                url = elmt["image"].value
                if (".jpg" in url) or (".png" in url):
                    break
    return url

def getWikidataBarGraph(sparqlres, qid):
    url = "https://query.wikidata.org/embed.html#"
    url = url+quote(sparqlres)
    return url

def getWDQSQuery(sparql):
    url = "https://query.wikidata.org/index.html#"
    url = url+quote(sparql)
    return url

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

def getLink(sparqlres, qid):
    link = """<a href="">???</a>"""
    if sparqlres and hasattr(sparqlres, "bindings"):
        if len(sparqlres.bindings):
            list = sparqlres.bindings
            name = list[0]["qidLabel"].value
            uri = list[0]["qid"].value
            link = """<a href="{uri}">{name}</a>""".format(uri=uri, name=name)
    return link


def getExternalLinksTable(sparqlres, qid):
    linksTable = """ """
    if sparqlres and hasattr(sparqlres, "bindings"):
        if len(sparqlres.bindings):
            list = sparqlres.bindings
            pass
    return linksTable

def getCurrentDate(sparqlres, qid):
    return str(datetime.date.today())

def getInt(sparqlres, qid):
    value = 0
    if sparqlres and hasattr(sparqlres, "bindings"):
        if len(sparqlres.bindings):
            list = sparqlres.bindings
            value = list[0]["c"].value
    return int(value)


def getLen(sparqlres, qid):
    value = 0
    if sparqlres and hasattr(sparqlres, "bindings"):
        if len(sparqlres.bindings):
            value = len(sparqlres.bindings)
    return int(value)


def getMainType(sparqlres, qid, lang="fr"):
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


def getOtherTypes(sparqlres, qid, lang="fr"):
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
            value += " et d'autres types d'œuvres plus exceptionnels"
    return value


def getTable(sparqlres, qid, lang="fr"):
    value = ""
    if sparqlres and hasattr(sparqlres, "bindings"):
        if len(sparqlres.bindings):
            formatelmt = {
                "http://www.wikidata.org/prop/direct/P571" : "{value} ({count}), ",
                "http://www.wikidata.org/prop/direct/P577" : "{value} ({count}), ",
                "http://www.wikidata.org/prop/direct/P2048": "{value} ({count}), ", # height
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
                              ?s wdt:P170 wd:__QID__;
                                <__PROPID__> ?v.
                            }
                            GROUP BY ?v
                            HAVING (?c > 8 )
                          }
                          SERVICE wikibase:label { bd:serviceParam wikibase:language "fr". }
                        }
                        order by desc(?c)""".replace("__QID__", qid).replace("__PROPID__", propuri)
                valuesList = ""
                res = sparqlQuery(endpoint, sparqlquery)
                time.sleep(0.1)
                if res and hasattr(res, "bindings"):
                    if len(res.bindings):
                        list = res.bindings
                        for elmt in list:
                            valLabel = elmt["vLabel"].value
                            uriVal = elmt["v"].value
                            count = elmt["c"].value
                            formatage = """<a href="{uri}">{value}</a> ({count}), """ if not propid in ["P571","P577","P2048", "P2049"] else "{value} ({count}), "

                            valuesList += formatage.format(
                                uri=uriVal,
                                value=valLabel if (propid!="P571")and(propid!="P577") else valLabel[0:4],
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

def getItemList(sparqlres, qid):
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

def getItemListSansMinus(sparqlres, qid): # pas de - pour mermaid
    value = getItemList(sparqlres, qid)
    value = value.replace("-", " ")
    return value

def getCountByLang(sparqlres, qid, lang):
    value = 0
    if sparqlres and hasattr(sparqlres, "bindings"):
        if len(sparqlres.bindings):
            list = sparqlres.bindings
            for elmt in list:
                if elmt["lang"].value==lang:
                    value = elmt["c"].value
    return int(value)

def getCountFr(sparqlres, qid):
    value = getCountByLang(sparqlres, qid, "fr")
    return value

def getCountEn(sparqlres, qid):
    value = getCountByLang(sparqlres, qid, "en")
    return value


# liste de requêtes sparql utiles pour construire une page
sparqlList = {
    "__DATE__": {"sparql": None,
                      "filtres": [{"filtre": getCurrentDate, "key": "__DATE__"}],
                      "urlquery": None},
    "__NOMCREATEUR__": {
        "sparql": """select distinct ?qid ?qidLabel where { values ?qid { <http://www.wikidata.org/entity/__QID__> }  
                    SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],fr,en". } }
                    """,
        "filtres": [{"filtre": getName, "key": "__NOMCREATEUR__"}],
        "urlquery": "__QUERYLABELEDLINK__"},
    "__LINKCREATEUR__": {
        "sparql": """select distinct ?qid ?qidLabel where { values ?qid { <http://www.wikidata.org/entity/__QID__> }  
                    SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],fr,en". } }
                    """,
        "filtres": [{"filtre": getLink, "key": "__LINKCREATEUR__"}],
        "urlquery": ""},
    "__NBOEUVRES__": {"sparql": "select (count(?s) as ?c) where { ?s wdt:P170 wd:__QID__ }",
                      "filtres": [{"filtre": getInt, "key": "__NBOEUVRES__"}],
                      "urlquery": "__QUERYNBOEUVRES__"},
    "__NBTYPES__": {"sparql": """select ?type ?typeLabel (count(?s) as ?c) where {
                          ?s wdt:P170 wd:__QID__; wdt:P31 ?type
                            SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],fr,en". }
                            } group by ?type ?typeLabel
                            order by desc(?c)""",
                    "filtres": [
                        {"filtre": getMainType, "key": "__NBMAINTYPE__"},
                        {"filtre": getOtherTypes, "key": "__NBOTHERTYPES__"},
                    ],
                    "urlquery": "__QUERYNBPARTYPES__"},
    "__NBPPROP__": {"sparql": "select (count(distinct ?p) as ?c) where { ?s wdt:P170 wd:__QID__; ?p [] }",
                    "filtres": [{"filtre": getInt, "key": "__NBPPROP__"}],
                    "urlquery": "__QUERYNBPROPRIETES__"},
    "__NBPROP50PLUS__": {"sparql": """select (count(?p) as ?c)
                                    where {
                                      {
                                        select  (count(distinct ?s) as ?nboeuvres) where { ?s wdt:P170 wd:__QID__ } 
                                      }
                                        {
                                        select ?p (count(distinct ?s) as ?oeuvresparprop) 
                                               where { ?s wdt:P170 wd:__QID__; ?p [] } 
                                        group by ?p 
                                      }
                                      filter(!contains(str(?p), "schema:"))
                                      filter(!contains(str(?p), "wikiba.se:"))
                                      filter(contains(str(?p), "direct"))
                                        bind ( (xsd:float(?nboeuvres)/2.0) as ?demi)
                                      filter(?oeuvresparprop>?demi)
                                    }
                                    """,
                         "filtres": [{"filtre": getInt, "key": "__NBPROP50PLUS__"}],
                         "urlquery": "__QUERYNBPROP50PLUS__"},
    "__NBPAIRESPROPVAL8__": {"sparql": """select distinct ?p ?v (count(distinct ?s) as ?c) where { ?s wdt:P170 wd:__QID__;
                                             ?p ?v 
                                             filter(?p!=schema:description)           
                                        } group by ?p ?v
                                        HAVING (?c>8)""",
                             "filtres": [{"filtre": getLen, "key": "__NBPAIRESPROPVAL8__"}],
                             "urlquery": "__QUERYPAIRESPROPVAL8__"},
    "__NBPROPPROPVAL8__": {"sparql": """SELECT DISTINCT ?p ?propLabel WHERE {
                                          {
                                            SELECT DISTINCT ?p ?v (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                              ?s wdt:P170 wd:__QID__;
                                                ?p ?v.
                                              FILTER(?p != schema:description)
                                            }
                                            GROUP BY ?p ?v
                                            HAVING (?c > 8 )
                                          }
                                          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
                                          ?prop wikibase:directClaim ?p.
                                        }""",
                           "filtres": [
                               {"filtre": getLen, "key": "__NBPROPPROPVAL8__"},
                               {"filtre": getTable, "key": "__TABLEPROPVAL8__"}
                           ],
                           "urlquery": "__QUERYPROPPROPVAL8__"},
    "__GENRELIST__": {"sparql": """SELECT DISTINCT ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                  ?s wdt:P170 wd:__QID__;
                                    wdt:P136 ?v.
                                  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],fr,en". }
                                }
                                GROUP BY ?v ?vLabel
                                HAVING (?c > 8 )
                                ORDER BY DESC (?c)""",
                        "filtres": [{"filtre": getItemListSansMinus, "key": "__GENRELIST__"}],
                        "urlquery": ""},
    "__DEPICTLIST__": {"sparql": """SELECT DISTINCT ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                  ?s wdt:P170 wd:__QID__;
                                    wdt:P180 ?v.
                                  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],fr,en". }
                                }
                                GROUP BY ?v ?vLabel
                                HAVING (?c > 8 )
                                ORDER BY DESC (?c)""",
                       "filtres": [{"filtre": getItemListSansMinus, "key": "__DEPICTLIST__"}],
                           "urlquery": ""},
    "__TYPELIST__": {"sparql": """SELECT DISTINCT ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                  ?s wdt:P170 wd:__QID__;
                                    wdt:P31 ?v.
                                  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],fr,en". }
                                }
                                GROUP BY ?v ?vLabel
                                HAVING (?c > 8 )
                                ORDER BY DESC (?c)""",
                       "filtres": [{"filtre": getItemListSansMinus, "key": "__TYPELIST__"}],
                           "urlquery": ""},
    "__NBPAGESWIKIPEDIA__": {"sparql": """select ?wiki # (count(?wiki) as ?c) 
                                    where { ?s wdt:P170 wd:__QID__ . ?wiki schema:about ?s }""",
                             "filtres": [{"filtre": getLen, "key": "__NBPAGESWIKIPEDIA__"}],
                             "urlquery": "__QUERYNBPAGESWIKIPEDIA__"},
    "__NBPAGESPARLANGUE__": {"sparql": """SELECT ?lang (count(?wiki) as ?c) 
                                WHERE {
                                  ?s wdt:P170 wd:__QID__ .
                                  ?wiki schema:about ?s.
                                  filter(contains(str(?wiki), "wikipedia.org"))
                                  bind(substr(str(?wiki), 9, 2) as ?lang)
                                }
                                group by ?lang
                                order by desc(?c)""",
                         "filtres": [
                             {"filtre": getCountFr, "key": "__NBPAGESFRANCO__"},
                             {"filtre": getCountEn, "key": "__NBPAGESANGLO__"}
                        ],
                        "urlquery": "__QUERYNBWIKIPEDIAPARLANGUE__"},
    "__NBOEUVRESAVECWIKIPEDIA__": {"sparql": """SELECT distinct ?s WHERE {
                                      ?s wdt:P170 wd:__QID__.
                                      ?wiki schema:about ?s.
                                      FILTER(CONTAINS(STR(?wiki), "wikipedia.org"))
                                    }
                                    """,
                                   "filtres": [{"filtre": getLen, "key": "__NBOEUVRESAVECWIKIPEDIA__"}],
                                   "urlquery": "__QUERYNBOEUVRESAVECWIKIPEDIA__"},
    "__NBIMAGES__": {"sparql": """SELECT distinct ?image WHERE {  ?s wdt:P170 wd:__QID__; (wdt:P7420| wdt:P18) ?image. }""",
                     "filtres": [
                         {"filtre": getLen, "key": "__NBIMAGES__"},
                         {"filtre": getUrlImage, "key": "__URLIMAGE__"}
                     ],
                     "urlquery": "__QUERYNBIMAGES__"},
    "__LIENSWIKIDATABARRES__": {"sparql": """#groupés par niveau de distance, la couleur dépendant de la distance
                                            #defaultView:BarChart
                                            PREFIX var_muntype: <http://www.wikidata.org/entity/Q15284>
                                            PREFIX var_area: <http://www.wikidata.org/entity/Q6308>
                                            SELECT ?year ?c WHERE {
                                              {
                                                SELECT DISTINCT ?p ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                                  ?s wdt:P170 wd:__QID__;
                                                    ?p ?v.
                                                  SERVICE wikibase:label { bd:serviceParam wikibase:language "%5BAUTO_LANGUAGE%5D,en". }
                                                  FILTER(?p != schema:description)
                                                  FILTER(CONTAINS(STR(?p), "direct"))
                                                }
                                                GROUP BY ?p ?v ?vLabel
                                                HAVING (?c > 8 )
                                              }
                                              FILTER((?p = wdt:P571)||(?p = wdt:P577))
                                              BIND(REPLACE(?vLabel, "-01-01T00:00:00Z", "") AS ?year)
                                            }
                                            ORDER BY (?year)
                                            """,
                                "filtres": [{"filtre": None, "key": "__QUERYLIENSWIKIDATABARRES__"}],
                                "urlquery": "__QUERYDONNEESPOURBARRES__",
                                }
}

titreTemplate = """__NOMCREATEUR__ dans Wikidata"""

imageTemplate = """<!-- wp:image {"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="__URLIMAGE__" alt="" /></figure>
<!-- /wp:image -->
"""

introTemplate = """<!-- wp:paragraph -->
<p><em>Note: les chiffres de ce billet correspondent à la situation du __DATE__</em></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Je vais faire dans ce billet une analyse de la présence des œuvres de __LINKCREATEUR__ dans Wikidata et de leur description.</p>
<p>Cette analyse s'appuie sur des requêtes sparql qui permettent d'interroger les données de Wikidata. Un lien est fourni pour exécuter la requête dans WDQS, l'outil d'interrogation SPARQL de Wikidata</p>
<!-- /wp:paragraph -->

"""

nombreOeuvresTemplate = """<!-- wp:paragraph -->
<p>Il y a <strong>__NBOEUVRES__ œuvres de __LINKCREATEUR__</strong> dans Wikidata.</p>
<!-- /wp:paragraph -->

"""

queryNbOeuvresTemplate = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBOEUVRES__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

nbTypesOeuvresTemplate = """<!-- wp:paragraph -->
<p>Il s'agit de <strong>__NBMAINTYPE__</strong>, __NBOTHERTYPES__.</p>
<!-- /wp:paragraph -->

"""

queryNbParTypesTemplate = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBPARTYPES__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

nbPropTemplate = """<!-- wp:paragraph -->
<p>Pour décrire ces œuvres, <strong>__NBPPROP__ propriétés</strong> sont utilisées.</p>
<!-- /wp:paragraph -->

"""

queryNbproprietesTemplate = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBPROPRIETES__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

importantesPropTemplate = """<!-- wp:paragraph -->
<p><strong>__NBPROP50PLUS__ propriétés</strong> sont utilisées sur plus de la <strong>moitié des œuvres</strong>.</p>
<!-- /wp:paragraph -->

"""

queryImportantesPropTemplate = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBPROP50PLUS__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

propvalTemplate = """<!-- wp:paragraph -->
<p>Il y a <strong>__NBPAIRESPROPVAL8__ paires (propriété, valeur)</strong> différentes utilisées sur au moins huit de ces œuvres.</p>
<!-- /wp:paragraph -->

"""

queryPropValTemplate = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYPAIRESPROPVAL8__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

propDePropvalTemplate = """<!-- wp:paragraph -->
<p>Cela concerne <strong>__NBPROPPROPVAL8__ propriétés</strong>.</p>
<!-- /wp:paragraph -->

"""

queryPropDePropValTemplate = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYPROPPROPVAL8__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

tableTemplate = """<!-- wp:paragraph -->
<p>Ce qui s'illustre dans la table:</p>
<!-- /wp:paragraph -->

<!-- wp:table {"hasFixedLayout":false} -->
<figure class="wp-block-table"><table><tbody><tr><td width="100px"><strong>Propriété Wikidata</strong></td><td width="150px"><strong>Label</strong></td><td><strong>Valeurs (nombre d'instances)</strong></td></tr>__TABLEPROPVAL8__</tbody></table><figcaption class="wp-element-caption"><strong>Table: Des paires (propriété, valeur) les plus utilisées.</strong></figcaption></figure>
<!-- /wp:table -->

"""

queryTableTemplate = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYPROPPROPVAL8__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

mermaidTemplate = """<!-- wp:wp-mermaid/block -->
<div class="wp-block-wp-mermaid-block mermaid">
mindmap
  root((__NOMCREATEUR__))
    Genre
__GENRELIST__    
    Illustre
__DEPICTLIST__
    Types
__TYPELIST__
</div>
<!-- /wp:wp-mermaid/block -->

"""

barresTemplate = """<!-- wp:paragraph -->
<p>On peut accéder à une représentation graphique de la répartition par année des œuvres présentes sur Wikidata <a href="__QUERYLIENSWIKIDATABARRES__">ici</a> (remarque: si certaines années ne sont pas dans le graphe, c'est qu'il n'y a pas d'œuvres présentes dans Wikidata pour ces années).</p>
<!-- /wp:paragraph -->

"""

queryDonneesPourBarres = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYDONNEESPOURBARRES__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

nbPagesWikipedia = """<!-- wp:paragraph -->
<p><strong>__NBPAGESWIKIPEDIA__ pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>
<!-- /wp:paragraph -->

"""

queryNbPagesWikipedia = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBPAGESWIKIPEDIA__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

wikipediaParPays = """<!-- wp:paragraph -->
<p>Dont __NBPAGESANGLO__ dans le Wikipedia anglophone et __NBPAGESFRANCO__ dans le Wikidata francophone.</p>
<!-- /wp:paragraph -->

"""

queryWikipediaParLangue = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBWIKIPEDIAPARLANGUE__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

oeuvresWikipediaTemplate = """<!-- wp:paragraph -->
<p>L'ensemble des <strong>pages</strong> concerne <strong>__NBOEUVRESAVECWIKIPEDIA__ œuvres</strong>.</p>
<!-- /wp:paragraph -->

"""

queryOeuvreWikipediaTemplate = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBOEUVRESAVECWIKIPEDIA__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

"""

imagesTemplate = """<!-- wp:paragraph -->
<p>Il y a <strong>__NBIMAGES__ images</strong> dans Wikimedia Commons associées à ces œuvres.</p>
<!-- /wp:paragraph -->

"""

queryImagesTemplate = """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBIMAGES__">sur WDQS</a>)<br></p>
<!-- /wp:paragraph -->

"""

finTemplate = """<!-- wp:paragraph -->
<br>J'ai ainsi donné un aperçu de la visibilité des œuvres de __LINKCREATEUR__ dans Wikidata et des propriétés qui les décrivent. Je vais maintenant voir si des œuvres sont présentes dans <a href="https://datamusee.wp.imt.fr/fr/2023/12/04/le-jeu-de-donnees-joconde-et-le-lod/">SemJoconde</a> et absentes de Wikidata pour compléter Wikidata si nécessaire ou si des compléments d'informations sur les œuvres peuvent être obtenus avec <a href="https://datamusee.wp.imt.fr/fr/2023/12/04/le-jeu-de-donnees-joconde-et-le-lod/">SemJoconde</a>.
<!-- /wp:paragraph -->
"""

pageTemplate = imageTemplate + \
               introTemplate + nombreOeuvresTemplate + \
               queryNbOeuvresTemplate + \
               nbTypesOeuvresTemplate + queryNbParTypesTemplate + \
               nbPropTemplate + queryNbproprietesTemplate + \
               importantesPropTemplate + queryImportantesPropTemplate + \
               propvalTemplate + queryPropValTemplate + \
               propDePropvalTemplate + queryPropDePropValTemplate + \
               tableTemplate + queryTableTemplate + \
               mermaidTemplate + \
               barresTemplate + queryDonneesPourBarres + \
               nbPagesWikipedia + queryNbPagesWikipedia + \
               wikipediaParPays + queryWikipediaParLangue + \
               oeuvresWikipediaTemplate + queryOeuvreWikipediaTemplate + \
               imagesTemplate + queryImagesTemplate + \
               finTemplate

# pageTemplate = mermaidTemplate

pass

endpoint = "https://query.wikidata.org/sparql"


def getWordPressPage(qid):
    page = pageTemplate
    for name, elmt in sparqlList.items():
        filtres = elmt["filtres"]
        urlqueryref = elmt["urlquery"]
        sparqlquery = elmt["sparql"].replace("__QID__", qid) if elmt["sparql"] else None
        if sparqlquery:
            res = sparqlQuery(endpoint, sparqlquery)
            wdqsquery = getWDQSQuery(sparqlquery)
            embedquery = getWikidataBarGraph(sparqlquery, qid)
        else:
            res = None
            wdqsquery = None
            embedquery = None
        for filtrage in filtres:
            if filtrage["filtre"]:
                output = filtrage["filtre"](res, qid)
                page = page.replace(filtrage["key"], str(output))
            else:
                page = page.replace(filtrage["key"], embedquery) # hack
        if wdqsquery and urlqueryref:
            page = page.replace(urlqueryref, wdqsquery)
        time.sleep(0.2)
    return page


# page = getWordPressPage("Q37693") # fait à la main Gauguin
#page = getWordPressPage("Q5580")  # Dürer planifié le 18/1/2024 vers 16h
#page = getWordPressPage("Q5582") # Van Gogh planifié le 19/1/2024 vers 16h
#page = getWordPressPage("Q468453")  # Lurçat
#page = getWordPressPage("Q26408")  # Bonnard planifié le 22/1/2024 vers 23h
#page = getWordPressPage("Q83155")  # David planifié le 23/1/2024 vers 23h
#page = getWordPressPage("Q1470")  # Escher planifié le 24/1/2024 vers 23h
#page = getWordPressPage("Q47551")  # Le Titien planifié le 25/1/2024 vers 23h
#page = getWordPressPage("Q159758")  # Turner planifié le 26/1/2024 vers 23h
# qid = "Q241732" # Rosa Bonheur  planifié le 27/1/2024 vers 23h
# qid = "Q22334076" # Marianne van der Heijden non planifiée
#qid = "Q11787765" # Mária Medvecká
#qid = "Q3348980" # Nandalal Bose planifié le 27/1/2024 vers 14h
#qid = "Q187506" # Honoré Daumier

def nettoyageContenu(page):
    if "<p><strong>0 pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>" in page:
        page = page.replace(
            "<p><strong>0 pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>",
            "Je n'ai trouvé aucune page dans Wikipedia associée à ces œuvres")
        page = page.replace("<p>Dont 0 dans le Wikipedia anglophone et 0 dans le Wikidata francophone.</p>",
                     "Et bien sûr, il n'y a de page pour ces œuvres ni dans le Wikipedia francophone, ni dans l'anglophone")
        page = page.replace("<p>L'ensemble des <strong>pages</strong> concerne <strong>0 œuvres</strong>.</p>",
                     "Et aussi, aucune de ces œuvres n'est concernée par une page de Wikipedia.")
    if "<p>Il y a <strong>0 images</strong> dans Wikimedia Commons associées à ces œuvres.</p>" in page:
        page = page.replace("<p>Il y a <strong>0 images</strong> dans Wikimedia Commons associées à ces œuvres.</p>",
                     "Il n'a aucune image dans Wikimedia Commons associée à ces œuvres.")
        pass
    return page

# ne traiter que ceux qui sont dans filterpainters en supprimant la page si elle existe déjà
filterPainters = [
"Q10378200",
"Q1074290",
"Q1389068",
"Q151679",
"Q153793",
"Q153920",
"Q154349",
"Q155057",
"Q159758",
"Q170071",
"Q186202",
"Q187506",
"Q1948973",
"Q239394",
"Q2614892",
"Q26408",
"Q289441",
"Q316307",
"Q35548",
"Q40599",
"Q435316",
"Q460124",
"Q46373",
"Q518406",
"Q531234",
"Q5432",
"Q544899",
"Q5577",
"Q5580",
"Q5582",
"Q5589",
"Q5593",
"Q560115",
"Q562540",
"Q93284",
"Q979534",
    "Q274901"
]
filelist = os.listdir("./pages")
for qid in filterPainters:
    if "{qid}.wp".format(qid=qid) in filelist:
        os.remove("pages/{qid}.wp".format(qid=qid))

#page = "test"
with open("data/wikidataSignificantPaintersTicket1527.json") as fListPainters:
    # temporaire painters = json.load(fListPainters)
    painters = [{"painter":"http://www.wikidata.org/entity/Q274901","painterLabel":"Carolus-Duran","c":"52"}    ]
    for p in painters:
        print(p["painter"], " ", p["painterLabel"])
        try:
            qid = p["painter"].replace("http://www.wikidata.org/entity/", "")
            if not qid in filterPainters:
                continue
            filename = "pages/{qid}.wp".format(qid=str(qid))
            with open(filename, "x", encoding="utf-8") as fpage:
                page = getWordPressPage(qid)
                page = nettoyageContenu(page)
                fpage.write(page)
                time.sleep(3)
        except: # file already exist or other error
            print("possibly a file already exists for ", qid)
        pass
""" voir ticket 1527 pour un peu mieux
requête pour identifier des artistes candidats

select ?s (count(?oeuvre) as ?c) 
where 
{
  ?s wdt:P106 wd:Q1028181 .
  ?oeuvre wdt:P170 ?s
}
group by ?s
order by desc(?c)
#having(?c>500)
"""
"""
faire des billets sur la présence des mouvements picturaux dans Wikidata
"""
