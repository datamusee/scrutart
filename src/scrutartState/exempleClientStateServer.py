import requests
import json

# URL de l'API
API_URL = 'http://127.0.0.1:5000/query'
API_CONSTRUCT = 'http://127.0.0.1:5000/construct'
API_DESC = 'http://127.0.0.1:5000/describe'

# Token autorisé pour l'authentification
TOKEN = '4444 5555 6666 7777'  # Remplacez par un Token valide

# Requête SPARQL exemple
sparql_query = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            prefix wd: <http://www.wikidata.org/entity/> 
            prefix wdt: <http://www.wikidata.org/prop/direct/> 
            prefix pgdc: <https://kg.grains-de-culture.fr/prop/> 
            select distinct ?galery
            where {
              ?s wdt:P18 ?urlImage;
                 wdt:P170 ?qid;
                 pgdc:piwigo_gallery ?galery;
                 rdfs:label ?title .
                ?s pgdc:piwigo_image ?piwigoId .
                  filter not exists { ?s pgdc:piwigo_gallery <https://kg.grains-de-culture.fr/entity/galNone>}
            }
    """


# En-têtes de la requête
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {TOKEN}'
}


# Corps de la requête
data = {
    'query': sparql_query
}

try:
    # Envoie la requête POST à l'API
    response = requests.post(API_URL, headers=headers, json=data)


    # Vérifie le statut de la réponse
    if response.status_code == 200:
        #print("Réponse JSON-LD :")
        print(json.dumps(response.json(), indent=4, ensure_ascii=False))
    else:
        print(f"Erreur : {response.status_code}")
        print(response.json())


except Exception as e:
    print(f"Erreur de connexion : {e}")

sparql_construct = """
prefix wd: <http://www.wikidata.org/entity/> 
construct {  wd:Q134307 ?p ?o }
where { wd:Q134307 ?p ?o }
"""
data = {
    'query': sparql_construct
}
try:
    # Envoie la requête POST à l'API
    response = requests.post(API_CONSTRUCT, headers=headers, json=data)


    # Vérifie le statut de la réponse
    if response.status_code == 200:
        print("Réponse JSON-LD :")
        print(json.dumps(response.json(), indent=4, ensure_ascii=False))
    else:
        print(f"Erreur : {response.status_code}")
        print(response.json())


except Exception as e:
    print(f"Erreur de connexion : {e}")

sparql_describe = """
prefix wd: <http://www.wikidata.org/entity/> 
DESCRIBE wd:Q134307
"""
data = {
    'query': sparql_describe
}
try:
    # Envoie la requête POST à l'API
    response = requests.post(API_DESC, headers=headers, json=data)


    # Vérifie le statut de la réponse
    if response.status_code == 200:
        pass
        #print("Réponse JSON-LD :")
        #print(json.dumps(response.json(), indent=4, ensure_ascii=False))
    else:
        print(f"Erreur : {response.status_code}")
        print(response.json())


except Exception as e:
    print(f"Erreur de connexion : {e}")
