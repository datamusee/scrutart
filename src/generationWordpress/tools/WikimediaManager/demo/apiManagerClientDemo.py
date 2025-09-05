import json
import time

import requests
from urllib.parse import urlencode, urlunsplit, quote_plus
from src.generationWordpress.tools.WikimediaManager.WikimediaManagerPackage import configPrivee
import socketio


baseurl = "http://127.0.0.1:6000"

data = {
    "api_patterns": ["https://randomuser.me/api/"] #, "https://query.wikidata.org/sparql"]
}
bearer = configPrivee.config['admin']['Bearer']
headers = {
    "Authorization": f"Bearer {bearer}",
    "Content-Type": "application/json"
}
resp = requests.post(f"{baseurl}/api/initialize", json=data, headers=headers)
print(resp.text)
scheduler_id = json.loads(resp.text)["scheduler_id"]
data = {
    "scheduler_id": scheduler_id,
    "limit": 1
}
# limit est le nombre d'appels par seconde pour ce manager
lim = requests.post(f"{baseurl}/api/set_rate_limit", json=data, headers=headers)
print(lim.text)
parameters = {"query": "select * where { ?s ?p ?o } limit 10", "format": "JSON"}
#query = urlencode(query=parameters, doseq=True)
query = "https://randomuser.me/api/"

cachedur = 0 # 0;  en secondes
data = {
    "scheduler_id": scheduler_id,
    "url": query, # urlunsplit(("https", "query.wikidata.org", "/sparql", query, "")),
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

response = requests.post(
    f"http://localhost:5000/api/request?scheduler_id={scheduler_id}",
    json={
        "url": query, # urlunsplit(("https", "query.wikidata.org", "/sparql", query, "")),
        "method": "GET",
        "cache_duration": 60,
        "request_kwargs": {
            "headers": {
                "Authorization": f"Bearer {bearer}",
                "User-Agent": "Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)"
            }
        }
    },
    headers=headers
)

print("Set Web Api Get with POST Call:", response.json())

response = requests.get(
    "http://localhost:5000/api/request",
    params={
        "scheduler_id": f"{scheduler_id}",
        "url": query, # urlunsplit(("https", "query.wikidata.org", "/sparql", query, "")),
        "method": "POST",
        "cache_duration": 30,
        "request_kwargs": {
            "headers": {
                "User-Agent": "Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)"
            }
        }
    },
    headers=headers
)

print("Set Web Api Post with GET Call:", response.json())


# Créer un client Socket.IO
sio = socketio.Client()

# Définir des événements
@sio.on('response_ready')
def on_response_ready(data):
    print("Réponse reçue:", data)

# Connexion au serveur WebSocket
sio.connect(f"http://localhost:5000?client_id=client_id_for_{response.json()['uuid']}", headers={"Authorization": f"Bearer {bearer}"})

# Maintenir la connexion active
sio.wait()

url = f"{baseurl}/api/delete_manager"
config = configPrivee.config["admin"]
bearer = config['Bearer']
headers = {
    f"Authorization": f"Bearer {bearer}"
}
response = requests.delete(f"{url}?scheduler_id={scheduler_id}", headers=headers)

if response.status_code == 200:
    print("Manager deleted successfully:", response.json())
else:
    print("Failed to delete manager:", response.json())

