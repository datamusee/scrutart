# WikimediaManagerPackage/exceptions.py
import datetime
from typing import Dict, Any

class WikimediaAccessError(Exception):
    """Exception de base pour WikimediaAccess"""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        super().__init__(message)
        self.context = context or {}
        self.timestamp = datetime.datetime.now()
        self.error_id = str(uuid.uuid4())[:8]

class SPARQLQueryError(WikimediaAccessError):
    """Erreur lors de l'exécution d'une requête SPARQL"""
    pass

class NetworkError(WikimediaAccessError):
    """Erreur réseau/connectivité"""
    pass

class ValidationError(WikimediaAccessError):
    """Erreur de validation des données"""
    pass

class APIManagerError(WikimediaAccessError):
    """Erreur liée à l'API Manager"""
    pass