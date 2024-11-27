class WPTemplate():
    dataConfig = {
        "__DATE__": {"sparql": None,
                     "filtres": [{"filtre": "getCurrentDate", "key": "__DATE__"}],
                     "urlquery": None},
        "__PROCESSPARAMS__": {"sparql": None,
                              "filtres": [{"filtre": "getQid", "key": "__PROCESSPARAMS__"}],
                              "urlquery": None},
        "__ENTITYNAME__": {
            "sparql": """select distinct ?qid ?qidLabel where { values ?qid { <http://www.wikidata.org/entity/__QID__> }  
                        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],__LANG__,en". } }
                        """,
            "filtres": [{"filtre": "getName", "key": "__ENTITYNAME__"},
                        {"filtre": "getLink", "key": "__ENTITYLINK__"}],
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
            "filtres": [{"filtre": "getExternalLinks", "key": "__EXTERNALLINKSTABLE__"}],
            "urlquery": None},
    }

    def __init__(self, lang="fr"):
        self.lang = lang
        self.dataConfig = WPTemplate.dataConfig

    def getDataConfig(self):
        return self.dataConfig

    def wpWrapPara(self, str):
        return """
        <!-- wp:paragraph -->
        """ + str + """
        <!-- /wp:paragraph -->
        
        """

    def wpWrapImage(self, str):
        return """
        <!-- wp:image -->
        """ + str + """
        <!-- /wp:image -->"""

    def buildQueryView(self, varstring="", lang="fr"):
        models = {
            "fr": """<p>(obtenu avec la requête sparql accessible <a href='""" + varstring + """'>sur WDQS</a>)</p>""",
        }
        return self.wpWrapPara(models.get(lang, models[lang]))

    def buildNbTypesOeuvresView(self, varnbmain="__NBMAINTYPE__", varnbother="__NBOTHERTYPES__", lang="fr"):
        models = {
            "fr": """<p>Il s'agit de <strong>+""" + varnbmain + """</strong>, """ + varnbother + """.</p>""",
        }
        return self.wpWrapPara(models.get(lang, models[lang]))

    def buildNbPropView(self, varnb="__NBPPROP__", lang="fr"):
        models = {
            "fr": """<p>Pour décrire ces œuvres, <strong>""" + varnb + """ propriétés</strong> sont utilisées.</p>""",
        }
        return self.wpWrapPara(models.get(lang, models[lang]))

    def buildImportantesPropView(self, lang="fr"):
        models = {
            "fr": """<p><strong>__NBPROP50PLUS__ propriétés</strong> sont utilisées sur plus de la <strong>moitié des œuvres</strong>.</p>""",
        }
        return self.wpWrapPara(models.get(lang, models[lang]))

    def buildPropDePropvalView(self, lang="fr"):
        models = {
            "fr": """<p>Cela concerne <strong>__NBPROPPROPVAL8__ propriétés</strong>.</p>""",
        }
        return self.wpWrapPara(models.get(lang, models[lang]))

    def buildTableView(self, lang="fr"):
        models = {
            "fr": """<p>Ce qui s'illustre dans la table:</p>""" + """

            <!-- wp:table -->
            <figure class="wp-block-table"><table><tbody><tr><td><strong>Propriété Wikidata</strong></td><td><strong>Label</strong></td><td><strong>Valeurs (nombre d'instances)</strong></td></tr>__TABLEPROPVAL8__</tbody></table><figcaption class="wp-element-caption"><strong>Table: Les paires (propriété, valeur) les plus utilisées.</strong></figcaption></figure>
            <!-- /wp:table -->

        """,
        }
        return models.get(lang, models[lang])

    def buildMermaidView(self, lang="fr"):
        models = {
            "fr": """<!-- wp:wp-mermaid/block -->
<div class="wp-block-wp-mermaid-block mermaid">
mindmap
  root((__ENTITYNAME__))
__GENRELIST__    
__DEPICTLIST__
__TYPELIST__
</div>
<!-- /wp:wp-mermaid/block -->

        """,
        }
        return models.get(lang, models[lang])

    def buildBarresView(self, lang="fr"):
        models = {
            "fr": """<p>On peut accéder à une représentation graphique de la répartition par année des œuvres présentes sur Wikidata <a href="__QUERYLIENSWIKIDATABARRES__">ici</a> (remarque: si certaines années ne sont pas dans le graphe, c'est qu'il n'y a pas d'œuvres présentes dans Wikidata pour ces années).</p>""",
        }
        return self.wpWrapPara(models.get(lang, models[lang]))

    def buildNbPagesWikipediaView(self, lang="fr"):
        models = {
            "fr": """<p><strong>__NBPAGESWIKIPEDIA__ pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>""",
        }
        return self.wpWrapPara(models.get(lang, models[lang]))

    def buildWikipediaParPaysView(self, lang="fr"):
        models = {
            "fr": """<p>Dont __NBPAGESANGLO__ dans le Wikipedia anglophone et __NBPAGESFRANCO__ dans le Wikidata francophone.</p>""",
        }
        return self.wpWrapPara(models.get(lang, models[lang]))

    def buildOeuvresWikipediaView(self, lang="fr"):
        models = {
            "fr": """<p>L'ensemble des <strong>pages</strong> concerne <strong>__NBOEUVRESAVECWIKIPEDIA__ œuvres</strong>.</p>""",
        }
        return self.wpWrapPara(models.get(lang, models[lang]))

    def buildImagesView(self, lang="fr"):
        models = {
            "fr": """<p>Il y a <strong>__NBIMAGES__ images</strong> dans Wikimedia Commons associées à ces œuvres.</p>"""
        }
        return self.wpWrapPara(models.get(lang, models[lang]))

    def buildScrutartLink(self, title, lang="fr"):
        # ici chercher l'url d'une page avec ce titre
        # si la page n'existe pas, la créer et récupérer l'url
        link = self.wpWrapPara(
            """<a href="">""" + title + """</a>""")
        return link

    def buildTitre(self, varstring="__ENTITYNAME__"):
        return """Titre temporaire"""

    def buildJsonProcessBlock(self, varcrea="__PROCESSPARAMS__"):
        commentProcess = """
        <!-- wp:html -->
        <!-- processParams = { "qid": \""""+varcrea+"""\", "templateVersion": \""""+self.version+"""\" } -->
        <!-- /wp:html -->        
        """
        return commentProcess

    def buildJsonLdScript(self, varstring="__ENTITYNAME__"):
        scriptBlock = """
        <!-- wp:html -->
        <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "Person",
              "name":\""""+ varstring +"""\",
            }
            </script>
        <!-- /wp:html -->
        """
        return scriptBlock

    def buildExternalLinks(self, varstring="__EXTERNALLINKSTABLE__"):
        linksBlock = """
        <!-- wp:table {"style":{"border":{"width":"0px","style":"none"}}} -->
        <p>Liens externes:</p>
        <figure class="wp-block-table">
        <table class="has-fixed-layout" style="border-style:none;border-width:0px">
        <tbody>
        <tr>
        """+varstring+"""</tr>
        </tbody>
        </table>
        </figure>
        <!-- /wp:table -->
        """
        return linksBlock

    def buildImageView(self):
        return self.wpWrapImage(
            """<figure class="wp-block-image size-large"><img src="__URLIMAGE__" alt="" /></figure>""")

    def buildIntroView(self, insert=""):
        intro = self.wpWrapPara(
            """<p><em>Note: les chiffres de ce billet correspondent à la situation du __DATE__</em></p>""") + """
        
        """ + self.wpWrapPara(insert+"""<p>Cette analyse s'appuie sur des requêtes sparql qui permettent d'interroger les données de Wikidata. Un lien est fourni pour exécuter la requête dans WDQS, l'outil d'interrogation SPARQL de Wikidata</p>
        """)
        return intro

    def buildNombreOeuvresView(self, varnb="__NBOEUVRES__", varcrea="__ENTITYLINK__"):
        return self.wpWrapPara(
            """<p>Il y a <strong>""" + varnb + """ œuvres de """ + varcrea + """</strong> dans Wikidata.</p>""")

    def buildQueryView(self, varstring=""):
        return self.wpWrapPara(
            """<p>(obtenu avec la requête sparql accessible <a href='""" + varstring + """'>sur WDQS</a>)</p>""")

    def buildQueryNbOeuvresView(self):
        return self.buildQueryView("__QUERYNBOEUVRES__")

    def buildNbTypesOeuvresView(self, varnbmain="__NBMAINTYPE__", varnbother="__NBOTHERTYPES__"):
        return self.wpWrapPara(
            """<p>Il s'agit de <strong>+""" + varnbmain + """</strong>, """ + varnbother + """.</p>""")

    def buildQueryNbParTypesView(self):
        return self.buildQueryView("__QUERYNBPARTYPES__")

    def buildNbPropView(self, varnb="__NBPPROP__"):
        return self.wpWrapPara(
            """<p>Pour décrire ces œuvres, <strong>""" + varnb + """ propriétés</strong> sont utilisées.</p>""")

    def buildQueryNbproprietesView(self):
        return self.buildQueryView("__QUERYNBPROPRIETES__")

    def buildImportantesPropView(self):
        return self.wpWrapPara(
            """<p><strong>__NBPROP50PLUS__ propriétés</strong> sont utilisées sur plus de la <strong>moitié des œuvres</strong>.</p>""")

    def buildQueryImportantesPropView(self):
        return self.buildQueryView("__QUERYNBPROP50PLUS__")

    def buildPropvalView(self):
        return self.wpWrapPara(
            """<p>Il y a <strong>__NBPAIRESPROPVAL8__ paires (propriété, valeur)</strong> différentes utilisées sur au moins huit de ces œuvres.</p>""")

    def buildQueryPropValView(self):
        return self.buildQueryView("__QUERYPAIRESPROPVAL8__")

    def buildPropDePropvalView(self):
        return self.wpWrapPara("""<p>Cela concerne <strong>__NBPROPPROPVAL8__ propriétés</strong>.</p>""")

    def buildQueryPropDePropValView(self):
        return self.buildQueryView("__QUERYPROPPROPVAL8__")

    def buildTableView(self): return self.wpWrapPara("""<p>Ce qui s'illustre dans la table:</p>""") + """
    
        <!-- wp:table -->
        <figure class="wp-block-table"><table><tbody><tr><th style="width:15%"><strong>Propriété Wikidata</strong></th><th style="width:20%"><strong>Label</strong></th><th style="width:60%"><strong>Valeurs (nombre d'instances)</strong></th></tr>__TABLEPROPVAL8__</tbody></table><figcaption class="wp-element-caption"><strong>Table: Les 5 paires (propriété, valeur) les plus utilisées.</strong></figcaption></figure>
        <!-- /wp:table -->
    
        """

    def buildQueryTableView(self):
        return self.buildQueryView("__QUERYPROPPROPVAL8__")

    def buildMermaidView(self):
        return """<!-- wp:wp-mermaid/block -->
<div class="wp-block-wp-mermaid-block mermaid">
mindmap
  root((__ENTITYNAME__))
__GENRELIST__    
__DEPICTLIST__
__TYPELIST__
</div>
<!-- /wp:wp-mermaid/block -->
    
        """

    def buildBarresView(self):
        return self.wpWrapPara(
            """<p>On peut accéder à une représentation graphique de la répartition par année des œuvres présentes sur Wikidata <a href="__QUERYLIENSWIKIDATABARRES__">ici</a> (remarque: si certaines années ne sont pas dans le graphe, c'est qu'il n'y a pas d'œuvres présentes dans Wikidata pour ces années).</p>""")

    def buildQueryDonneesPourBarresView(self):
        return self.buildQueryView("__QUERYDONNEESPOURBARRES__")

    def buildNbPagesWikipediaView(self): return self.wpWrapPara(
        """<p><strong>__NBPAGESWIKIPEDIA__ pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>""")

    def buildQueryNbPagesWikipediaView(self):
        return self.buildQueryView("__QUERYNBPAGESWIKIPEDIA__")

    def buildWikipediaParPaysView(self):
        return self.wpWrapPara(
            """<p>Dont __NBPAGESANGLO__ dans le Wikipedia anglophone et __NBPAGESFRANCO__ dans le Wikidata francophone.</p>""")

    def buildQueryWikipediaParLangueView(self):
        return self.buildQueryView("__QUERYNBWIKIPEDIAPARLANGUE__")

    def buildOeuvresWikipediaView(self):
        return self.wpWrapPara(
            """<p>L'ensemble des <strong>pages</strong> concerne <strong>__NBOEUVRESAVECWIKIPEDIA__ œuvres</strong>.</p>""")

    def buildQueryOeuvreWikipediaView(self):
        return self.buildQueryView("__QUERYNBOEUVRESAVECWIKIPEDIA__")

    def buildImagesView(self):
        return self.wpWrapPara(
            """<p>Il y a <strong>__NBIMAGES__ images</strong> dans Wikimedia Commons associées à ces œuvres.</p>""")

    def buildQueryImagesView(self):
        return self.buildQueryView("__QUERYNBIMAGES__")

    def buildFinView(self): return self.wpWrapPara(
        """<br>J'ai ainsi donné un aperçu de la visibilité des œuvres de __ENTITYLINK__ dans Wikidata et des propriétés qui les décrivent. Je vais maintenant voir si des œuvres sont présentes dans <a href="https://datamusee.wp.imt.fr/fr/2023/12/04/le-jeu-de-donnees-joconde-et-le-lod/">SemJoconde</a> et absentes de Wikidata pour compléter Wikidata si nécessaire ou si des compléments d'informations sur les œuvres peuvent être obtenus avec <a href="https://datamusee.wp.imt.fr/fr/2023/12/04/le-jeu-de-donnees-joconde-et-le-lod/">SemJoconde</a>.""")

    def buildScrutartLink(self, title):
        # ici chercher l'url d'une page avec ce titre
        # si la page n'existe pas, la créer et récupérer l'url
        link = self.wpWrapPara(
            """<a href="">"""+title+"""</a>""")
        return link

    def buildPageTemplate(self):
        pageTemplate = self.buildJsonProcessBlock() +\
                       self.buildJsonLdScript() +\
                       self.buildImageView() + \
                       self.buildExternalLinks() +\
                       self.buildIntroView() + \
                       self.buildNombreOeuvresView() + \
                       self.buildQueryNbOeuvresView() + \
                       self.buildNbTypesOeuvresView() + self.buildQueryNbParTypesView() + \
                       self.buildNbPropView() + self.buildQueryNbproprietesView() + \
                       self.buildImportantesPropView() + self.buildQueryImportantesPropView() + \
                       self.buildPropvalView() + self.buildQueryPropValView() + \
                       self.buildPropDePropvalView() + self.buildQueryPropDePropValView() + \
                       self.buildTableView() + self.buildQueryTableView() + \
                       self.buildMermaidView() + \
                       self.buildBarresView() + self.buildQueryDonneesPourBarresView() + \
                       self.buildNbPagesWikipediaView() + self.buildQueryNbPagesWikipediaView() + \
                       self.buildWikipediaParPaysView() + self.buildQueryWikipediaParLangueView() + \
                       self.buildOeuvresWikipediaView() + self.buildQueryOeuvreWikipediaView() + \
                       self.buildImagesView() + self.buildQueryImagesView() + \
                       self.buildFinView()
        return pageTemplate
