# ============================================================================
# core/sparql_client.py - Client SPARQL
# ============================================================================

"""
Client pour interagir avec l'endpoint SPARQL
"""

from SPARQLWrapper import SPARQLWrapper, JSON, POST
from typing import List, Dict


class SPARQLClient:
    """Client pour interagir avec l'endpoint SPARQL"""

    def __init__(self, endpoint: str, update_endpoint: str, cache_manager=None):
        self.endpoint = endpoint
        self.update_endpoint = update_endpoint
        self.cache_manager = cache_manager

    def query(self, sparql_query: str, use_cache: bool = False) -> List[Dict]:
        """Exécute une requête SPARQL SELECT"""
        if use_cache and self.cache_manager:
            cached = self.cache_manager.get(sparql_query, 'sparql')
            if cached:
                return cached

        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)

        results = sparql.query().convert()
        bindings = results['results']['bindings']

        # Convertir en format simplifié
        simplified = []
        for binding in bindings:
            row = {}
            for key, value in binding.items():
                row[key] = value['value']
            simplified.append(row)

        if use_cache and self.cache_manager:
            self.cache_manager.set(sparql_query, simplified, 'sparql')

        return simplified

    def ask(self, sparql_query: str, use_cache: bool = False) -> List[Dict]:
        """Exécute une requête SPARQL SELECT"""
        if use_cache and self.cache_manager:
            cached = self.cache_manager.get(sparql_query, 'sparql')
            if cached:
                return cached

        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)

        results = sparql.query().convert()
        val = results['boolean']

        if use_cache and self.cache_manager:
            self.cache_manager.set(sparql_query, val, 'sparql')

        return val

    def update(self, sparql_update: str):
        """Exécute une requête SPARQL UPDATE"""
        sparql = SPARQLWrapper(self.update_endpoint)
        sparql.setQuery(sparql_update)
        sparql.method = POST
        sparql.query()

    def get_all_named_graphs(self) -> List[str]:
        """Récupère tous les graphes nommés"""
        query = "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }"
        results = self.query(query)
        return [r['g'] for r in results]

