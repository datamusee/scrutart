import unittest
import PageBuilder as PageBuilder

class TestGenreBuilder(unittest.TestCase):
    def test_genre_portrait(self):
        qid = "Q134307"
        # create PageBuilder
        pbGenreFr = PageBuilder.PageBuilder("Q1792379") # genre, default lang fr
        page = pbGenreFr.build_scrutart_page("Q134307") # portrait
        pass
        self.assertTrue("""{ "qid": "Q134307", "templateVersion": "1.0.2" }""" in page)

if __name__=='__main__':
    unittest.main()
