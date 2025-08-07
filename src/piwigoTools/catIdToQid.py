# but: input un id de catégorie piwigo en entrée, un qid d'entité wikidata en sortie
# méthode: utiliser les données de scrutartState pour trouver le résultat
from src.generationWordpress.CScrutartState import CScrutartState

def catidToQid(catid):
    qid = None
    cs = CScrutartState(urlread="http://datamusee.r2.enst.fr/scrutartState/query")
    # on commence à regarder dans scrutartSTate
    sparqlTemplate = """    
        prefix pgdc: <https://kg.grains-de-culture.fr/prop/>
        select  ?entity where { ?entity pgdc:piwigo_main_gallery <https://kg.grains-de-culture.fr/entity/gal__IDGAL__> }
        """
    res = cs.sparqlQuery(sparqlTemplate.replace("__IDGAL__", str(galId)))
    if res and res.bindings:
        entity = res.bindings[0]["entity"].value
        qid = entity.replace("http://www.wikidata.org/entity/", "")
        return qid
    # si pas dans scrutartState, on cherche par une première heuristique sur scrutartState
    # si c'est un catid de peintre et que presque toutes les créations de cette galerie sont du même créateur
    # on considère qu'il s'agit de la galerie de ce créateur
    sparqlTemplate = """    
        prefix wdt: <http://www.wikidata.org/prop/direct/>
        prefix pgdc: <https://kg.grains-de-culture.fr/prop/>
        select  ?entity (count(?s) as ?c) 
        {
          ?s wdt:P170 ?entity .
          ?s pgdc:piwigo_gallery <https://kg.grains-de-culture.fr/entity/gal__IDGAL__> 
        }
        group by ?entity
        """
    res = cs.sparqlQuery(sparqlTemplate.replace("__IDGAL__", str(galId)))
    if res and res.bindings:
        entityList = res.bindings
        seuilNombreOeuvresMinimal = 20
        seuilNombreOeuvresMaximal = 5
        if len(entityList)==1 and int(entityList[0]["c"].value)>seuilNombreOeuvresMinimal:
            entity = res.bindings[0]["entity"].value
            qid = entity.replace("http://www.wikidata.org/entity/", "")
            return qid
        elif len(entityList)>1:
            hypo = []
            for entity in entityList:
                if int(entity["c"].value)<seuilNombreOeuvresMaximal:
                    pass # pas assez d'oeuvres, je néglige cette hypothèse; ajouter un log
                else:
                    # je prends en compte cette hypothèse
                    hypo.append(entity["entity"].value)
            if len(hypo)==1:
                entity = hypo[0]
                qid = entity.replace("http://www.wikidata.org/entity/", "")
                return qid
            # ce serait bien de mettre un log s'il y 0 ou plusieurs hypothèses
        pass
    return qid

def qidToCatid(qid):
    catid = None
    # on commence à regarder dans scrutartSTate si scrutartState est accessible
    cs = CScrutartState(urlread="http://datamusee.r2.enst.fr/scrutartState/query")
    # on commence à regarder dans scrutartSTate
    sparqlTemplate = """    
        prefix pgdc: <https://kg.grains-de-culture.fr/prop/>
        select  ?entity where { <http://www.wikidata.org/entity/__QID__> pgdc:piwigo_main_gallery ?galid }
        """
    res = cs.sparqlQuery(sparqlTemplate.replace("__QID__", str(qid)))
    if res and res.bindings:
        entity = res.bindings[0]["entity"].value
        catid = entity.replace("https://kg.grains-de-culture.fr/entity/gal", "")
        return catid
    # si pas dans scrutartState, on cherche par une première heuristique sur scrutartState
    # si c'est un qid de peintre et que presque toutes les créations de ce peintre sont principalement dans une seule galerie
    # on considère qu'il s'agit de la galerie de ce créateur
    sparqlTemplate = """    
        prefix wdt: <http://www.wikidata.org/prop/direct/>
        prefix pgdc: <https://kg.grains-de-culture.fr/prop/>
        select  ?galid (count(?s) as ?c) 
        {
          ?s wdt:P170 <http://www.wikidata.org/entity/__QID__> .
          ?s pgdc:piwigo_gallery ?galid 
        }
        group by ?galid
        order by desc(?c)
        """
    res = cs.sparqlQuery(sparqlTemplate.replace("__QID__", str(qid)))
    if res and res.bindings:
        galList = res.bindings
        seuilNombreOeuvresMinimal = 20
        seuilNombreOeuvresMaximal = 5
        if len(galList) == 1 and int(galList[0]["c"].value) > seuilNombreOeuvresMinimal:
            galuri = res.bindings[0]["galid"].value
            catid = galuri.replace("https://kg.grains-de-culture.fr/entity/gal", "")
            return catid
        elif len(galList) > 1:
            hypo = galList[0]["galid"].value.replace("https://kg.grains-de-culture.fr/entity/gal", "")
            c_hypo = int(galList[0]["c"].value)
            c_follower = int(galList[1]["c"].value)
            if c_hypo/c_follower > 3:
                return hypo
            else:
                # could be a log
                print(f"""Plusieurs galeries envisageables; vérifier à la main: {galList[0]["galid"].value}, {galList[1]["galid"].value}""")
        else:
            print(qid, galList)
            pass
    return catid

