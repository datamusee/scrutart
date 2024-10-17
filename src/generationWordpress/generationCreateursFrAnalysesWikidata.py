# but: générer des contenus prêts à être intégrés dans un wordpress
# part d'un template basé sur le billet
# https://datamusee.wp.imt.fr/fr/2024/01/12/paul-gauguin-dans-wikidata/
# récupération de la source de cette page comme base de template
import time
import json
import os
import configPrivee
from wikidataObject import WikidataObject
#from dataConfig import dataConfig
from WPPainterFrenchTemplate import WPPainterFrenchTemplate as WPFrTemplate
from WPTools import WPTools

def getTemplate(oType, lang="fr"):
    template = None
    if oType:
        templates = {
            "fr": {
                "Q1028181": WPFrTemplate(),
            },
            "en": {},
        }
        if templates[lang]:
            template = templates[lang].get(oType, None)
    return template

# fonction destinée à généraliser et remplacer la fonction ci-dessous buildScrutartArtistPage
def buildScrutartPage(qid, lang="fr"):
    wObj = WikidataObject(qid)
    objectTypes = wObj.getTypes(qid)
    if objectTypes and objectTypes[0]=="Q5":
        objectTypes[0] = "Q1028181" # artiste peintre # il faudrait aller chercher son occupation P106
    tManager = getTemplate(objectTypes[0])
    page = None
    if tManager:
        page = tManager.buildPageTemplate()
    if page:
        # liste de requêtes sparql utiles pour construire une page
        sparqlList = tManager.getDataConfig()
        for name, elmt in sparqlList.items():
            filtres = elmt["filtres"]
            urlqueryref = elmt["urlquery"]
            # recuperation d'une query pour avoir les données du QID liées à l'item 'name'
            crtquery = elmt["sparql"].replace("__QID__", qid).replace("__LANG__", lang) if elmt["sparql"] else None
            if crtquery:
                res = wObj.sparqlQuery(crtquery)
                # recuperation d'un lien vers WDQS pour la query courante
                wdqsquery = wObj.getWDQSQuery(crtquery)
                # recuperation d'un lien d'affichage de bargraph pour la query courante
                embedquery = wObj.getWikidataBarGraph(crtquery, qid)
            else:
                res = None
                wdqsquery = None
                embedquery = None
            for filtrage in filtres:
                if filtrage["filtre"]:
                    fct = wObj.getWObjFct(filtrage["filtre"])
                    if fct:
                        output = fct(wObj, res, qid)
                        page = page.replace(filtrage["key"], str(output))
                else:
                    page = page.replace(filtrage["key"], embedquery) # hack
            if wdqsquery and urlqueryref:
                page = page.replace(urlqueryref, wdqsquery)
            time.sleep(0.2)
    return page


# page = getWordPressPage("Q37693") # fait à la main Gauguin
#page = getWordPressPage("Q5580")  # Dürer planifié le 18/1/2024 vers 16h
#page = getWordPressPage("Q5582") # Van Gogh planifié le 19/1/2024 vers 16h
#page = getWordPressPage("Q468453")  # Lurçat
#page = getWordPressPage("Q26408")  # Bonnard planifié le 22/1/2024 vers 23h
#page = getWordPressPage("Q83155")  # David planifié le 23/1/2024 vers 23h
#page = getWordPressPage("Q1470")  # Escher planifié le 24/1/2024 vers 23h
#page = getWordPressPage("Q47551")  # Le Titien planifié le 25/1/2024 vers 23h
#page = getWordPressPage("Q159758")  # Turner planifié le 26/1/2024 vers 23h
# qid = "Q241732" # Rosa Bonheur  planifié le 27/1/2024 vers 23h
# qid = "Q22334076" # Marianne van der Heijden non planifiée
#qid = "Q11787765" # Mária Medvecká
#qid = "Q3348980" # Nandalal Bose planifié le 27/1/2024 vers 14h
#qid = "Q187506" # Honoré Daumier

def nettoyageContenu(page):
    if "<p><strong>0 pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>" in page:
        page = page.replace(
            "<p><strong>0 pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>",
            "<p>Je n'ai trouvé aucune page dans Wikipedia associée à ces oeuvres</p>")
        page = page.replace("<p>Dont 0 dans le Wikipedia anglophone et 0 dans le Wikidata francophone.</p>",
                     "<p>Et bien sûr, il n'y a de page pour ces oeuvres ni dans le Wikipedia francophone, ni dans l'anglophone</p>")
        page = page.replace("<p>L'ensemble des <strong>pages</strong> concerne <strong>0 œuvres</strong>.</p>",
                     "<p>Et aussi, aucune de ces oeuvres n'est concernée par une page de Wikipedia.</p>")
    if "<p>Il y a <strong>0 images</strong> dans Wikimedia Commons associées à ces œuvres.</p>" in page:
        page = page.replace("<p>Il y a <strong>0 images</strong> dans Wikimedia Commons associées à ces œuvres.</p>",
                     "<p>Il n'a aucune image dans Wikimedia Commons associée à ces oeuvres.</p>")
        pass
    return page

# test recup link WP en vue crosslink entre pages WP
# attention ne marche pas si la page n'est pas déjà créée
# est-ce que ça marche si elle est en mode brouillon
wpt = WPTools(configPrivee)
link = wpt.getWPLink("Où trouver Honoré Daumier dans Wikidata, suivez le guide")
link = wpt.getWPLink("Test brouillon")

# ne traiter que ceux qui sont dans filterpainters en supprimant la page si elle existe déjà
filterPainters = [
"Q10378200",
"Q1074290",
"Q1389068",
"Q151679",
"Q153793",
"Q153920",
"Q154349",
"Q155057",
"Q159758",
"Q170071",
"Q186202",
"Q187506",
"Q1948973",
"Q239394",
"Q2614892",
"Q26408",
"Q289441",
"Q316307",
"Q35548",
"Q40599",
"Q435316",
"Q460124",
"Q46373",
"Q518406",
"Q531234",
"Q5432",
"Q544899",
"Q5577",
"Q5580",
"Q5582",
"Q5589",
"Q5593",
"Q560115",
"Q562540",
"Q93284",
"Q979534",
]
#filterPainters = [
#    "Q9440", # Paul Véronèse    "Q274901", # Carolus-Duran,    "Q47842", # CIxi    #"Q920924", # munch    #"Q706359" # Auguste Herbin]
#filterPainters = ["Q10378200","Q1074290","Q1389068",]
filelist = os.listdir("./pages")
for qid in filterPainters:
    if "{qid}.wp".format(qid=qid) in filelist:
        os.remove("pages/{qid}.wp".format(qid=qid))

#page = "test"
with open("data/wikidataSignificantPaintersTicket1527.json") as fListPainters:
    painters = json.load(fListPainters)
    # commentaire de version temporaire->
    # painters = [{"painter":"http://www.wikidata.org/entity/Q274901","painterLabel":"Carolus-Duran","c":"52"}    ]
    # painters = [{"painter":"http://www.wikidata.org/entity/Q9440","painterLabel":"Paul Véronèse" }    ]
    # painters = [{"painter":"http://www.wikidata.org/entity/Q47842","painterLabel":"Cixi" }    ]
    for p in painters:
        print(p["painter"], " ", p["painterLabel"])
        try:
            qid = p["painter"].replace("http://www.wikidata.org/entity/", "")
            if not qid in filterPainters:
                continue
            filename = "pages/{qid}.wp".format(qid=str(qid))
            with open(filename, "x", encoding="utf-8") as fpage:
                page = buildScrutartPage(qid)
                page = nettoyageContenu(page)
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
