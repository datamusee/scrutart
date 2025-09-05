import time
from urllib.parse import urlencode, urlunsplit
from WikimediaManagerPackage import configPrivee
import requests
import json
import uuid
import socketio

baseurl = "http://127.0.0.1:5000"

data = {
    "api_patterns": ["https://randomuser.me/api/", "https://query.wikidata.org/sparql"]
}
headers = {
    "Authorization": f"Bearer {configPrivee.config['admin']['Bearer']}",
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
parameters = {
    "query": "select * where { ?s ?p ?o } limit 10",
    "format": "JSON"
}
query = urlencode(query=parameters, doseq=True)
#query = "https://randomuser.me/api/"

# Générer un client_id unique
client_id = str(uuid.uuid4()) # Identifiant unique pour ce client

# Créer une instance du client Socket.IO
sio = socketio.Client()

# Gérer les événements
@sio.on('message')
def on_message(data):
    msg = data['data']
    print(f"Message received: {msg}")
    if "request_id" in msg:
        sio.disconnect()
        sio.shutdown()

@sio.on('connect')
def on_connect():
    print("Connected to server")
    # Envoyer le client_id au serveur pour s'enregistrer
    time.sleep(1)
    sio.emit('register', {'client_id': client_id})

@sio.on('disconnect')
def on_disconnect():
    print("Disconnected from server")

server_url = "http://localhost:5000"
sio.connect(server_url)
# Maintenir la connexion active

# Définir des événements
# Callback pour recevoir les messages WebSocket

# Soumettre une requête via /api/request
cachedur = 0 # 0;  en secondes
data = {
    "manager_id": manager_id,
    "url": urlunsplit(("https", "query.wikidata.org", "/sparql", query, "")),
    "method": "GET",
    "cache_duration": cachedur,
    "headers": {
        "User-Agent": "Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)"
    },
    "client_id": client_id
}
bearer = configPrivee.config['admin']['Bearer']

req = requests.post(f"{baseurl}/api/request", json=data, headers=headers)
uuidreq = json.loads(req.text)["uuid"]
print(json.loads(req.text))
statusUrl = f"{baseurl}{json.loads(req.text)['status_url']}"
print(statusUrl)
sio.wait()

url = f"{baseurl}/api/delete_manager"
config = configPrivee.config["admin"]
bearer = config['Bearer']
headers = {
    "User-Agent": "Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)",
    "Authorization": f"Bearer {bearer}"
}
response = requests.delete(f"{url}?manager_id={manager_id}", headers=headers)

if response.status_code == 200:
    print("Manager deleted successfully:", response.json())
else:
    print("Failed to delete manager:", response.json())
