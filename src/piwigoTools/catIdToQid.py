# but: input un id de catégorie piwigo en entrée, un qid d'entité wikidata en sortie
# méthode: utiliser les données de scrutartState pour trouver le résultats

from src.generationWordpress.CScrutartState import CScrutartState
def catidToQid(catid):
    qid = None
    return qid


if __name__ == "__main__":
    # extrait de la liste obtenue avec piwigoCategoriesComment.py
    sparqlTemplate = """    
        prefix wdt: <http://www.wikidata.org/prop/direct/>
        prefix wd: <http://www.wikidata.org/entity/>
        prefix kgdc: <https://kg.grains-de-culture.fr/entity/>
        prefix pgdc: <https://kg.grains-de-culture.fr/prop/>
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        prefix xsd: <http://www.w3.org/2001/XMLSchema#>
        select  ?creator (count(?s) as ?c) 
        {
          ?s wdt:P170 ?creator .
          ?s pgdc:piwigo_gallery <https://kg.grains-de-culture.fr/entity/gal__IDGAL__> 
        }
        group by ?creator
        """
    reference = {
        "927": "Q237911",
        "793": "Q2610236",
        "837": "Q191423",
        "838": "Q515553",
        "829": "Q637420",
        "826": "Q37562",
        "799": "Q17101440",
        "790": "Q330848",
        "331": "",  # 245 images
        "330": "",  # 55 images
        "329": "",  # 141 images
        "338": "",  # 557 images
        "410": "",  # 36 images
        "567": "",  # 149 images
        "424": "",  # 42 images
        "443": "",  # 43 images
        "381": "",  # 66 images
        "419": "",  # 50 images
        "467": "",  # 47 images
        "354": "",  # 135 images
        "552": "",  # 37 images
        "434": "",  # 62 images
        "471": "",  # 40 images
        "458": "",  # 131 images
        "461": "",  # 35 images
        "478": "",  # 48 images
        "475": "",  # 40 images
        "484": "",  # 43 images
        "495": "",  # 45 images
        "519": "",  # 55 images
        "599": "",  # 37 images
        "596": "",  # 39 images
        "615": "",  # 32 images
        "455": "",  # 54 images
        "454": "",  # 40 images
        "435": "",  # 95 images
        "433": "",  # 61 images
        "420": "",  # 65 images
        "425": "",  # 74 images
        "386": "",  # 75 images
        "379": "",  # 166 images
        "361": "",  # 62 images
        "360": "",  # 402 images
    }
    cs = CScrutartState()
    # appeler le sparql avec le catid et s'il n'y a qu'un créateur, c'est celui associé à la catégorie
    # s'il y a plusieurs créateurs, mais un seul avec beaucoup de créations alors on suppose que c'est lui, mais à vérifier à la main
    pass
