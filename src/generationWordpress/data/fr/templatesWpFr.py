templatesCreateur = {
    "lang": "en",
    "titreTemplate": """__NOMCREATEUR__ dans Wikidata""",

    "imageTemplate": """<!-- wp:image {"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="__URLIMAGE__" alt="" /></figure>
<!-- /wp:image -->
""",

    "introTemplate": """<!-- wp:paragraph -->
<p><em>Note: les chiffres de ce billet correspondent à la situation du __DATE__</em></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Je vais faire dans ce billet une analyse de la présence des œuvres de __LINKCREATEUR__ dans Wikidata et de leur description.</p>
<p>Cette analyse s'appuie sur des requêtes sparql qui permettent d'interroger les données de Wikidata. Un lien est fourni pour exécuter la requête dans WDQS, l'outil d'interrogation SPARQL de Wikidata</p>
<!-- /wp:paragraph -->

""",

    "nombreOeuvresTemplate": """<!-- wp:paragraph -->
<p>Il y a <strong>__NBOEUVRES__ œuvres de __LINKCREATEUR__</strong> dans Wikidata.</p>
<!-- /wp:paragraph -->

""",

    "queryNbOeuvresTemplate": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBOEUVRES__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "nbTypesOeuvresTemplate": """<!-- wp:paragraph -->
<p>Il s'agit de <strong>__NBMAINTYPE__</strong>, __NBOTHERTYPES__.</p>
<!-- /wp:paragraph -->

""",

    "queryNbParTypesTemplate": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBPARTYPES__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "nbPropTemplate": """<!-- wp:paragraph -->
<p>Pour décrire ces œuvres, <strong>__NBPPROP__ propriétés</strong> sont utilisées.</p>
<!-- /wp:paragraph -->

""",

    "queryNbproprietesTemplate": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBPROPRIETES__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "importantesPropTemplate": """<!-- wp:paragraph -->
<p><strong>__NBPROP50PLUS__ propriétés</strong> sont utilisées sur plus de la <strong>moitié des œuvres</strong>.</p>
<!-- /wp:paragraph -->

""",

    "queryImportantesPropTemplate": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBPROP50PLUS__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "propvalTemplate": """<!-- wp:paragraph -->
<p>Il y a <strong>__NBPAIRESPROPVAL8__ paires (propriété, valeur)</strong> différentes utilisées sur au moins huit de ces œuvres.</p>
<!-- /wp:paragraph -->

""",

    "queryPropValTemplate": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYPAIRESPROPVAL8__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "propDePropvalTemplate": """<!-- wp:paragraph -->
<p>Cela concerne <strong>__NBPROPPROPVAL8__ propriétés</strong>.</p>
<!-- /wp:paragraph -->

""",

    "queryPropDePropValTemplate": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYPROPPROPVAL8__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "tableTemplate": """<!-- wp:paragraph -->
<p>Ce qui s'illustre dans la table:</p>
<!-- /wp:paragraph -->

<!-- wp:table -->
<figure class="wp-block-table"><table><tbody><tr><td><strong>Propriété Wikidata</strong></td><td><strong>Label</strong></td><td><strong>Valeurs (nombre d'instances)</strong></td></tr>__TABLEPROPVAL8__</tbody></table><figcaption class="wp-element-caption"><strong>Table: Les paires (propriété, valeur) utilisées plus de 8 fois.</strong></figcaption></figure>
<!-- /wp:table -->

""",

    "queryTableTemplate": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYPROPPROPVAL8__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "mermaidTemplate": """<!-- wp:wp-mermaid/block -->
<div class="wp-block-wp-mermaid-block mermaid">
mindmap
  root((__NOMCREATEUR__))
    Genre
__GENRELIST__    
    Depicts
__DEPICTLIST__
    Types
__TYPELIST__
</div>
<!-- /wp:wp-mermaid/block -->

""",

    "barresTemplate": """<!-- wp:paragraph -->
<p>On peut accéder à une représentation graphique de la répartition par année des œuvres présentes sur Wikidata <a href="__QUERYLIENSWIKIDATABARRES__">ici</a> (remarque: si certaines années ne sont pas dans le graphe, c'est qu'il n'y a pas d'œuvres présentes dans Wikidata pour ces années).</p>
<!-- /wp:paragraph -->

""",

    "queryDonneesPourBarres": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYDONNEESPOURBARRES__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "nbPagesWikipedia": """<!-- wp:paragraph -->
<p><strong>__NBPAGESWIKIPEDIA__ pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>
<!-- /wp:paragraph -->

""",

    "queryNbPagesWikipedia": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBPAGESWIKIPEDIA__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "wikipediaParPays": """<!-- wp:paragraph -->
<p>Dont __NBPAGESANGLO__ dans le Wikipedia anglophone et __NBPAGESFRANCO__ dans le Wikipedia francophone.</p>
<!-- /wp:paragraph -->

""",

    "queryWikipediaParLangue": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBWIKIPEDIAPARLANGUE__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "oeuvresWikipediaTemplate": """<!-- wp:paragraph -->
<p>L'ensemble des <strong>pages</strong> concerne <strong>__NBOEUVRESAVECWIKIPEDIA__ œuvres</strong>.</p>
<!-- /wp:paragraph -->

""",

    "queryOeuvreWikipediaTemplate": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBOEUVRESAVECWIKIPEDIA__">sur WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "imagesTemplate": """<!-- wp:paragraph -->
<p>Il y a <strong>__NBIMAGES__ images</strong> dans Wikimedia Commons associées à ces œuvres.</p>
<!-- /wp:paragraph -->

""",

    "queryImagesTemplate": """<!-- wp:paragraph -->
<p>(obtenu avec la requête sparql accessible <a href="__QUERYNBIMAGES__">sur WDQS</a>)<br></p>
<!-- /wp:paragraph -->

""",

    "finTemplate": """<!-- wp:paragraph -->
<br>J'ai ainsi donné un aperçu de la visibilité des œuvres de __LINKCREATEUR__ dans Wikidata et des propriétés qui les décrivent. Je vais maintenant voir si des œuvres sont présentes dans <a href="https://datamusee.wp.imt.fr/2023/12/04/the-joconde-dataset-and-lod/">SemJoconde</a> et absentes de Wikidata pour compléter Wikidata si nécessaire ou si des compléments d'informations sur les œuvres peuvent être obtenues avec <a href="https://datamusee.wp.imt.fr/2023/12/04/the-joconde-dataset-and-lod/">SemJoconde</a>.
<!-- /wp:paragraph -->
"""

}


def getPageTemplate():
    pageTemplate = templatesCreateur["imageTemplate"] + \
                   templatesCreateur["introTemplate"] + templatesCreateur["nombreOeuvresTemplate"] + \
                   templatesCreateur["queryNbOeuvresTemplate"] + \
                   templatesCreateur["nbTypesOeuvresTemplate"] + templatesCreateur["queryNbParTypesTemplate"] + \
                   templatesCreateur["nbPropTemplate"] + templatesCreateur["queryNbproprietesTemplate"] + \
                   templatesCreateur["importantesPropTemplate"] + templatesCreateur["queryImportantesPropTemplate"] + \
                   templatesCreateur["propvalTemplate"] + templatesCreateur["queryPropValTemplate"] + \
                   templatesCreateur["propDePropvalTemplate"] + templatesCreateur["queryPropDePropValTemplate"] + \
                   templatesCreateur["tableTemplate"] + templatesCreateur["queryTableTemplate"] + \
                   templatesCreateur["mermaidTemplate"] + \
                   templatesCreateur["barresTemplate"] + templatesCreateur["queryDonneesPourBarres"] + \
                   templatesCreateur["nbPagesWikipedia"] + templatesCreateur["queryNbPagesWikipedia"] + \
                   templatesCreateur["wikipediaParPays"] + templatesCreateur["queryWikipediaParLangue"] + \
                   templatesCreateur["oeuvresWikipediaTemplate"] + templatesCreateur["queryOeuvreWikipediaTemplate"] + \
                   templatesCreateur["imagesTemplate"] + templatesCreateur["queryImagesTemplate"] + \
                   templatesCreateur["finTemplate"]
    return pageTemplate