if __name__ == "__main__":
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
    # extrait de la liste obtenue avec piwigoCategoriesComment.py
    reference = {
        "927": "Q237911",
        "793": "Q2610236",
        "837": "Q191423",
        "838": "Q515553",
        "829": "Q568760",
        "826": "Q37562",
        "799": "Q17101440",
        "790": "Q330848",
        "331": "Q148475",  # 245 images
        "330": "Q5582",  # 55 images
        "329": "Q39931",  # 142 images
        "338": "Q35548",  # 557 images
        "410": "Q310715",  # 36 images
        "567": "Q334200",  # 149 images
        "424": "Q120993",  # 42 images
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
    # cs = CScrutartState()
    cs = CScrutartState(urlread="http://datamusee.r2.enst.fr/scrutartState/query")
    # appeler le sparql avec le catid et s'il n'y a qu'un créateur, c'est celui associé à la catégorie
    # s'il y a plusieurs créateurs, mais un seul avec beaucoup de créations alors on suppose que c'est lui, mais à vérifier à la main
    for galId in reference:
        res = cs.sparqlQuery(sparqlTemplate.replace("__IDGAL__", str(galId)))
        if res and  res.bindings:
            creatorList = res.bindings
            if len(creatorList)==1:
                print(galId, "OK" if creatorList[0]["creator"].value.replace("http://www.wikidata.org/entity/", "")==reference[galId] else "??",
                      creatorList[0]["creator"].value, creatorList[0]["c"].value, "-->", reference[galId])
            elif len(creatorList)>1:
                print("\n--------------------------")
                for crea in creatorList:
                    if int(crea["c"].value)<5:
                        print(galId, "OK" if crea["creator"].value.replace("http://www.wikidata.org/entity/", "")==reference[galId] else "BAD",
                              crea["creator"].value, crea["c"].value, "--> ", reference[galId])
                    else:
                        print(galId, "OK" if crea["creator"].value.replace("http://www.wikidata.org/entity/", "")==reference[galId] else "BAD",
                              crea["creator"].value, crea["c"].value, "--> ", reference[galId])
                print("===========================\n")
        else:
            print(f"Il est probable que les images de {galId} n'ont pas été intégrées à scrutartState")

        pass

globalQuery = """
prefix wdt: <http://www.wikidata.org/prop/direct/>
prefix wd: <http://www.wikidata.org/entity/>
prefix kgdc: <https://kg.grains-de-culture.fr/entity/>
prefix pgdc: <https://kg.grains-de-culture.fr/prop/>
prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
prefix xsd: <http://www.w3.org/2001/XMLSchema#>
select  ?galery ?creator (count(?s) as ?c) 
{
  ?s wdt:P170 ?creator .
  ?s pgdc:piwigo_gallery ?galery 
}
group by ?galery ?creator
order by desc(?c)
"""
print("#############################################")
globalres = cs.sparqlQuery(globalQuery)
if globalres and globalres.bindings:
    for galres in globalres.bindings:
        galId = galres["galery"].value.replace("https://kg.grains-de-culture.fr/entity/gal", "")
        qid = galres["creator"].value.replace("http://www.wikidata.org/entity/", "")
        ref = reference.get(galId, "?")
        if qid==ref:
            print(galres)
print("#############################################")
print("#############################################")
for galId in reference:
    print(galId, catidToQid(galId))

print("#############################################")
print("#############################################")
for galid, qid in reference.items():
    catid = qidToCatid(qid)
    print(qid, galid, catid , " --> OK" if catid==galid else "?")