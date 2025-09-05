# tests/test_current_functionality.py
import unittest
from src.generationWordpress.tools.WikimediaManager.WikimediaManagerPackage.WikimediaAccess import WikimediaAccess

class TestCurrentFunctionality(unittest.TestCase):
    def test_basic_functionality(self):
        """Test que l'existant fonctionne avant migration"""
        try:
            with WikimediaAccess("Q762") as wma:
                occupations = wma.getOccupations("Q762")
                self.assertIsInstance(occupations, list)
                print(f"✅ Test réussi: {len(occupations)} occupations trouvées")
        except Exception as e:
            self.fail(f"Test existant échoué: {e}")

if __name__ == "__main__":
    unittest.main()