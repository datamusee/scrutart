# voir fichier automateGenerationScrutart.py
import ArtistPagesListBuilder

def buildPageListToBuild(buildParams):
    plb = ArtistPagesListBuilder.ArtistPagesListBuilder()
    pagesList = plb.build(buildParams)
    return pagesList

def isPageInWP(page, wpref):
    isInWP = True # default True to avoid injection of page
    return isInWP

def checkPageState(checkParams):
    wpref = checkParams["wpref"] if "wpref"in checkParams else None
    pagesList = checkParams["pagesList"]
    for page in pagesList:
        if (not "check" in page) or (not page["check"]):
            page["check"] = isPageInWP(page, wpref)
    return { "wpref": wpref, "pagesList": pagesList }

def generatePage(page, template):
    pageID = ""
    pageTitle = template.buildTitre(page["mainSubject"])
    pageContent = ""
    return pageID, pageTitle, pageContent

def generatePage(pageParams, template):
    wpref = pageParams["wpref"] if "wpref" in pageParams else None
    pagesList = pageParams["pagesList"]
    for index, pageDescription in enumerate(pagesList):
        if (not "check" in pageDescription) or (not pageDescription["check"]):
            pagesList[index]["id"], pagesList[index]["title"], pagesList[index]["content"] = generatePage(pageDescription, template)
    return { "wpref": wpref, "pagesList": pagesList }

def getWPPageDescription(pagedesc, wpref):
    pageID = ""
    pageTitle = ""
    pageContent = ""
    pageGalery = ""
    return  { "id": pageID, "title": pageTitle, "content": pageContent, "galery": pageGalery }

def getPageContent(pagesParams):
    wpref = pagesParams["wpref"] if "wpref" in pagesParams else None
    pagesList = pagesParams["pagesList"]
    for index, pageDescription in enumerate(pagesList):
        if ("check" in pageDescription) and (pageDescription["check"]):
            pagesList[index] = getWPPageDescription(pageDescription, wpref)
    return { "wpref": wpref, "pagesList": pagesList }

def putPageInGit(gitref, pagesdesc):
    return False

def putPageInWP(wpref, pagedesc):
    return False

def createMinimalPage(wpref, pagedesc):
    wpPageId = None
    return wpPageId

def existingPage(wpref, pagedesc):
    return True

def hasFeaturedImage(wpref, pagedesc):
    return True

def injectFeaturedImage(wpref, wpageid, urlImage=""):
    if urlImage:
        pass

def pageProcess(pagedesc, wpref, template):
    checkParams = {"wpref": wpref, "pagedesc": pagedesc}
    checkedPagesList = checkPageState(checkParams)

    # récupération du contenu des pages qui existent déjà
    existingPageContent = getPageContent(pagedesc)

    # mettre dans git le contenu des pages qui existent déjà
    putPageInGit(existingPageContent, gitref)

    # générer les nouvelles versions des pages
    pageContent = generatePage(pagedesc, frenchtemplate)

    if not existingPage(wpref, pagedesc):
        wpageid = createMinimalPage(wpref, pagedesc)
    if not hasFeaturedImage(wpref, pagedesc):
        injectFeaturedImage(wpref, wpageid)

    # mettre les pages générées dans le wordpress
    putPageInWP(pageContent, wpref)

    # mettre les pages générées dans le git
    putPageInGit(pageContent, gitref)
    pass

if __name__ == '__main__':
    import WPPainterTemplate as wpTemplate

    # chargement de template de page à appliquer
    frenchtemplate = wpTemplate.WPPainterTemplate("fr")
    gitref = None
    wpref = None
    jsonParams = {}

    # construction d'une liste de pages à générer; par exemple, liste de créateurs avec + de x créations ds wikidata
    pagesList = buildPageListToBuild(jsonParams)

    for pagedesc in pagesList:
        pageProcess(pagedesc, wpref, frenchtemplate)
