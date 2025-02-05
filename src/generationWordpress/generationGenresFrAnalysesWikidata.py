# but: générer des contenus prêts à être intégrés dans un wordpress
# part d'un template basé sur le billet
# https://datamusee.wp.imt.fr/fr/2024/01/12/paul-gauguin-dans-wikidata/
# récupération de la source de cette page comme base de template
# ce code source est copiée de generationWordpress\generationCreateursFrAnalysesWikidata.py
# et modifié pour traiter des genres au lieu des créateurs
# cela nécessite notamment de modifier le template
# il parait souhaitable d'homogénéiser le code pour les différentes langues et les différents thèmes
# dans le cas des créateurs, on a relativement peu d'instances d'œuvres et pas rencontré de timeout
# dans le cas des genre, il arrive qu'il y ait des timeout
# il en résulte la nécessité d'adapter les requêtes sparql pour éviter les timeout
# par exemple pour le genre portrait, en limitant à la recherche des propriétés sur 50000 œuvres
# on n'a pas de timeout, alors qu'avec le compte complet de plus de 100000 œuvres, on a des timeout
import datetime
import time
import json
import os
import src.generationWordpress.PageBuilder as PageBuilder

# ne traiter que ceux qui sont dans filterEntities en supprimant la page si elle existe déjà
filterEntities = [
    "Q134307" # portrait
]
filelist = os.listdir("./pages/genre/fr")
for qid in filterEntities:
    if "{qid}.wp".format(qid=qid) in filelist:
        os.remove("pages/genre/fr/{qid}.wp".format(qid=qid))

pbTypeFr = PageBuilder.PageBuilder("Q1028181")  # type=genre, default lang fr
with open("data/GenresWikidataPlusde10Peintures.json", encoding="UTF-8") as fListType:
    types = json.load(fListType)
    for p in types:
        print(p["entity"], " ", p["entityLabel"])
        try:
            qid = p["entity"].replace("http://www.wikidata.org/entity/", "")
            if not qid in filterEntities:
                continue
            filename = "pages/genre/fr/{qid}.wp".format(qid=str(qid))
            with open(filename, "x", encoding="utf-8") as fpage:
                page = pbTypeFr.build_scrutart_page(qid)
                page = pbTypeFr.nettoyageContenu(page)
                fpage.write(page)
                time.sleep(3)
        except Exception as e: # file already exist or other error
            print(e)
            print("error; possibly a file already exists for ", qid)
        pass
