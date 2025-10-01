from src.generationWordpress.WPTemplateManager import WPTemplate

dataConfig = {
    # "__TITRE_TEMPLATE__":
    #    [ { "version": "1.0.2", "template": "Où trouver __ENTITYNAME__ dans Wikidata, suivez le guide"} ],
    "__DATE__": {"sparql": None,
                 "filtres": [{"filtre": "get_current_date", "key": "__DATE__"}],
                 "urlquery": None},
    "__PROCESSPARAMS__": {"sparql": None,
                 "filtres": [{"filtre": "get_qid", "key": "__PROCESSPARAMS__"}],
                 "urlquery": None},
    "__EXTERNALLINKSTABLE__": {
        "sparql": """
            SELECT ?link ?baseUrl WHERE {
              values ?qid { <http://www.wikidata.org/entity/__QID__> }
              VALUES ?idprop {
                wdt:P214 wdt:P3219 wdt:P347 wdt:P213 wdt:P268
                wdt:P12212 wdt:P245 wdt:P8705 wdt:1711 wdt:4200
                wdt:3219 wdt:10297 wdt:2268 wdt:7444 wdt:1795
                wdt:1014
              }
              OPTIONAL {
                ?qid ?idprop ?lid.
                ?propentity wikibase:directClaim ?idprop;
                  wdt:P1630 ?baseUrl.
                BIND(IRI(REPLACE(?baseUrl, "[$]1", ?lid)) AS ?link)
              }
            }
        """,
        "filtres": [{"filtre": "get_external_links", "key": "__EXTERNALLINKSTABLE__"}],
        "urlquery": None},
    "__ENTITYNAME__": {
        "sparql": """select distinct ?qid ?qidLabel where { values ?qid { <http://www.wikidata.org/entity/__QID__> }  
                    SERVICE wikibase:label { bd:serviceParam wikibase:language "__LANG__,en". } }
                    """,
        "filtres": [{"filtre": "get_name", "key": "__ENTITYNAME__"},
                    {"filtre": "get_link", "key": "__ENTITYLINK__"}],
        "urlquery": None},
    # "__ENTITYLINK__": {
    #    "sparql": """select distinct ?qid ?qidLabel where { values ?qid { <http://www.wikidata.org/entity/__QID__> }
    #                SERVICE wikibase:label { bd:serviceParam wikibase:language "__LANG__,en". } }
    #                """,
    #    "filtres": [{"filtre": "getLink", "key": "__ENTITYLINK__"}],
    #    "urlquery": ""},
    "__NBOEUVRES__": {"sparql": "select (count(?s) as ?c) where { ?s wdt:P170 wd:__QID__ }",
                      "filtres": [{"filtre": "get_int", "key": "__NBOEUVRES__"}],
                      "urlquery": "__QUERYNBOEUVRES__"},
    "__NBTYPES__": {"sparql": """select ?type ?typeLabel (count(?s) as ?c) where {
                          ?s wdt:P170 wd:__QID__; wdt:P31 ?type
                            SERVICE wikibase:label { bd:serviceParam wikibase:language "__LANG__,en". }
                            } group by ?type ?typeLabel
                            order by desc(?c)""",
                    "filtres": [
                        {"filtre": "get_main_type", "key": "__NBMAINTYPE__"},
                        {"filtre": "get_other_types", "key": "__NBOTHERTYPES__"},
                    ],
                    "urlquery": "__QUERYNBPARTYPES__"},
    "__NBPPROP__": {"sparql": "select (count(distinct ?p) as ?c) where { ?s wdt:P170 wd:__QID__; ?p [] }",
                    "filtres": [{"filtre": "get_int", "key": "__NBPPROP__"}],
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
                         "filtres": [{"filtre": "get_int", "key": "__NBPROP50PLUS__"}],
                         "urlquery": "__QUERYNBPROP50PLUS__"},
    "__NBPAIRESPROPVAL8__": {"sparql": """select distinct ?p ?v (count(distinct ?s) as ?c) where { ?s wdt:P170 wd:__QID__;
                                             ?p ?v 
                                             filter(?p!=schema:description)           
                                        } group by ?p ?v
                                        HAVING (?c>8)""",
                             "filtres": [{"filtre": "get_len", "key": "__NBPAIRESPROPVAL8__"}],
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
                               {"filtre": "get_len", "key": "__NBPROPPROPVAL8__"},
                               {"filtre": "get_table", "key": "__TABLEPROPVAL8__"}
                           ],
                           "urlquery": "__QUERYPROPPROPVAL8__"},
    "__GENRELIST__": {"sparql": """SELECT DISTINCT ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                  ?s wdt:P170 wd:__QID__;
                                    wdt:P136 ?v.
                                  SERVICE wikibase:label { bd:serviceParam wikibase:language "__LANG__,en". }
                                }
                                GROUP BY ?v ?vLabel
                                HAVING (?c > 8 )
                                ORDER BY DESC (?c)""",
                      "filtres": [{"filtre": "get_genre_list", "key": "__GENRELIST__"}],
                      "urlquery": ""},
    "__DEPICTLIST__": {"sparql": """SELECT DISTINCT ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                  ?s wdt:P170 wd:__QID__;
                                    wdt:P180 ?v.
                                  SERVICE wikibase:label { bd:serviceParam wikibase:language "__LANG__,en". }
                                }
                                GROUP BY ?v ?vLabel
                                HAVING (?c > 8 )
                                ORDER BY DESC (?c)""",
                       "filtres": [{"filtre": "get_depict_list", "key": "__DEPICTLIST__"}],
                       "urlquery": ""},
    "__TYPELIST__": {"sparql": """SELECT DISTINCT ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                  ?s wdt:P170 wd:__QID__;
                                    wdt:P31 ?v.
                                  SERVICE wikibase:label { bd:serviceParam wikibase:language "__LANG__,en". }
                                }
                                GROUP BY ?v ?vLabel
                                HAVING (?c > 8 )
                                ORDER BY DESC (?c)""",
                     "filtres": [{"filtre": "get_type_list", "key": "__TYPELIST__"}],
                     "urlquery": ""},
    "__NBPAGESWIKIPEDIA__": {"sparql": """select ?wiki # (count(?wiki) as ?c) 
                                    where { ?s wdt:P170 wd:__QID__ . ?wiki schema:about ?s }""",
                             "filtres": [{"filtre": "get_len", "key": "__NBPAGESWIKIPEDIA__"}],
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
                                 {"filtre": "get_count_fr", "key": "__NBPAGESFRANCO__"},
                                 {"filtre": "get_count_en", "key": "__NBPAGESANGLO__"}
                             ],
                             "urlquery": "__QUERYNBWIKIPEDIAPARLANGUE__"},
    "__NBOEUVRESAVECWIKIPEDIA__": {"sparql": """SELECT distinct ?s WHERE {
                                      ?s wdt:P170 wd:__QID__.
                                      ?wiki schema:about ?s.
                                      FILTER(CONTAINS(STR(?wiki), "wikipedia.org"))
                                    }
                                    """,
                                   "filtres": [{"filtre": "get_len", "key": "__NBOEUVRESAVECWIKIPEDIA__"}],
                                   "urlquery": "__QUERYNBOEUVRESAVECWIKIPEDIA__"},
    "__NBIMAGES__": {
        "sparql": """SELECT distinct ?image WHERE {  ?s wdt:P170 wd:__QID__; (wdt:P7420| wdt:P18) ?image. }""",
        "filtres": [
            {"filtre": "get_len", "key": "__NBIMAGES__"},
            {"filtre": "get_url_image", "key": "__URLIMAGE__"},
            {"filtre": "get_table_boxes", "key": "__IMAGES_TABLE_BOXES__"},
            {"filtre": "get_gallery_link", "key": "__GALLERY_LINK__"}
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
                                "urlquery": "__QUERYDONNEESPOURBARRES__"

    }
}

class WPPainterTemplate(WPTemplate):
    def __init__(self, lang="fr"):
        super().__init__(lang)
        self.version = "1.0.2"
        self.dataConfig = dataConfig

    def buildIntroView(self):
        intro = {
            "fr": super().buildIntroView(insert="""<p><p>Je vais faire dans ce billet une analyse de la présence des œuvres de __ENTITYLINK__ dans Wikidata et de leur description.</p></p>"""),
            "en": super().buildIntroView(insert="""<p><p>In this post I'm going to analyze the presence of __ENTITYLINK__'s works in Wikidata and their description.</p></p>"""),
            "es": super().buildIntroView(
                insert="""<p><p>En este post voy a analizar la presencia de obras de __ENTITYLINK__ en Wikidata y su descripción.</p></p>"""),
        }
        return intro[self.lang]

    def buildTitre(self, varstring="__ENTITYNAME__", lang="fr"):
        title = {
            "fr": f"""Où trouver {varstring} dans Wikidata, suivez le guide""", # titre pour créateur
            "en": f"""Where to find {varstring} in Wikidata, follow the guide""", # titre pour créateur
            "es": """Dónde encontrar {varstring} en Wikidata, siga la guía""",
        }
        return title[lang]
