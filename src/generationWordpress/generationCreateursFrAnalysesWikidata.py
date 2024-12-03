# but: générer des contenus prêts à être intégrés dans un wordpress
# part d'un template basé sur le billet
# https://datamusee.wp.imt.fr/fr/2024/01/12/paul-gauguin-dans-wikidata/
# récupération de la source de cette page comme base de template
# ce code source est copiée de generationWordpress\generationCreateursFrAnalysesWikidata.py
# il parait souhaitable d'homogénéiser le code pour les différentes langues et les différents thèmes
# dans le cas des créateurs, on a relativement peu d'instances d'oeuvres et pas rencontré de timeout
import datetime
import time
import json
import os
import src.generationWordpress.PageBuilder as PageBuilder

# ne traiter que ceux qui sont dans filterEntities en supprimant la page si elle existe déjà
filterEntities = [
    "Q295144" # Caillebotte
]
filelist = os.listdir("./pages/creator/fr")
for qid in filterEntities:
    if "{qid}.wp".format(qid=qid) in filelist:
        os.remove("pages/creator/fr/{qid}.wp".format(qid=qid))

pbTypeFr = PageBuilder.PageBuilder("Q1028181")  # type=peintre, default lang fr
with open("data/wikidataSignificantPaintersTicket1527.json", encoding="UTF-8") as fListTypes:
    types = json.load(fListTypes)
    for p in types:
        print(p["entity"], " ", p["entityLabel"])
        try:
            qid = p["entity"].replace("http://www.wikidata.org/entity/", "")
            if not qid in filterEntities:
                continue
            filename = "pages/creator/fr/{qid}.wp".format(qid=str(qid))
            with open(filename, "x", encoding="utf-8") as fpage:
                page = pbTypeFr.build_scrutart_page(qid)
                page = pbTypeFr.nettoyageContenu(page)
                fpage.write(page)
                time.sleep(3)
        except Exception as e: # file already exist or other error
            print(e)
            print("possibly a file already exists for ", qid)
        pass
""" voir ticket 1527 pour un peu mieux identifier les candidats
requête pour identifier des artistes candidats

select ?s (count(?oeuvre) as ?c) 
where 
{
  ?s wdt:P106 wd:Q1028181 .
  ?oeuvre wdt:P170 ?s
}
group by ?s
order by desc(?c)
#having(?c>500)
"""
"""
faire des billets sur la présence des mouvements picturaux dans Wikidata
"""
