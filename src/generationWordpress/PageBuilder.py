import datetime
import time
import json
from src.generationWordpress.WPGenreTemplate import WPGenreTemplate as WPGenreTemplate
from src.generationWordpress.WPPainterTemplate import WPPainterTemplate as WPPainterTemplate
from src.generationWordpress.WikimediaAccess import WikimediaAccess

# il parait souhaitable d'homogénéiser ici le code pour les différentes langues et les différents thèmes
# dans le cas des créateurs, on a relativement peu d'instances d'œuvres et pas rencontré de timeout
class PageBuilder:
    def __init__(self, o_type, lang="fr"):
        self.objectType = o_type
        self.lang = lang
        self.template_builder = None
        if self.objectType:
            templates = {
                "Q1028181": WPPainterTemplate(lang),  # template pour page de peintre
                "Q1792379": WPGenreTemplate,  # template pour page de genre
            }
            self.template_builder = templates.get(self.objectType, None)
            if self.template_builder:
                self.template_manager = self.template_builder
            if self.template_manager:
                self.template = self.template_manager.buildPageTemplate()
        pass

    def check_object_type(self, w_obj):
        object_types = w_obj.getTypes(w_obj.qid)
        if object_types and object_types[0] == "Q5":
            object_types[0] = "Q1028181"  # artiste peintre # il faudrait aller chercher son occupation P106
        res = False
        if len(object_types):
            res = object_types[0] == self.objectType
        return res

    # fonction destinée à généraliser et remplacer la fonction ci-dessous buildScrutartArtistPage
    def build_scrutart_page(self, qid):
        page = None
        wAccess = WikimediaAccess(qid, lang=self.lang)
        with  wAccess as w_obj:
            check = self.check_object_type(w_obj)
            page = self.template
            if page:
                # liste de requêtes sparql utiles pour construire une page
                sparql_list = self.template_manager.getDataConfig()
                for name, elmt in sparql_list.items():
                    print(name, elmt)
                    filtres = elmt["filtres"]
                    urlqueryref = elmt["urlquery"]
                    # recuperation d'une query pour avoir les données du QID liées à l'item 'name'
                    crtquery = elmt["sparql"].replace("__QID__", qid).replace("__LANG__", self.lang) if elmt["sparql"] else None
                    if crtquery:
                        res = w_obj.sparqlQuery(crtquery)
                        print(crtquery, datetime.datetime.now())
                        # recuperation d'un lien vers WDQS pour la query courante
                        wdqsquery = w_obj.getWDQSQuery(crtquery)
                        # recuperation d'un lien d'affichage de bargraph pour la query courante
                        embedquery = w_obj.getWikidataBarGraph(crtquery, qid)
                    else:
                        res = None
                        wdqsquery = None
                        embedquery = None
                    for filtrage in filtres:
                        if filtrage["filtre"]:
                            fct = w_obj.getWObjFct(filtrage["filtre"])
                            if fct:
                                output = fct(w_obj, res, qid)
                                page = page.replace(filtrage["key"], str(output))
                        else:
                            page = page.replace(filtrage["key"], embedquery)  # hack
                    if wdqsquery and urlqueryref:
                        page = page.replace(urlqueryref, wdqsquery)
                    time.sleep(0.2)
        return page

    def generatePage(self, qid, targetDir):
        # en faire un log print(p["entity"], " ", p["entityLabel"])
        try:
            page = self.build_scrutart_page(qid)
            page = self.nettoyageContenu(page)
            if targetDir:
                filename = f"""{targetDir}/{qid}.wp"""
                with open(filename, "x", encoding="utf-8") as fpage:
                    fpage.write(page)
                    # time.sleep(3)
            else:
                return page
        except Exception as e:  # file already exist or other error
            print(e)
            print("possibly a file already exists for ", qid)
        pass

    def nettoyageContenu(self, page):
        if "<p><strong>0 pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>" in page:
            page = page.replace(
                "<p><strong>0 pages</strong> d'un <strong>Wikipedia</strong> dans au moins une langue sont associées à ces œuvres.</p>",
                "<p>Je n'ai trouvé aucune page dans Wikipedia associée à ces œuvres</p>")
            page = page.replace("<p>Dont 0 dans le Wikipedia anglophone et 0 dans le Wikidata francophone.</p>",
                         "<p>Et bien sûr, il n'y a de page pour ces œuvres ni dans le Wikipedia francophone, ni dans l'anglophone</p>")
            page = page.replace("<p>L'ensemble des <strong>pages</strong> concerne <strong>0 œuvres</strong>.</p>",
                         "<p>Et aussi, aucune de ces œuvres n'est concernée par une page de Wikipedia.</p>")
        if "<p>Il y a <strong>0 images</strong> dans Wikimedia Commons associées à ces œuvres.</p>" in page:
            page = page.replace("<p>Il y a <strong>0 images</strong> dans Wikimedia Commons associées à ces œuvres.</p>",
                         "<p>Il n'a aucune image dans Wikimedia Commons associée à ces œuvres.</p>")
            pass
        if "On peut voir une sélection de ces œuvres dans . (vous avez plus de possibilités de réglages sur la galerie si vous vous inscrivez comme utilisateur)." in page:
            page = page.replace("On peut voir une sélection de ces œuvres dans . (vous avez plus de possibilités de réglages sur la galerie si vous vous inscrivez comme utilisateur).", "")
        # gestion de pluriels spécifiques
        page = page.replace("série de peinturess", "séries de peintures")
        page = page.replace("œuvre d'arts", "œuvres d'art")
        page = page.replace("pièce de monnaies", "pièces de monnaie")
        page = page.replace("rouleau suspendus", "rouleaux suspendus")
        page = page.replace("photo-carte de visites", "photo-cartes de visite")
        page = page.replace("film négatifs", "films négatifs")
        page = page.replace("série de peinturess", "séries de peintures")
        page = page.replace("eau-fortes", "eaux-fortes")
        page = page.replace("carte postales", "cartes postales")
        page = page.replace("œuvre inachevées", "œuvres inachevées")
        page = page.replace("plaque commémoratives", "plaques commémoratives")
        page = page.replace("élément d’une collection ou d’une expositions", "éléments d’une collection ou d’une exposition")
        page = page.replace("carreaus", "carreaux")
        page = page.replace("peinture sur panneaus", "peintures sur panneau")
        page = page.replace("estampe à la manière noires", "estampes à la manière noire")
        page = page.replace("peinture murales", "peintures murales")
        page = page.replace("groupe de peinturess", "groupes de peintures")
        page = page.replace("aureuss", "aurei")
        page = page.replace("artefact archéologiques", "artefacts archéologiques")
        page = page.replace("impression photomécaniques", "impressions photomécaniques")
        page = page.replace("œuvre avec de multiples exécutionss", "œuvres avec de multiples exécutions")
        return page

