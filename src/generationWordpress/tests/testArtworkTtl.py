import unittest
from src.generationWordpress.CScrutartState import CScrutartState, DCPiwigoArtwork, DCWikidataCreator, DCLangLabel, DCImage
class TestArtworkTtl(unittest.TestCase):
    def sampleArtwork(self):
        artwork = DCPiwigoArtwork(
            uri="http://www.wikidata.org/entity/Q328523", # impression soleil levant
            creators= [ DCWikidataCreator(uri="http://www.wikidata.org/entity/Q296", labels=[DCLangLabel(label="Claude Monet", lang="fr")])],
            labels=[DCLangLabel(label="Impression, soleil levant", lang="fr")],
            images=[DCImage(url="https://commons.wikimedia.org/wiki/File:Monet_-_Impression,_Sunrise.jpg")],
            sparqlSrc= "select * where { ?s ?p ?o } limit 1",
            wtypes= ["Q838948"] # oeuvre d'art
        )
        return artwork

    def test_artwork_to_ttl(self):
        ttl = self.sampleArtwork().toTtl()
        self.assertTrue("""wd:Q328523 rdfs:label """ in ttl)
        self.assertTrue("Claude Monet" in ttl)
        self.assertTrue("wd:Q328523 wdt:P31 wd:Q838948 ." in ttl)
        self.assertTrue("wd:Q328523 wdt:P170 wd:Q296." in ttl)
        self.assertTrue("wd:Q296 rdfs:label " in ttl)
        self.assertTrue("wd:Q296 wdt:P31 wd:Q3391743 ." in ttl)
        self.assertTrue("""wd:Q328523 wdt:P18 "https://commons.wikimedia.org/wiki/File:Monet_-_Impression,_Sunrise.jpg".""" in ttl)
        self.assertTrue("""kgdc:sparqlQHpbzfvoXg0rNInANqBRxcO0YJsM1xo2Lg2mNIadj84 pgdc:sparql_src """ in ttl)
        self.assertTrue("""select * where { ?s ?p ?o } limit 1""" in ttl)

    def test_artwork_ttl_to_endpoint(self):
        st = CScrutartState()
        response = st.putArtwork(self.sampleArtwork())
        assert(response.status_code in (200, 204))

if __name__=='__main__':
    unittest.main()
