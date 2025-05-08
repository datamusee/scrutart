import requests

url = "https://galeries.grains-de-culture.fr/ws.php"  # ← bien ws.php ici !
payload = {
    "method": "pwg.session.getStatus",
    "format": "json"
}
headers = {
    "Accept": "application/json"
}
# il faut utiliser params=.. et pas data=...
r = requests.post(url, params=payload, headers=headers)

print("Type de réponse :", r.headers.get("Content-Type"))
print("Corps de la réponse :", r.text)