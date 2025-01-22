import json
import time

import requests
from urllib.parse import urlencode, urlunsplit, quote_plus

baseurl = "http://127.0.0.1:5000"

data = {
    "api_urls": ["https://query.wikidata.org/sparql"]
}
headers = {
    "Authorization": "Bearer SECRET_TOKEN",
    "Content-Type": "application/json"
}
resp = requests.post(f"{baseurl}/api/initialize", json=data, headers=headers)
print(resp.text)
manager_id = json.loads(resp.text)["manager_id"]
data = {
    "manager_id": manager_id,
    "limit": 1
}
lim = requests.post(f"{baseurl}/api/set_rate_limit", json=data, headers=headers)
print(lim.text)
parameters = {"query": "select * where { ?s ?p ?o } limit 10", "format": "JSON"}
no_value_parameters = ["kiosk", "other_parameter"]
no_value_parameters_quoted = [quote_plus(p) for p in no_value_parameters]

query = urlencode(query=parameters, doseq=True)
link = urlunsplit(("https", "my_grafana.com", "/graph", query, ""))

cachedur = 1000 # 0;  en secondes
data = {
    "manager_id": manager_id,
    "url": urlunsplit(("https", "query.wikidata.org", "/sparql", query, "")),
    "httpcmd": "GET",
    # "payload": { "query": "??"},
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
headers = {
    "Authorization": "Bearer SECRET_TOKEN"
}
response = requests.delete(f"{url}?manager_id={manager_id}", headers=headers)

if response.status_code == 200:
    print("Manager deleted successfully:", response.json())
else:
    print("Failed to delete manager:", response.json())
