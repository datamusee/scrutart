import json
import time

import requests
# from configPrivee import config
from ..WikimediaManagerPackage.configPrivee import config

def main():
    baseurl = "http://127.0.0.1:5000"
    #baseurl = "https://webapimanager.grains-de-culture.fr"

    data = {
        "api_patterns": ["https://randomuser.me/api/"]
    }
    headers = {
        "Authorization": f"Bearer {config['admin']['Bearer']}",
        "Content-Type": "application/json"
    }
    resp = requests.post(f"{baseurl}/api/initialize", json=data, headers=headers)
    print(resp.text)
    manager_id = json.loads(resp.text)["manager_id"]
    data = {
        "manager_id": manager_id,
        "limit": 1
    }
    # limit est le nombre d'appels par seconde pour ce manager
    lim = requests.post(f"{baseurl}/api/set_rate_limit", json=data, headers=headers)
    print(lim.text)
    query = "https://randomuser.me/api/"

    cachedur = 0 # 0;  en secondes
    data = {
        "manager_id": manager_id,
        "url": query,
        "method": "GET",
        "cache_duration": cachedur,
        "headers": {
            "User-Agent": "Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)"
        }
    }
    req = requests.post(f"{baseurl}/api/request", json=data, headers=headers)
    uuidreq = json.loads(req.text)["uuid"]
    print(json.loads(req.text))
    statusUrl = f"{baseurl}{json.loads(req.text)['status_url']}"
    print(statusUrl)
    time.sleep(json.loads(req.text)["estimated_delay"])
    while True:
        stat = requests.get(statusUrl, headers=headers)
        jstat = json.loads(stat.text)
        if "status" in jstat and jstat["status"]=="complete":
            print(jstat["response"])
            break
        elif "status" in jstat and jstat["status"]=="pending":
            print(jstat["message"])
        else:
            print(jstat)
        time.sleep(1)

    url = f"{baseurl}/api/delete_manager"
    maconfig = config["admin"]
    bearer = maconfig['Bearer']
    headers = {
        f"Authorization": f"Bearer {bearer}"
    }
    response = requests.delete(f"{url}?manager_id={manager_id}", headers=headers)

    if response.status_code == 200:
        print("Manager deleted successfully:", response.json())
    else:
        print("Failed to delete manager:", response.json())

if __name__=="__main__":
    main()