# ce template est une ébauche multilingue avec l'hypothèse qu'au moins le français est défini pour chaque texte
# ce qui fait qu'un texte non défini das une langue apparaitra en français
from WPTemplateManager import WPTemplate

class WPGenreTemplate(WPTemplate):
    dataConfig = {
        # "__TITRE_TEMPLATE__":
        #    [ { "version": "1.0.2", "template": "Où trouver __ENTITYNAME__ dans Wikidata, suivez le guide"} ],
        "__NBENTITIES__": {"sparql": "select (count(?s) as ?c) where { ?s wdt:P136 wd:__QID__ }",
                          "filtres": [{"filtre": "getInt", "key": "__NBENTITIES__"}],
                          "urlquery": "__QUERYNBOEUVRES__"},
        "__NBTYPES__": {"sparql": """select ?type ?typeLabel (count(?s) as ?c) where {
                              ?s wdt:P136 wd:__QID__; wdt:P31 ?type
                                SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],__LANG__,en". }
                                } group by ?type ?typeLabel
                                order by desc(?c)""",
                        "filtres": [
                            {"filtre": "getMainType", "key": "__NBMAINTYPE__"},
                            {"filtre": "getOtherTypes", "key": "__NBOTHERTYPES__"},
                        ],
                        "urlquery": "__QUERYNBPARTYPES__"},
        "__NBPPROP__": {"sparql": "select (count(distinct ?p) as ?c) where { ?s wdt:P136 wd:__QID__; ?p [] }",
                        "filtres": [{"filtre": "getInt", "key": "__NBPPROP__"}],
                        "urlquery": "__QUERYNBPROPRIETES__"},
        "__NBPROP50PLUS__": {"sparql": """select (count(?p) as ?c)
                                        where {
                                          {
                                            select  (count(distinct ?s) as ?nboeuvres) where { ?s wdt:P136 wd:__QID__ } 
                                          }
                                            {
                                            select ?p (count(distinct ?s) as ?oeuvresparprop) 
                                                   where { ?s wdt:P136 wd:__QID__; ?p [] } 
                                            group by ?p 
                                          }
                                          filter(!contains(str(?p), "schema:"))
                                          filter(!contains(str(?p), "wikiba.se:"))
                                          filter(contains(str(?p), "direct"))
                                            bind ( (xsd:float(?nboeuvres)/2.0) as ?demi)
                                          filter(?oeuvresparprop>?demi)
                                        }
                                        """,
                             "filtres": [{"filtre": "getInt", "key": "__NBPROP50PLUS__"}],
                             "urlquery": "__QUERYNBPROP50PLUS__"},
        "__NBPAIRESPROPVAL8__": {"sparql": """select distinct ?p ?v (count(distinct ?s) as ?c) where { ?s wdt:P136 wd:__QID__;
                                                 ?p ?v 
                                                 filter(?p!=schema:description)           
                                            } group by ?p ?v
                                            HAVING (?c>550)""",
                                 "filtres": [{"filtre": "getLen", "key": "__NBPAIRESPROPVAL8__"}],
                                 "urlquery": "__QUERYPAIRESPROPVAL8__"},
        "__NBPROPPROPVAL8__": {"sparql": """SELECT DISTINCT ?p ?propLabel WHERE {
                                              {
                                                SELECT DISTINCT ?p ?v (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                                  ?s wdt:P136 wd:__QID__;
                                                    ?p ?v.
                                                  FILTER(?p != schema:description)
                                                }
                                                GROUP BY ?p ?v
                                                HAVING (?c > 1000 )
                                              }
                                              SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
                                              ?prop wikibase:directClaim ?p.
                                            }""",
                               "filtres": [
                                   {"filtre": "getLen", "key": "__NBPROPPROPVAL8__"},
                                   {"filtre": "getTable", "key": "__TABLEPROPVAL8__"}
                               ],
                               "urlquery": "__QUERYPROPPROPVAL8__"},
        "__GENRELIST__": {"sparql": """SELECT DISTINCT ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                      ?s wdt:P136 wd:__QID__;
                                        wdt:P136 ?v.
                                      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],__LANG__,en". }
                                    }
                                    GROUP BY ?v ?vLabel
                                    HAVING (?c > 1000 )
                                    ORDER BY DESC (?c)""",
                          "filtres": [{"filtre": "getGenreList", "key": "__GENRELIST__"}],
                          "urlquery": ""},
        "__DEPICTLIST__": {"sparql": """SELECT DISTINCT ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                      ?s wdt:P136 wd:__QID__;
                                        wdt:P180 ?v.
                                      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],__LANG__,en". }
                                    }
                                    GROUP BY ?v ?vLabel
                                    HAVING (?c > 1000 )
                                    ORDER BY DESC (?c)""",
                           "filtres": [{"filtre": "getDepictList", "key": "__DEPICTLIST__"}],
                           "urlquery": ""},
        "__TYPELIST__": {"sparql": """SELECT DISTINCT ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                      ?s wdt:P136 wd:__QID__;
                                        wdt:P31 ?v.
                                      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],__LANG__,en". }
                                    }
                                    GROUP BY ?v ?vLabel
                                    HAVING (?c > 1000 )
                                    ORDER BY DESC (?c)""",
                         "filtres": [{"filtre": "getTypeList", "key": "__TYPELIST__"}],
                         "urlquery": ""},
        "__NBPAGESWIKIPEDIA__": {"sparql": """select ?wiki # (count(?wiki) as ?c) 
                                        where { ?s wdt:P136 wd:__QID__ . ?wiki schema:about ?s }""",
                                 "filtres": [{"filtre": "getLen", "key": "__NBPAGESWIKIPEDIA__"}],
                                 "urlquery": "__QUERYNBPAGESWIKIPEDIA__"},
        "__NBPAGESPARLANGUE__": {"sparql": """SELECT ?lang (count(?wiki) as ?c) 
                                    WHERE {
                                      ?s wdt:P136 wd:__QID__ .
                                      ?wiki schema:about ?s.
                                      filter(contains(str(?wiki), "wikipedia.org"))
                                      bind(substr(str(?wiki), 9, 2) as ?lang)
                                    }
                                    group by ?lang
                                    order by desc(?c)""",
                                 "filtres": [
                                     {"filtre": "getCountFr", "key": "__NBPAGESFRANCO__"},
                                     {"filtre": "getCountEn", "key": "__NBPAGESANGLO__"}
                                 ],
                                 "urlquery": "__QUERYNBWIKIPEDIAPARLANGUE__"},
        "__NBOEUVRESAVECWIKIPEDIA__": {"sparql": """SELECT distinct ?s WHERE {
                                          ?s wdt:P31 wd:Q3305213 .
                                          ?s wdt:P136 wd:__QID__.
                                          ?wiki schema:about ?s.
                                          FILTER(CONTAINS(STR(?wiki), "wikipedia.org"))
                                        }
                                        """,
                                       "filtres": [{"filtre": "getLen", "key": "__NBOEUVRESAVECWIKIPEDIA__"}],
                                       "urlquery": "__QUERYNBOEUVRESAVECWIKIPEDIA__"},
        "__NBIMAGES__": {
            "sparql": """SELECT distinct ?image WHERE {  ?s wdt:P136 wd:__QID__; (wdt:P7420| wdt:P18) ?image. }""",
            "filtres": [
                {"filtre": "getLen", "key": "__NBIMAGES__"},
                {"filtre": "getUrlImage", "key": "__URLIMAGE__"}
            ],
            "urlquery": "__QUERYNBIMAGES__"},
        "__LIENSWIKIDATABARRES__": {"sparql": """#groupés par niveau de distance, la couleur dépendant de la distance
                                                #defaultView:BarChart
                                                PREFIX var_muntype: <http://www.wikidata.org/entity/Q15284>
                                                PREFIX var_area: <http://www.wikidata.org/entity/Q6308>
                                                SELECT ?year ?c WHERE {
                                                  {
                                                    SELECT DISTINCT ?p ?v ?vLabel (COUNT(DISTINCT ?s) AS ?c) WHERE {
                                                      ?s wdt:P136 wd:__QID__;
                                                        ?p ?v.
                                                      SERVICE wikibase:label { bd:serviceParam wikibase:language "%5BAUTO_LANGUAGE%5D,en". }
                                                      FILTER(?p != schema:description)
                                                      FILTER(CONTAINS(STR(?p), "direct"))
                                                    }
                                                    GROUP BY ?p ?v ?vLabel
                                                    HAVING (?c > 1000 )
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

    def __init__(self, lang="fr"):
        self.version = "1.0.3"
        super().__init__(lang)
        superDataConfig = super().dataConfig
        localDataConfig = WPGenreTemplate.dataConfig
        self.dataConfig = localDataConfig | superDataConfig # fusion
        pass

    def getDataConfig(self):
        return self.dataConfig

    def buildTitre(self, varstring="__ENTITYNAME__", lang="fr"):
        titleModels = {
            "es": """""",
            "en": """I look for the paintaings with genre '""" + varstring + """' in Wikidata : descriptive data analysis""",
            "fr": """Je scrute les peintures de '""" + varstring + """' dans Wikidata : analyse des données descriptives""",
        }
        titleTemplate = titleModels.get(lang, titleModels["fr"])
        return titleTemplate

    def buildIntroView(self, lang="fr"):
        introModels = {
            "fr": """<p>Je vais faire dans ce billet une analyse de la présence d'œuvres de la catégorie '__ENTITYLINK__' dans Wikidata et de leur description.</p>""",
        }
        intro = super().buildIntroView(introModels.get(lang, introModels["fr"]))
        return intro

    def buildNombreOeuvresView(self, varnb="__NBENTITIES__", varcrea="__ENTITYLINK__", lang="fr"):
        models = {
            "fr": """<p>Il y a <strong>""" + varnb + """ œuvres de catégorie '""" + varcrea + """'</strong> dans Wikidata.</p>""",
        }
        return self.wpWrapPara(models.get(lang, models["fr"]))

    def buildPropvalView(self, lang="fr"):
        models = {
            "fr": """<p>Il y a <strong>__NBPAIRESPROPVAL8__ paires (propriété, valeur)</strong> différentes le plus utilisées sur ces œuvres.</p>""",
        }
        return self.wpWrapPara(models.get(lang, models["fr"]))

    def buildFinView(self, lang="fr"):
        models = {
            "fr": """<p>J'ai ainsi donné un aperçu de la visibilité des œuvres de catégorie '__ENTITYLINK__' dans Wikidata et des propriétés qui les décrivent. Je vais maintenant voir si des œuvres sont présentes dans <a href="https://datamusee.wp.imt.fr/fr/2023/12/04/le-jeu-de-donnees-joconde-et-le-lod/">SemJoconde</a> et absentes de Wikidata pour compléter Wikidata si nécessaire ou si des compléments d'informations sur les œuvres peuvent être obtenus avec <a href="https://datamusee.wp.imt.fr/fr/2023/12/04/le-jeu-de-donnees-joconde-et-le-lod/">SemJoconde</a>.</p>""",
        }
        return self.wpWrapPara(models.get(lang, models["fr"]))

