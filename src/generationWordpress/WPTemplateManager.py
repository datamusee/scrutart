class WPTemplate():

    def __init__(self, lang="fr"):
        self.lang = lang
        self.dataConfig = None

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

    def buildTitre(self, varstring="__NOMCREATEUR__"):
        return """Titre temporaire"""

    def buildJsonProcessBlock(self, varcrea="__PROCESSPARAMS__"):
        commentProcess = """
        <!-- wp:html -->
        <!-- processParams = { "qid": \""""+varcrea+"""\", "templateVersion": \""""+self.version+"""\" } -->
        <!-- /wp:html -->        
        """
        return commentProcess

    def buildJsonLdScript(self, varstring="__NOMCREATEUR__"):
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

    def buildNombreOeuvresView(self, varnb="__NBOEUVRES__", varcrea="__LINKCREATEUR__"):
        return self.wpWrapPara(
            """<p>Il y a <strong>""" + varnb + """ œuvres de """ + varcrea + """</strong> dans Wikidata.</p>""")

    def buildQueryView(self, varstring=""):
        return """"""

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
        <figure class="wp-block-table"><table><tbody><tr><td><strong>Propriété Wikidata</strong></td><td><strong>Label</strong></td><td><strong>Valeurs (nombre d'instances)</strong></td></tr>__TABLEPROPVAL8__</tbody></table><figcaption class="wp-element-caption"><strong>Table: Les paires (propriété, valeur) utilisées plus de 8 fois.</strong></figcaption></figure>
        <!-- /wp:table -->
    
        """

    def buildQueryTableView(self):
        return self.buildQueryView("__QUERYPROPPROPVAL8__")

    def buildMermaidView(self):
        return """<!-- wp:wp-mermaid/block -->
<div class="wp-block-wp-mermaid-block mermaid">
mindmap
  root((__NOMCREATEUR__))
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
        """<br>J'ai ainsi donné un aperçu de la visibilité des œuvres de __LINKCREATEUR__ dans Wikidata et des propriétés qui les décrivent. Je vais maintenant voir si des œuvres sont présentes dans <a href="https://datamusee.wp.imt.fr/fr/2023/12/04/le-jeu-de-donnees-joconde-et-le-lod/">SemJoconde</a> et absentes de Wikidata pour compléter Wikidata si nécessaire ou si des compléments d'informations sur les œuvres peuvent être obtenues avec <a href="https://datamusee.wp.imt.fr/fr/2023/12/04/le-jeu-de-donnees-joconde-et-le-lod/">SemJoconde</a>.""")

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
