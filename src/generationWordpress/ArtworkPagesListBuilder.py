from PagesListBuilder import PagesListBuilder

class ArtworkPagesListBuilder(PagesListBuilder):
    def __init__(self):
        pass

    def build(self, buildParams):
        pagesList = []
        titre = "Test de page 1"
        page = {}
        page["title"] = titre
        pagesList.append(page)
        return pagesList
