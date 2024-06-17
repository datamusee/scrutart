templatesCreateur = {
    "lang": "en",
    "titreTemplate": """Where to find __NOMCREATEUR__ in Wikidata, follow the guide""",

    "imageTemplate": """<!-- wp:image {"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="__URLIMAGE__" alt="" /></figure>
<!-- /wp:image -->
""",

    "introTemplate": """<!-- wp:paragraph -->
<p><em>Note: the values in this post correspond to the situation on __DATE__</em></p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>In this blog post, I will delve into an analysis of the representation of __LINKCREATEUR__'s artworks within Wikidata and explore the intricacies of their descriptions.</p>
<p>The foundation of this analysis lies in the utilization of SPARQL queries, a powerful tool for querying Wikidata's extensive dataset.</p>
<p>To immerse yourself in the exploration, a link is provided for executing the query within WDQS, Wikidata's SPARQL querying tool.</p>
<p>Join me on this journey to unravel the rich tapestry of information surrounding Honoré Daumier's artistic legacy, using the precision of SPARQL queries to assemble information that is present in Wikidata, but not directly accessible.</p>
<!-- /wp:paragraph -->

""",

    "nombreOeuvresTemplate": """<!-- wp:paragraph -->
<p>There are <strong>__NBOEUVRES__ works by __LINKCREATEUR__</strong> in Wikidata.</p>
<!-- /wp:paragraph -->

""",

    "queryNbOeuvresTemplate": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYNBOEUVRES__">on WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "nbTypesOeuvresTemplate": """<!-- wp:paragraph -->
<p>These include <strong>__NBMAINTYPE__</strong>, __NBOTHERTYPES__.</p>
<!-- /wp:paragraph -->

""",

    "queryNbParTypesTemplate": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYNBPARTYPES__">on WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "nbPropTemplate": """<!-- wp:paragraph -->
<p>To describe these works,  <strong>__NBPPROP__ propriétés</strong> are used.</p>
<!-- /wp:paragraph -->

""",

    "queryNbproprietesTemplate": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYNBPROPRIETES__">on WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "importantesPropTemplate": """<!-- wp:paragraph -->
<p><strong>__NBPROP50PLUS__ propriétés</strong> properties are used on more than <strong>half of the works</strong>.</p>
<!-- /wp:paragraph -->

""",

    "queryImportantesPropTemplate": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYNBPROP50PLUS__">on WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "propvalTemplate": """<!-- wp:paragraph -->
<p>There are <strong>__NBPAIRESPROPVAL8__ different (property, value) pairs</strong> used on at least eight of these works.</p>
<!-- /wp:paragraph -->

""",

    "queryPropValTemplate": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYPAIRESPROPVAL8__">on WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "propDePropvalTemplate": """<!-- wp:paragraph -->
<p>This concerns <strong>__NBPROPPROPVAL8__ properties</strong>.</p>
<!-- /wp:paragraph -->

""",

    "queryPropDePropValTemplate": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYPROPPROPVAL8__">on WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "tableTemplate": """<!-- wp:paragraph -->
<p>This is illustrated in the table:</p>
<!-- /wp:paragraph -->

<!-- wp:table -->
<figure class="wp-block-table"><table><tbody><tr><td><strong>Wikidata property</strong></td><td><strong>Label</strong></td><td><strong>Values (number of instances)</strong></td></tr>__TABLEPROPVAL8__</tbody></table><figcaption class="wp-element-caption"><strong>Table: Pairs (property, value) used more than 8 times.
</strong></figcaption></figure>
<!-- /wp:table -->

""",

    "queryTableTemplate": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYPROPPROPVAL8__">on WDQS</a>)</p>
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
  (note: if certain years are not in the graph, there are no works present in Wikidata for those years).
<p>A graphical representation of the distribution by year of the works present on Wikidata can be accessed <a href="__QUERYLIENSWIKIDATABARRES__">here</a> (note: if certain years are not in the graph, there are no works present in Wikidata for those years).</p>
<!-- /wp:paragraph -->

""",

    "queryDonneesPourBarres": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYDONNEESPOURBARRES__">on WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "nbPagesWikipedia": """<!-- wp:paragraph -->
<p><strong>__NBPAGESWIKIPEDIA__ pages</strong> d'un <strong>Wikipedia</strong> in at least one language are associated with these works.</p>
<!-- /wp:paragraph -->

""",

    "queryNbPagesWikipedia": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYNBPAGESWIKIPEDIA__">on WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "wikipediaParPays": """<!-- wp:paragraph -->
<p>Of which __NBPAGESANGLO__ in English Wikipedia and __NBPAGESFRANCO__ in French Wikipedia.</p>
<!-- /wp:paragraph -->

""",

    "queryWikipediaParLangue": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYNBWIKIPEDIAPARLANGUE__">on WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "oeuvresWikipediaTemplate": """<!-- wp:paragraph -->
<p>All <strong>pages</strong> concern <strong>__NBOEUVRESAVECWIKIPEDIA__ works</strong>.</p>
<!-- /wp:paragraph -->

""",

    "queryOeuvreWikipediaTemplate": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYNBOEUVRESAVECWIKIPEDIA__">on WDQS</a>)</p>
<!-- /wp:paragraph -->

""",

    "imagesTemplate": """<!-- wp:paragraph -->
<p>There are <strong>__NBIMAGES__ images</strong> in Wikimedia Commons associated with these works.</p>
<!-- /wp:paragraph -->

""",

    "queryImagesTemplate": """<!-- wp:paragraph -->
<p>(obtained with the sparql query accessible <a href="__QUERYNBIMAGES__">on WDQS</a>)<br></p>
<!-- /wp:paragraph -->

""",

    "finTemplate": """<!-- wp:paragraph -->
<br>In conclusion, I have provided a comprehensive overview of the visibility of __LINKCREATEUR__'s works on Wikidata, along with the corresponding descriptive properties. Moving forward, my next step involves exploring <a href="https://datamusee.wp.imt.fr/2023/12/04/the-joconde-dataset-and-lod/">SemJoconde</a> to identify any works that may be present in <a href="https://datamusee.wp.imt.fr/2023/12/04/the-joconde-dataset-and-lod/">SemJoconde</a> but are currently absent from Wikidata. This endeavor aims to enrich Wikidata with additional information or, when needed, supplement it with missing entries. Additionally, I will assess whether <a href="https://datamusee.wp.imt.fr/2023/12/04/the-joconde-dataset-and-lod/">SemJoconde</a> can offer further insights into these works, providing a more holistic understanding of __LINKCREATEUR__'s artistic legacy. Your enthusiasm for history of the arts is crucial in fostering a vibrant community, and I invite you to support this blog post and the Grains de Culture association on the social networks."
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
