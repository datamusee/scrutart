class WPTemplate():
    dataConfig = {
        "__DATE__": {"sparql": None,
                     "filtres": [{"filtre": "get_current_date", "key": "__DATE__"}],
                     "urlquery": None},
        "__PROCESSPARAMS__": {"sparql": None,
                              "filtres": [{"filtre": "get_qid", "key": "__PROCESSPARAMS__"}],
                              "urlquery": None},
        "__ENTITYNAME__": {
            "sparql": """select distinct ?qid ?qidLabel where { values ?qid { <http://www.wikidata.org/entity/__QID__> }  
                        SERVICE wikibase:label { bd:serviceParam wikibase:language "__LANG__,en". } }
                        """,
            "filtres": [{"filtre": "get_name", "key": "__ENTITYNAME__"},
                        {"filtre": "get_link", "key": "__ENTITYLINK__"}],
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
    }

    def __init__(self, lang="fr"):
        self.lang = lang
        self.version = "1.5"
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

    def buildTableView(self):
        # TODO vérifier si wp:table peut être imbriqué dans le wp-para
        # au lieu de 15%, cela pourrait être 100px, puis 150px pour le deuxième colonne
        queryview = self.buildQueryTableView()
        models = {
            "fr": self.wpWrapPara(f"""<p>Ce qui s'illustre dans la table: {queryview}</p>""") + """

	        <!-- wp:table {"hasFixedLayout":false} -->
	        <figure class="wp-block-table"><table><tbody><tr><td width="100px"><strong>Propriété Wikidata</strong></td><td width="150px"><strong>Label</strong></td><td><strong>Valeurs (nombre d'instances)</strong></td></tr>__TABLEPROPVAL8__</tbody></table><figcaption class="wp-element-caption"><strong>Table: Les paires (propriété, valeur) les plus utilisées.</strong></figcaption></figure>
            <!-- /wp:table -->

            """,
            "en": self.wpWrapPara("""<p>This is illustrated in the table: {queryview}</p>""") + """

        	        <!-- wp:table {"hasFixedLayout":false} -->
            	    <figure class="wp-block-table"><table><tbody><tr><td width="100px"><strong>Wikidata Property</strong></td><td width="150px"><strong>Label</strong></td><td><strong>Values (number of instances)</strong></td></tr>__TABLEPROPVAL8__</tbody></table><figcaption class="wp-element-caption"><strong>Table: Most frequently used (property, value) pairs.</strong></figcaption></figure>
                    <!-- /wp:table -->

                    """,
            "es": self.wpWrapPara("""<p>Ce qui s'illustre dans la table: {queryview}</p>""") + """

        	        <!-- wp:table {"hasFixedLayout":false} -->
        	        <figure class="wp-block-table"><table><tbody><tr><td width="100px"><strong>Propriété Wikidata</strong></td><td width="150px"><strong>Label</strong></td><td><strong>Valeurs (nombre d'instances)</strong></td></tr>__TABLEPROPVAL8__</tbody></table><figcaption class="wp-element-caption"><strong>Table: Les paires (propriété, valeur) les plus utilisées.</strong></figcaption></figure>
                    <!-- /wp:table -->

                    """,
        }
        return models.get(self.lang, models["en"])

    def buildMermaidView(self):
        mermaidblock = """<!-- wp:wp-mermaid/block -->
<div class="wp-block-wp-mermaid-block mermaid">
mindmap
  root((__ENTITYNAME__))
__GENRELIST__    
__DEPICTLIST__
__TYPELIST__
</div>
<!-- /wp:wp-mermaid/block -->

            """
        models = {
            "fr": mermaidblock,
            "en": mermaidblock,
            "es": mermaidblock,
        }
        return models.get(self.lang, models["en"])

    def buildScrutartLink(self, title):
        # ici chercher l'url d'une page avec ce titre
        # si la page n'existe pas, la créer et récupérer l'url
        link = self.wpWrapPara(
            """<a href="">""" + title + """</a>""")
        return link

    def buildTitre(self, varstring="__ENTITYNAME__"):
        title = {
            "fr": f"""Où trouver {varstring} dans Wikidata, suivez le guide""", # titre pour créateur
            "en": f"""Where to find {varstring} in Wikidata, follow the guide""", # titre pour créateur
            "es": """Título temporal""",
        }
        return title[self.lang]

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
        label = {
            "fr": "Liens externes:",
            "en": "External links:",
            "es": "Liens externes:",
        }
        linksBlock = f"""
        <!-- wp:table {{"style":{{"border":{{"width":"0px","style":"none"}}}}}} -->
        <p>{label[self.lang]}</p>
        <figure class="wp-block-table">
        <table class="has-fixed-layout" style="border-style:none;border-width:0px">
        <tbody>
        <tr>{varstring}</tr>
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
        note = {
            "fr": """<p><em>Note: les chiffres présentés dans ce billet correspondent à la situation du __DATE__</em></p>""",
            "en": """<p><em>Note: Note: the figures in this post correspond to the situation at __DATE__</em></p>""",
            "es": """<p><em>Nota: las cifras de este post corresponden a la situación en __DATE__</em></p>""",
        }
        wdqsnote = {
            "fr": """<p><em>L'icône <img class="wp-image-710" style="width: 50px;" src="https://scrutart.grains-de-culture.fr/wp-content/uploads/2025/05/boutonWDQS2.svg" alt="lien WDQS"> fournit un lien vers une requête à WDQS, l'outil qui permet d'interroger Wikidata par programme.</em></p>""",
            "en": """<p><em>The <img class="wp-image-710" style="width: 50px;" src="https://scrutart.grains-de-culture.fr/wp-content/uploads/2025/05/boutonWDQS2.svg" alt="WDQS link"> icon provides a link to a query to WDQS, the tool that allows Wikidata to be queried programmatically.</em></p>""",
            "es": """<p><em>El icono <img class="wp-image-710" style="width: 50px;" src="https://scrutart.grains-de-culture.fr/wp-content/uploads/2025/05/boutonWDQS2.svg" alt="WDQS link"> proporciona un enlace a una solicitud a WDQS, la herramienta que permite consultar Wikidata de forma programática.</em></p>"""
        }
        para = {
            "fr": f"""{insert}<p>Cette analyse s'appuie sur des requêtes sparql qui permettent d'interroger les données de Wikidata.</p>""",
            "en": f"""{insert}<p>This analysis is based on sparql queries that interrogate Wikidata data.</p>""",
            "es": f"""{insert}<p>Este análisis utiliza consultas sparql para interrogar los datos de Wikidata.</p>""",
        }
        intro = self.wpWrapPara(note[self.lang]) + self.wpWrapPara(wdqsnote[self.lang]) + self.wpWrapPara(para[self.lang])
        return intro

    def buildNombreOeuvresView(self, varnb="__NBOEUVRES__", varcrea="__ENTITYLINK__"):
        queryview = self.buildQueryNbOeuvresView()
        models = {
            "fr": f"""<p>Il y a <strong>{varnb} œuvres de {varcrea}</strong> dans Wikidata. {queryview}</p>""",
            "en": f"""<p>There are <strong>{varnb} works by {varcrea}</strong> in Wikidata. {queryview}</p>""",
            "es": f"""<p>Hay <strong>{varnb} obras de {varcrea}</strong> en Wikidata. {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryView_1_0(self, varstring=""):
        models = {
            "fr": """<p>(obtenu avec la requête sparql accessible <a href='""" + varstring + """'>sur WDQS</a>)</p>""",
            "en": """<p>(obtained with the sparql query accessible <a href='""" + varstring + """'>on WDQS</a>)</p>""",
            "es": """<p>(obtenido con la consulta sparql accesible <a href='""" + varstring + """'>en WDQS</a>)</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryView_2_0(self, varstring=""):
        models = {
            "fr": """<a href='""" + varstring + """'><img class="wp-image-710" style="width: 30px;" src="https://scrutart.grains-de-culture.fr/wp-content/uploads/2025/05/boutonWDQS2.svg" alt="lien WDQS"></a>""",
            "en": """<a href='""" + varstring + """'><img class="wp-image-710" style="width: 30px;" src="https://scrutart.grains-de-culture.fr/wp-content/uploads/2025/05/boutonWDQS2.svg" alt="WDQS link"></a>""",
            "es": """<a href='""" + varstring + """'><img class="wp-image-710" style="width: 30px;" src="https://scrutart.grains-de-culture.fr/wp-content/uploads/2025/05/boutonWDQS2.svg" alt="en WDQS"></a>""",
        }
        return models.get(self.lang, models["en"]) # self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryView(self, varstring="", version="2.0"):
        versionstr = version.replace(".", "_")
        fctName = f"""buildQueryView_{versionstr}"""
        fct = getattr(WPTemplate, fctName)
        res = fct(self, varstring)
        return res

    def buildQueryNbOeuvresView(self):
        return self.buildQueryView("__QUERYNBOEUVRES__")

    def buildNbTypesOeuvresView(self, varnbmain="__NBMAINTYPE__", varnbother="__NBOTHERTYPES__"):
        models = {
            "fr": """<p>Il s'agit de <strong>+""" + varnbmain + """</strong>, """ + varnbother + """.</p>""",
            "en": """<p>It's all about <strong>+""" + varnbmain + """</strong>, """ + varnbother + """.</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildNbTypesOeuvresView(self, varnbmain="__NBMAINTYPE__", varnbother="__NBOTHERTYPES__"):
        queryview = self.buildQueryNbParTypesView()
        models = {
            "fr": f"""<p>Il s'agit de <strong>{varnbmain}</strong>, {varnbother}. {queryview}</p>""",
            "en": f"""<p>They are <strong>{varnbmain}</strong>, {varnbother}. {queryview}</p>""",
            "es": f"""<p>Se trata de <strong>{varnbmain}</strong>, {varnbother}. {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryNbParTypesView(self):
        return self.buildQueryView("__QUERYNBPARTYPES__")

    def buildNbPropView(self, varnb="__NBPPROP__"):
        queryview = self.buildQueryNbproprietesView()
        models = {
            "fr": f"""<p>Pour décrire ces œuvres, <strong>{varnb} propriétés</strong> sont utilisées. {queryview}</p>""",
            "en": f"""<p>To describe these works, <strong>{varnb} properties</strong> are used.</p> {queryview}""",
            "es": f"""<p>Para describir estas obras se utilizan <strong>{varnb} propiedades</strong>. {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryNbproprietesView(self):
        return self.buildQueryView("__QUERYNBPROPRIETES__")


    def buildImportantesPropView(self):
        queryview = self.buildQueryImportantesPropView()
        models = {
            "fr": f"""<p><strong>__NBPROP50PLUS__ propriétés</strong> sont utilisées sur plus de la <strong>moitié des œuvres</strong>. {queryview}</p>""",
            "en": f"""<p><strong>__NBPROP50PLUS__ propriétés</strong> sont utilisées sur plus de la <strong>moitié des œuvres</strong>. {queryview}</p>""",
            "es": f"""<p><strong>__NBPROP50PLUS__ propriétés</strong> sont utilisées sur plus de la <strong>moitié des œuvres</strong>. {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryImportantesPropView(self):
        return self.buildQueryView("__QUERYNBPROP50PLUS__")

    def buildPropvalView(self):
        # TODO remplacer 8 par un autre seuil? par un seuil relatif?(ex: la moitié)
        queryview = self.buildQueryPropValView()
        models = {
            "fr": f"""<p>Il y a <strong>__NBPAIRESPROPVAL8__ paires (propriété, valeur)</strong> différentes utilisées sur au moins huit de ces œuvres. {queryview}</p>""",
            "en": f"""<p>There are <strong>__NBPAIRESPROPVAL8__ (property, value)</strong> different pairs used on at least eight of these works. {queryview}</p>""",
            "es": f"""<p>Il y a <strong>__NBPAIRESPROPVAL8__ paires (propriété, valeur)</strong> différentes utilisées sur au moins huit de ces œuvres. {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryPropValView(self):
        return self.buildQueryView("__QUERYPAIRESPROPVAL8__")

    def buildPropDePropvalView(self):
        queryview = self.buildQueryPropDePropValView()
        models = {
            "fr": f"""<p>Cela concerne <strong>__NBPROPPROPVAL8__ propriétés</strong>. {queryview}</p>""",
            "en": f"""<p>It as about <strong>__NBPROPPROPVAL8__ properties</strong>. {queryview}</p>""",
            "es": f"""<p>Cela concerne <strong>__NBPROPPROPVAL8__ propriétés</strong>. {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryPropDePropValView(self):
        return self.buildQueryView("__QUERYPROPPROPVAL8__")

    def buildQueryTableView(self):
        return self.buildQueryView("__QUERYPROPPROPVAL8__")

    def buildBarresView(self):
        queryview = self.buildQueryDonneesPourBarresView()
        models = {
            "fr": f"""<p>On peut accéder à une représentation graphique de la répartition par année des œuvres présentes sur Wikidata <a href="__QUERYLIENSWIKIDATABARRES__">ici</a> (remarque: si certaines années ne sont pas dans le graphe, c'est qu'il n'y a pas d'œuvres présentes dans Wikidata pour ces années). {queryview}</p>""",
            "en": f"""<p>You can access a graphical representation of the distribution by year of the works present on Wikidata <a href=“__QUERYLIENSWIKIDATABARRES__”>here</a> (note: if certain years are not in the graph, it's because there are no works present in Wikidata for those years). {queryview}</p>""",
            "es": f"""<p>On peut accéder à une représentation graphique de la répartition par année des œuvres présentes sur Wikidata <a href="__QUERYLIENSWIKIDATABARRES__">ici</a> (remarque: si certaines années ne sont pas dans le graphe, c'est qu'il n'y a pas d'œuvres présentes dans Wikidata pour ces années). {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryDonneesPourBarresView(self):
        return self.buildQueryView("__QUERYDONNEESPOURBARRES__")


    def buildNbPagesWikipediaView(self):
        queryview = self.buildQueryNbPagesWikipediaView()
        models = {
            "fr": f"""<p><strong>__NBPAGESWIKIPEDIA__ pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres. {queryview}</p>""",
            "en": f"""<p><strong>__NBPAGESWIKIPEDIA__ Wikipedia pages</strong> in at least one language are associated with these works. {queryview}</p>""",
            "es": f"""<p><strong>__NBPAGESWIKIPEDIA__ pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres. {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryNbPagesWikipediaView(self):
        return self.buildQueryView("__QUERYNBPAGESWIKIPEDIA__")

    def buildWikipediaParPaysView(self):
        queryview= self.buildQueryWikipediaParLangueView()
        models = {
            "fr": f"""<p>Dont __NBPAGESANGLO__ dans le Wikipedia anglophone et __NBPAGESFRANCO__ dans le Wikidata francophone. {queryview}</p>""",
            "en": f"""<p>Including __NBPAGESANGLO__ in English Wikipedia and __NBPAGESFRANCO__ in French Wikipedia. {queryview}</p>""",
            "es": f"""<p>Incluyendo __NBPAGESANGLO__ en Wikipedia en inglés y __NBPAGESFRANCO__ en Wikidata en francés. {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryWikipediaParLangueView(self):
        return self.buildQueryView("__QUERYNBWIKIPEDIAPARLANGUE__")

    def buildOeuvresWikipediaView(self):
        queryview = self.buildQueryOeuvreWikipediaView()
        models = {
            "fr": f"""<p>L'ensemble des pages concerne <strong>__NBOEUVRESAVECWIKIPEDIA__ œuvres</strong>. {queryview}</p>""",
            "en": f"""<p>All <strong>pages</strong> relate to <strong>__NBOEUVRESAVECWIKIPEDIA__ works</strong>. {queryview}</p>""",
            "es": f"""<p>Todas las páginas se refieren a las obras de <strong>__NBOEUVRESAVECWIKIPEDIA__. {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryOeuvreWikipediaView(self):
        return self.buildQueryView("__QUERYNBOEUVRESAVECWIKIPEDIA__")

    def buildImagesView(self):
        queryview = self.buildQueryImagesView()
        models = {
            "fr": f"""<p>Il y a <strong>__NBIMAGES__ images</strong> dans Wikimedia Commons associées à ces œuvres. {queryview}</p>""",
            "en": f"""<p>There are <strong>__NBIMAGES__ images</strong> in Wikimedia Commons associated with these works. {queryview}</p>""",
            "es": f"""<p>Existen <strong>__Imágenes NBIMAGES__</strong> en Wikimedia Commons asociadas a estas obras. {queryview}</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildQueryImagesView(self):
        return self.buildQueryView("__QUERYNBIMAGES__")


    def buildPicturesTableView(self):
        block = self.wpWrapPara("""<p></p """)+"""
        <!-- wp:table {"style":{"border":{"width":"0px","style":"none"}}} -->
        <figure class="wp-block-table">
        <table class="has-fixed-layout" style="border-style:none;border-width:0px">
        <tbody>
        <tr>
        __IMAGES_TABLE_BOXES__
        </tr>
        </tbody>
        </table>
        </figure>
        <!-- /wp:table -->

        """
        return block

    def buildGalleryLink(self):
        models = {
            "fr": """<p>Pour ceux qui sont pressés de voir des œuvres, on peut en voir une sélection d'images dans __GALLERY_LINK__. (vous avez plus de possibilités de réglages sur la galerie si vous vous inscrivez comme utilisateur).</p>""",
            "en": """<p>For those in a hurry to see works, a selection of images can be viewed in __GALLERY_LINK__. (You have more setting options on the gallery if you register as a user).</p>""",
            "es": """<p>Para los que tengan prisa por ver obras, se puede ver una selección de imágenes en __GALLERY_LINK__. (Tienes más opciones de configuración en la galería si te registras como usuario).</p>""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildFinView(self):
        models = {
            "fr": """<br>Nous avons ainsi donné un aperçu de la visibilité des œuvres de __ENTITYLINK__ dans Wikidata et des propriétés qui les décrivent. Nous allons maintenant étudier les informations absentes de Wikidata et que nous pouvons trouver par ailleurs. Si vous appréciez les efforts de notre association, <a href="https://grains-de-culture.fr/">'Grains de Culture'</a>, vous pouvez nous soutenir soit en vous inscrivant à l'association ou en faisant un don grâce à <a href="https://www.helloasso.com/associations/grains-de-culture">HelloAsso</a>. Vous pouvez aussi parcourir les nombreuses <a href="https://galeries.grains-de-culture.fr">galeries</a> que nous avons mis en ligne.""",
            "en": """<br>This has given us an overview of the visibility of __ENTITYLINK__ works in Wikidata and the properties that describe them. We're now going to look at the information that isn't available in Wikidata and that we can find elsewhere. If you appreciate the efforts of our association, <a href="https://grains-de-culture.fr/">'Grains de Culture'</a>, you can support us either by joining the association or by making a donation through <a href="https://www.helloasso.com/associations/grains-de-culture">HelloAsso</a>. You can also browse the many <a href="https://galleries.grains-de-culture.fr">galleries</a> we've put online.""",
            "es": """<br>Hemos dado así una visión general de la visibilidad de las obras __ENTITYLINK__ en Wikidata y de las propiedades que las describen. Ahora examinaremos la información que no está disponible en Wikidata y que podemos encontrar en otros sitios. Si aprecias los esfuerzos de nuestra asociación, <a href="https://grains-de-culture.fr/">'Grains de Culture'</a>, puedes apoyarnos uniéndote a la asociación o haciendo una donación a través de <a href="https://www.helloasso.com/associations/grains-de-culture">HelloAsso</a>. También puede consultar las numerosas <a href="https://galeries.grains-de-culture.fr">galerías</a> que tenemos en línea.""",
        }
        return self.wpWrapPara(models.get(self.lang, models["en"]))

    def buildScrutartLink(self, title):
        # TODO ici chercher l'url d'une page avec ce titre
        # si la page n'existe pas, la créer et récupérer l'url et la mettre comme href
        url = ""
        link = self.wpWrapPara(
            f"""<a href="{url}">{title}</a>""")
        return link

    def buildPageTemplate(self):
        pageTemplate = self.buildJsonProcessBlock() +\
                       self.buildJsonLdScript() +\
                       self.buildExternalLinks() +\
                       self.buildIntroView() + \
                       self.buildNombreOeuvresView() + \
                       self.buildGalleryLink() + \
                       self.buildMermaidView() + \
                       self.buildNbTypesOeuvresView() + \
                       self.buildNbPropView() + \
                       self.buildImportantesPropView() + \
                       self.buildPropvalView() + \
                       self.buildPropDePropvalView() + \
                       self.buildTableView() + \
                       self.buildBarresView() + \
                       self.buildNbPagesWikipediaView() + \
                       self.buildWikipediaParPaysView() + \
                       self.buildOeuvresWikipediaView() + \
                       self.buildImagesView() + \
                       self.buildPicturesTableView() + \
                       self.buildFinView()
        return pageTemplate
