# tests/test_retry_validation.py
import unittest
import unittest.mock
import time
from src.generationWordpress.tools.WikimediaManager.WikimediaManagerPackage.WikimediaAccess import WikimediaAccess
from src.generationWordpress.tools.WikimediaManager.WikimediaManagerPackage.exceptions import ValidationError, NetworkError
import requests.exceptions


class TestRetryValidation(unittest.TestCase):

    def test_qid_validation(self):
        """Test de validation des QIDs"""
        from src.generationWordpress.tools.WikimediaManager.WikimediaManagerPackage.validators import WikidataValidator

        # QIDs valides
        self.assertEqual(WikidataValidator.validate_qid("Q762"), "Q762")
        self.assertEqual(WikidataValidator.validate_qid("762"), "Q762")
        self.assertEqual(WikidataValidator.validate_qid("q123"), "Q123")

        # QIDs invalides
        with self.assertRaises(ValidationError):
            WikidataValidator.validate_qid("")

        with self.assertRaises(ValidationError):
            WikidataValidator.validate_qid("ABC123")

    def test_retry_mechanism(self):
        """Test du mécanisme de retry"""

        # Simuler des erreurs réseau transitoires
        call_count = 0

        def mock_sparql_query(query):
            nonlocal call_count
            call_count += 1

            if call_count <= 2:  # Échouer 2 fois
                raise requests.exceptions.ConnectionError("Connection failed")
            else:  # Réussir la 3ème fois
                return {"results": {"bindings": [{"type": {"value": "http://www.wikidata.org/entity/Q5"}}]}}

        with WikimediaAccess("Q762") as wma:
            # Mock la méthode sparqlQuery
            with unittest.mock.patch.object(wma, 'sparqlQuery', side_effect=mock_sparql_query):
                start_time = time.time()
                types = wma.getTypes()
                duration = time.time() - start_time

                # Vérifier qu'on a bien retryé
                self.assertEqual(call_count, 3)
                self.assertGreater(duration, 1.5)  # Au moins 1.5s à cause des backoffs
                self.assertEqual(types, ["Q5"])

    def test_no_retry_on_validation_error(self):
        """Vérifier qu'on ne retry pas sur les erreurs de validation"""

        call_count = 0

        def mock_sparql_query(query):
            nonlocal call_count
            call_count += 1
            return {"results": {"bindings": []}}

        with WikimediaAccess("Q762") as wma:
            with unittest.mock.patch.object(wma, 'sparqlQuery', side_effect=mock_sparql_query):
                # Erreur de validation - ne doit pas retry
                with self.assertRaises(ValidationError):
                    wma.getTypes("")  # QID vide

                # Vérifier qu'on n'a pas appelé sparqlQuery
                self.assertEqual(call_count, 0)


if __name__ == "__main__":
    unittest.main()