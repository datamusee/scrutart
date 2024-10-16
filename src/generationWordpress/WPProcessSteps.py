# voir fichier automateGenerationScrutart.py
import ArtistPagesListBuilder

def buildPagesListToGenerate(buildParams):
    plb = ArtistPagesListBuilder.ArtistPagesListBuilder()
    pagesList = plb.build(buildParams)
    return pagesList

def isPageInWP(page, wpref):
    isInWP = True # default True to avoid injection of page
    return isInWP

def checkPagesListState(checkParams):
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

def generatePages(pagesParams, template):
    wpref = pagesParams["wpref"] if "wpref"in pagesParams else None
    pagesList = pagesParams["pagesList"]
    for index, pageDescription in enumerate(pagesList):
        if (not "check" in pageDescription) or (not pageDescription["check"]):
            pagesList[index]["id"], pagesList[index]["title"], pagesList[index]["content"] = generatePage(pageDescription, template)
    return { "wpref": wpref, "pagesList": pagesList }

def getWPPageContent(pagedesc, wpref):
    pageID = ""
    pageTitle = ""
    pageContent = ""
    return pageID, pageTitle, pageContent

def getPagesListContents(pagesParams):
    wpref = pagesParams["wpref"] if "wpref" in pagesParams else None
    pagesList = pagesParams["pagesList"]
    for index, pageDescription in enumerate(pagesList):
        if ("check" in pageDescription) and (pageDescription["check"]):
            pagesList[index]["id"], pagesList[index]["title"], pagesList[index]["content"] = getWPPageContent(pageDescription, wpref)
    return { "wpref": wpref, "pagesList": pagesList }

def putPagesInGit(pagesList, gitref):
    pass

def putPagesInWP(pagesList, wpref):
    pass


if __name__ == '__main__':
    import WPPainterFrenchTemplate as wpFrenchTemplate
    frenchtemplate = wpFrenchTemplate.WPPainterFrenchTemplate()
    gitref = None
    wpref = None
    jsonParams = {}
    pagesList = buildPagesListToGenerate(jsonParams)
    checkParams = { "wpref": wpref, "pagesList": pagesList }
    checkedPagesList = checkPagesListState(checkParams)
    existingPagesListContents = getPagesListContents(checkedPagesList)
    putPagesInGit(existingPagesListContents, gitref)
    pagesListContents = generatePages(existingPagesListContents, frenchtemplate)
    putPagesInWP(pagesListContents, wpref)
    putPagesInGit(pagesListContents, gitref)
    pass