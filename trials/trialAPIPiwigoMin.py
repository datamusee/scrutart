import requests
import configPiwigo as cp
piwigo_base_url = "https://galleries.grains-de-culture.fr/ws.php"
url = piwigo_base_url+"?format=json&method=pwg.session.login"
auth_data = {
    "username": cp.configPiwigo["login"],
    "password": cp.configPiwigo["pass"],
}
session = requests.Session()  # Crée une session persistante
response = session.post(url, data=auth_data)

if response.ok and response.json().get("stat") == "ok":
    print("Connexion réussie!")
    image_path = "image.jpg"
    # check if the image is findable
    with open(image_path,"r") as fimage:
        print("image trouvée: ", image_path)

    # send the image
    payload = {
        "image": image_path,
        "method": "pwg.images.addSimple",
        "category": 15,
        "name": "Test",
    }

    # Envoi de la requête avec authentification
    response_image = session.post(
        piwigo_base_url+"?format=json&method=pwg.images.addSimple",
        data=payload
    )

    # Vérification du succès de l'opération
    if response_image.status_code == 200:
        print("image uploaded in my piwigo, category 15")
    else:
        print("Erreur :", response_image.status_code, response_image.text)
