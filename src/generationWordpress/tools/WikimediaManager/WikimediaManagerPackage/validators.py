# WikimediaManagerPackage/validators.py
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

# WikimediaManagerPackage/validators.py
import re
import logging
from typing import Any, List, Optional
from .exceptions import ValidationError


class WikidataValidator:
    """Validateur pour les données Wikidata"""

    @staticmethod
    def validate_qid(qid: str, allow_none: bool = False) -> str:
        """Valide et normalise un QID Wikidata"""
        logger = logging.getLogger('WikimediaAccess')

        if qid is None and allow_none:
            return None

        if not qid or not str(qid).strip():
            raise ValidationError("QID vide ou None", {'qid': qid})

        # Normaliser
        qid = str(qid).strip().upper()
        if not qid.startswith('Q'):
            if qid.isdigit():
                qid = 'Q' + qid
            else:
                raise ValidationError(f"Format QID invalide: {qid}", {'qid': qid})

        # Validation format Q[digits]
        if not re.match(r'^Q\d+$', qid):
            raise ValidationError(f"Format QID invalide: {qid}", {'qid': qid})

        # Validation range (QIDs trop élevés sont suspects)
        qid_number = int(qid[1:])
        if qid_number > 200000000:  # Ajuster selon les besoins
            logger.warning(f"QID très élevé, possiblement invalide: {qid}")

        logger.debug(f"QID validé: {qid}")
        return qid

    @staticmethod
    def validate_sparql_response(response: Any, expected_fields: List[str] = None) -> bool:
        """Valide la structure d'une réponse SPARQL"""
        logger = logging.getLogger('WikimediaAccess')

        if not response:
            logger.warning("Réponse SPARQL vide")
            return False

        # Validation structure dict
        if isinstance(response, dict):
            if "results" not in response:
                logger.warning("Clé 'results' manquante dans réponse SPARQL")
                return False
            if "bindings" not in response["results"]:
                logger.warning("Clé 'bindings' manquante dans results SPARQL")
                return False

            bindings = response["results"]["bindings"]

        # Validation structure SPARQLWrapper
        elif hasattr(response, "bindings"):
            bindings = response.bindings

        else:
            logger.warning(f"Type de réponse SPARQL non reconnu: {type(response)}")
            return False

        # Validation champs attendus
        if expected_fields and bindings:
            first_binding = bindings[0] if isinstance(bindings, list) else bindings[0] if hasattr(bindings,
                                                                                                  '__iter__') else None

            if first_binding:
                if isinstance(first_binding, dict):
                    missing_fields = [field for field in expected_fields if field not in first_binding]
                else:
                    missing_fields = [field for field in expected_fields if not hasattr(first_binding, field)]

                if missing_fields:
                    logger.warning(f"Champs manquants dans réponse SPARQL: {missing_fields}")
                    return False

        logger.debug("Validation réponse SPARQL réussie")
        return True