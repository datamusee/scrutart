import requests

url = "http://localhost:5000/send_message"
data = {"client_id": "client123", "message": "Hello, client123!"}
response = requests.post(url, json=data)
print(response.json())
