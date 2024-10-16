from PagesListBuilder import PagesListBuilder

# but: outil pour construire des pages wordpress qui récapitulent des liens vers des pages sur un sujet donné
class ArtistPagesListBuilder(PagesListBuilder):
    def __init__(self):
        pass

    def build(self, buildParams):
        pagesList = []
        name = "Picasso"
        page = {}
        page["mainSubject"] = name
        pagesList.append(page)
        return pagesList
