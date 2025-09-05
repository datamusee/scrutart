import SPARQLWrapper as sw

@dataclass
class Artist:
    pass

@dataclass
class Work:
    pass

@dataclass
class Museum:
    pass

@dataclass
class Gallery:
    pass

@dataclass
class Exhibition:
    pass

class scrutartStateManager():
    def __init__(self, urlendpoint):
        self.urlendpoint = urlendpoint
        check = self.checkIfSparqlScrutartStateEndpointIsAvailable(urlendpoint)
        pass

    def checkIfSparqlScrutartStateEndpointIsAvailable(self, urlendpoint):
        query = """select distinct ?s            where {              ?s ?p ?o            } LIMIT 1        """
        sparqlScrutartWrapper = sw.SPARQLWrapper2(urlendpoint)  # implicit JSON format
        sparqlScrutartWrapper.setQuery(query)
        try:
            res = sparqlScrutartWrapper.queryAndConvert()
            return True if res and res.bindings else False
        except Exception as e:
            print(
                    f"le serveur scrutart state (au 12/2/2025, {urlendpoint} (D:\Outils\Semantic/apache-jena-fuseki-4.8.0/fuseki-server) doit avoir été lancé avant de lancer cette application")
            exit(7777)
            return False
