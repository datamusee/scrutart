# but: générer des contenus prêts à être intégrés dans un wordpress
# voir ticket 1527 pour un peu mieux identifier les créateurs candidats
import json
import os
from PageBuilder import PageBuilder
from entitiesList import entitiesList
from tools.scrutartStateManager import scrutartStateManager

def cleanTargetDirectory(targetDir, entityList):
    if not os.path.exists(targetDir):
        os.makedirs(targetDir)
    filelist = os.listdir(targetDir)
    for qid in entityList:
        if f"""{qid}.wp""" in filelist:
            os.remove(f"{targetDir}/{qid}.wp")


if __name__=="__main__":
    # scrutartState = scrutartStateManager("http://127.0.0.1:3030/scrutartState/query") # si local
    scrutartState = scrutartStateManager("https://datamusee.r2.enst.fr/scrutartState/query") # si TPT
    # ne traiter que les entités qui sont dans filterEntities en supprimant la page si elle existe déjà
    # filterEntities =  [   "Q5597" ] # Raphaël entitiesList
    # filterEntities =  [   "Q334200" ] # Christian  Krohg  entitiesList
    filterEntities =  [   "Q347139" ] # JB Greuze  entitiesList
    pageType = "Q1028181"
    labelType = {
        "Q1028181": "painter",
    }
    pageLang = "fr"
    targetDir = f"""./pages/{pageType}_{labelType[pageType]}/{pageLang}"""
    # detruire les pages à générer si elles existent déjà
    cleanTargetDirectory(targetDir, filterEntities)

    crtPageBuilder = PageBuilder(pageType, lang=pageLang)  # type=peintre, default lang fr
    types = []
    if not filterEntities:
        with open("data/wikidataSignificantPaintersTicket1527.json", encoding="UTF-8") as fListTypes:
            types = json.load(fListTypes)
            filterEntities = [ elmt["entity"].replace("http://www.wikidata.org/entity/", "") for elmt in types ]# ligne à enlever si je ne veux pas tout traiter et tenir compte du filtre
        for p in types:
            qid = p["entity"].replace("http://www.wikidata.org/entity/", "")
            if not qid in filterEntities:
                continue
            crtPageBuilder.generatePage(qid, targetDir)
    else:
        for qid in filterEntities:
            crtPageBuilder.generatePage(qid, targetDir)

