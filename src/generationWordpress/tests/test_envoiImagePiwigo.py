import sys
import os

# sys.path.insert(0, os.path.abspath('D:/wamp64/www/givingsense.eu/src/piwigoTools'))

from unittest import TestCase
from envoiImagePiwigo import postImageToPiwigo
import configPiwigo as cp


class Test(TestCase):
    def test_post_image_to_piwigo(self):
        im = {
      "uri": "http://www.wikidata.org/entity/Q15874516",
      "createur": "http://www.wikidata.org/entity/Q45006",
      "createurLabel": "Tests",
      "titre_fr": "Chat2",
      "images": [
        "https://jardinage.lemonde.fr/images/dossiers/2017-10/chatte-155436.jpg"
      ]
        }
        res = postImageToPiwigo(im, piwigoCategory=852, categoryName="Tests", cp=cp)
        self.assertEqual(res.text, """{"stat":"ok","result":{"image_id":"18439","url":"https:\/\/galleries.grains-de-culture.fr\/picture.php?\/18439\/category\/852"}}""")
        pass
