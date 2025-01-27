import unittest
import json
import time
import requests
from ..WikimediaManagerPackage.configPrivee import config

#baseurl = "http://127.0.0.1:5000"
baseurl = "https://webapimanager.grains-de-culture.fr"


def createManager(targetUrls, bearer=None):
    data = {"api_urls": targetUrls }
    headers = {"Authorization": f"Bearer {bearer}", "Content-Type": "application/json"} if bearer else {}
    # create manager
    resp = requests.post(f"{baseurl}/api/initialize", json=data, headers=headers)
    jsonrep = json.loads(resp.text)
    manager_id = jsonrep["manager_id"] if "manager_id" in jsonrep else None
    return manager_id

def deleteManager(manager_id, bearer=None):
    headers = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    url = f"{baseurl}/api/delete_manager"
    response = requests.delete(f"{url}?manager_id={manager_id}", headers=headers)
    ok = (response.status_code == 200)
    return ok

class MyTestCase(unittest.TestCase):
    def test_creation_destruction_manager_sans_token(self):
        query = "https://randomuser.me/api/"
        manager_id= createManager([query])
        self.assertEqual(manager_id, None, "échec de Manager créé" )

    def test_creation_destruction_manager(self):
        bearer = config['admin']["Bearer"]
        query = "https://randomuser.me/api/"
        manager_id= createManager([query], bearer)
        ok = deleteManager(manager_id, bearer)
        self.assertEqual(ok, True, "échec de Manager créé, manager détruit")

    def test_un_appel_synchrone(self):
        bearer = config['admin']["Bearer"]
        headers = {f"Authorization": f"Bearer {bearer}"} if bearer else {}
        query = "https://randomuser.me/api/"
        manager_id = createManager([query], bearer=bearer)
        # limit est le nombre d'appels par seconde pour ce manager
        data = { "manager_id": manager_id, "limit": 1 }
        lim = requests.post(f"{baseurl}/api/set_rate_limit", json=data, headers=headers)
        cachedur = 60  # 0;  en secondes
        data = {
            "manager_id": manager_id,
            "url": query,
            "method": "GET",
            "cache_duration": cachedur,
        }
        # mise de la requête dans la file d'attente
        req = requests.post(f"{baseurl}/api/request", json=data, headers=headers)
        uuidreq = json.loads(req.text)["uuid"]
        statusUrl = f"{baseurl}{json.loads(req.text)['status_url']}"
        while True:
            stat = requests.get(statusUrl, headers=headers)
            jstat = json.loads(stat.text)
            if "status" in jstat and jstat["status"] == "complete":
                rep = jstat["response"]
                break
            elif "status" in jstat and jstat["status"] == "pending":
                time.sleep(0.1)
            else:
                # print(jstat)
                pass
        print(rep)
        ok = (stat.status_code == 200) and ("response" in jstat) and ("info" in jstat["response"])
        deleteManager(manager_id, bearer=bearer)
        self.assertEqual(ok, True, "Manager créé, requête envoyée, manager détruit")


if __name__ == '__main__':
    # lancer le manager
    print("#############################")
    print("#############################")
    print("#############################")
    print("#############################")
    print("#############################")
    print("Penser à lancer le manager (code apiManager.py)!!!")
    print("#############################")
    print("#############################")
    print("#############################")
    print("#############################")
    print("#############################")
    unittest.main()
