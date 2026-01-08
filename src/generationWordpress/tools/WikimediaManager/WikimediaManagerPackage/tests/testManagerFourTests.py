import unittest
import json
import time
import requests
from src.generationWordpress.tools.WikimediaManager.WikimediaManagerPackage.configPrivee import config
from urllib.parse import urlencode, urlunsplit

baseurl = "http://127.0.0.1:6000"

def createManager(targetUrls, bearer=None):
    data = {"api_patterns": targetUrls}
    headers = {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"} if bearer else {}
    # create manager
    resp = requests.post(f"{baseurl}/api/initialize", json=data, headers=headers)
    jsonrep = json.loads(resp.text)
    scheduler_id = jsonrep["scheduler_id"] if "scheduler_id" in jsonrep else None
    return scheduler_id

def deleteManager(scheduler_id, bearer=None):
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    url = f"{baseurl}/api/delete_scheduler"
    response = requests.delete(f"{url}?scheduler_id={scheduler_id}", headers=headers)
    ok = (response.status_code == 200)
    return ok

class MyTestCase(unittest.TestCase):
    def test_creation_destruction_manager_sans_token(self):
        query = "http://127.0.0.1:5000/mockapi/test"
        scheduler_id = createManager([query])
        self.assertEqual(scheduler_id, None, "échec de Manager créé")

    def test_creation_destruction_manager(self):
        bearer = config['admin']["Bearer"]
        query = "http://127.0.0.1:5000/mockapi/test"
        scheduler_id = createManager([query], bearer)
        ok = deleteManager(scheduler_id, bearer)
        self.assertEqual(ok, True, "échec de Manager créé, manager détruit")

    def test_un_appel_synchrone(self):
        bearer = config['admin']["Bearer"]
        headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
        query = "http://127.0.0.1:5000/mockapi/test"
        scheduler_id = createManager([query], bearer=bearer)
        
        # limit est le nombre d'appels par seconde pour ce manager
        data = {"scheduler_id": scheduler_id, "limit": 1}
        lim = requests.post(f"{baseurl}/api/set_rate_limit", json=data, headers=headers)
        
        cachedur = 60  # en secondes
        data = {
            "scheduler_id": scheduler_id,
            "url": query,
            "method": "GET",
            "cache_duration": cachedur,
        }
        
        # mise de la requête dans la file d'attente
        req = requests.post(f"{baseurl}/api/request", json=data, headers=headers)
        
        # 🔧 AMÉLIORATION: Gestion d'erreur pour le parsing JSON
        try:
            req_json = json.loads(req.text)
            if "uuid" not in req_json:
                print(f"❌ Erreur dans la réponse: {req.text}")
                self.fail(f"Pas d'UUID dans la réponse: {req_json}")
            
            uuidreq = req_json["uuid"]
            statusUrl = f"{baseurl}{req_json['status_url']}"
        except json.JSONDecodeError:
            print(f"❌ Réponse invalide: {req.text}")
            self.fail(f"Réponse JSON invalide: {req.text}")
        
        # 🔧 AMÉLIORATION: Limite pour éviter une boucle infinie
        max_attempts = 100
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            stat = requests.get(statusUrl, headers=headers)
            jstat = json.loads(stat.text)
            
            if "status" in jstat and jstat["status"] == "complete":
                rep = jstat["response"]
                break
            elif "status" in jstat and jstat["status"] == "pending":
                time.sleep(0.1)
            else:
                print(f"⚠️ Status inattendu: {jstat}")
                time.sleep(0.1)
        else:
            self.fail(f"Timeout après {max_attempts} tentatives")
        
        print(rep)
        ok = (stat.status_code == 200) and ("response" in jstat) and ("data" in jstat["response"])
        deleteManager(scheduler_id, bearer=bearer)
        self.assertEqual(ok, True, "Manager créé, requête envoyée, manager détruit")

    def test_un_appel_synchrone_wikidata(self):
        bearer = config['admin']["Bearer"]
        headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
        query = "https://query.wikidata.org/sparql"
        scheduler_id = createManager([query], bearer=bearer)
        
        # limit est le nombre d'appels par seconde pour ce manager
        data = {"scheduler_id": scheduler_id, "limit": 1}
        lim = requests.post(f"{baseurl}/api/set_rate_limit", json=data, headers=headers)
        
        cachedur = 60  # en secondes
        parameters = {"query": "select * where { ?s ?p ?o } limit 10", "format": "JSON"}
        encodedquery = urlencode(query=parameters, doseq=True)
        data = {
            "scheduler_id": scheduler_id,
            "url": urlunsplit(("https", "query.wikidata.org", "/sparql", encodedquery, "")),
            "method": "GET",
            "cache_duration": cachedur,
            "headers": {
                "User-Agent": "Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)"
            }
        }
        
        # 🔧 CORRECTION: Utiliser POST au lieu de GET pour envoyer la requête à l'API manager
        req = requests.post(f"{baseurl}/api/request", json=data, headers=headers)
        
        try:
            req_json = json.loads(req.text)
            if "uuid" not in req_json:
                print(f"❌ Erreur dans la réponse: {req.text}")
                self.fail(f"Pas d'UUID dans la réponse: {req_json}")
            
            uuidreq = req_json["uuid"]
            statusUrl = f"{baseurl}{req_json['status_url']}"
        except json.JSONDecodeError:
            print(f"❌ Réponse invalide: {req.text}")
            self.fail(f"Réponse JSON invalide: {req.text}")
        
        max_attempts = 100
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            stat = requests.get(statusUrl, headers=headers)
            jstat = json.loads(stat.text)
            
            if "status" in jstat and jstat["status"] == "complete":
                rep = jstat["response"]
                break
            elif "status" in jstat and jstat["status"] == "pending":
                time.sleep(0.1)
            else:
                print(f"⚠️ Status inattendu: {jstat}")
                time.sleep(0.1)
        else:
            self.fail(f"Timeout après {max_attempts} tentatives")
        
        print(rep)
        ok = (stat.status_code == 200) and ("response" in jstat) and ("results" in jstat["response"])
        deleteManager(scheduler_id, bearer=bearer)
        self.assertEqual(ok, True, "Manager créé, requête envoyée, manager détruit")

if __name__ == '__main__':
    print("#" * 50)
    print("🚨 PENSER À LANCER LE MANAGER (apiManager.py) !!!")
    print("#" * 50)
    unittest.main()
