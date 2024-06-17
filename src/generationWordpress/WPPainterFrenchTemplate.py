from WPPainterTemplate import WPPainterTemplate
class WPPainterFrenchTemplate(WPPainterTemplate):

    def __init__(self):
        super().__init__("fr")

    def buildTitre(self, varstring="__NOMCREATEUR__"):
        return """Où trouver """ + varstring + """ dans Wikidata, suivez le guide"""

    def buildIntroView(self):
        intro = super().buildIntroView("""<p>Je vais faire dans ce billet une analyse de la présence des œuvres de __LINKCREATEUR__ dans Wikidata et de leur description.</p>""")
        return intro

    def buildNombreOeuvresView(self, varnb="__NBOEUVRES__", varcrea="__LINKCREATEUR__"):
        return self.wpWrapPara(
            """<p>Il y a <strong>""" + varnb + """ œuvres de """ + varcrea + """</strong> dans Wikidata.</p>""")

    def buildQueryView(self, varstring=""):
        return self.wpWrapPara(
            """<p>(obtenu avec la requête sparql accessible <a href='""" + varstring + """'>sur WDQS</a>)</p>""")

    def buildNbTypesOeuvresView(self, varnbmain="__NBMAINTYPE__", varnbother="__NBOTHERTYPES__"):
        return self.wpWrapPara(
            """<p>Il s'agit de <strong>+""" + varnbmain + """</strong>, """ + varnbother + """.</p>""")

    def buildNbPropView(self, varnb="__NBPPROP__"):
        return self.wpWrapPara(
            """<p>Pour décrire ces œuvres, <strong>""" + varnb + """ propriétés</strong> sont utilisées.</p>""")

    def buildImportantesPropView(self):
        return self.wpWrapPara(
            """<p><strong>__NBPROP50PLUS__ propriétés</strong> sont utilisées sur plus de la <strong>moitié des œuvres</strong>.</p>""")

    def buildPropvalView(self):
        return self.wpWrapPara(
            """<p>Il y a <strong>__NBPAIRESPROPVAL8__ paires (propriété, valeur)</strong> différentes utilisées sur au moins huit de ces œuvres.</p>""")

    def buildPropDePropvalView(self):
        return self.wpWrapPara("""<p>Cela concerne <strong>__NBPROPPROPVAL8__ propriétés</strong>.</p>""")

    def buildTableView(self): return self.wpWrapPara("""<p>Ce qui s'illustre dans la table:</p>""") + """
    
        <!-- wp:table -->
        <figure class="wp-block-table"><table><tbody><tr><td><strong>Propriété Wikidata</strong></td><td><strong>Label</strong></td><td><strong>Valeurs (nombre d'instances)</strong></td></tr>__TABLEPROPVAL8__</tbody></table><figcaption class="wp-element-caption"><strong>Table: Les paires (propriété, valeur) utilisées plus de 8 fois.</strong></figcaption></figure>
        <!-- /wp:table -->
    
        """

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

    def buildNbPagesWikipediaView(self): return self.wpWrapPara(
        """<p><strong>__NBPAGESWIKIPEDIA__ pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>""")

    def buildWikipediaParPaysView(self):
        return self.wpWrapPara(
            """<p>Dont __NBPAGESANGLO__ dans le Wikipedia anglophone et __NBPAGESFRANCO__ dans le Wikidata francophone.</p>""")

    def buildOeuvresWikipediaView(self):
        return self.wpWrapPara(
            """<p>L'ensemble des <strong>pages</strong> concerne <strong>__NBOEUVRESAVECWIKIPEDIA__ œuvres</strong>.</p>""")

    def buildImagesView(self):
        return self.wpWrapPara(
            """<p>Il y a <strong>__NBIMAGES__ images</strong> dans Wikimedia Commons associées à ces œuvres.</p>""")

    def buildFinView(self): return self.wpWrapPara(
        """<p>J'ai ainsi donné un aperçu de la visibilité des œuvres de __LINKCREATEUR__ dans Wikidata et des propriétés qui les décrivent. Je vais maintenant voir si des œuvres sont présentes dans <a href="https://datamusee.wp.imt.fr/fr/2023/12/04/le-jeu-de-donnees-joconde-et-le-lod/">SemJoconde</a> et absentes de Wikidata pour compléter Wikidata si nécessaire ou si des compléments d'informations sur les œuvres peuvent être obtenues avec <a href="https://datamusee.wp.imt.fr/fr/2023/12/04/le-jeu-de-donnees-joconde-et-le-lod/">SemJoconde</a>.</p>""")

    def buildScrutartLink(self, title):
        # ici chercher l'url d'une page avec ce titre
        # si la page n'existe pas, la créer et récupérer l'url
        link = self.wpWrapPara(
            """<a href="">"""+title+"""</a>""")
        return link
