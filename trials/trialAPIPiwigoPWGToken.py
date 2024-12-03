import json
import requests
import configPiwigo as cp

def get_pwg_token():
    username = cp.configPiwigo["login"]
    password = cp.configPiwigo["pass"]
    auth_data = {
        "format": "application/json",
        "method": "pwg.session.login",
        "username": username,
        "password": password,
    }
    # Ouvrir une session avec l'API pour se connecter
    session = requests.Session()  # Crée une session persistante
    # Envoyer la requête de connexion
    piwigo_base_url = "https://galleries.grains-de-culture.fr/ws.php"
    response = session.post(piwigo_base_url, data=auth_data)
    if response.ok:  # and response.json().get("stat") == "ok":
        payload = {
            "method": "pwg.session.getStatus",
            "format": "application/json"
        }
        # Authentification et envoi de l'image avec des métadonnées
        status_response = session.post(
            piwigo_base_url + "?format=json&method=pwg.images.setCategory",
            data=payload,
        )
        json_response = json.loads(status_response.text)
        token = json_response.get("result", {}).get("pwg_token")
        if status_response.status_code == 200:
            return response, token
        else:
            print("Erreur :", response.status_code, response.text)
            return None, "Erreur de récupération "

def delete_image(image_id, pwg_token, cookies):
    """Delete an image from Piwigo using the API."""
    payload = {
        "method": "pwg.images.delete",
        "pwg_token": pwg_token,
        "image_id": image_id,
        "format": "application/json",
    }
    response = requests.post(PIWIGO_URL, data=payload, cookies=cookies)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    try:
        # Step 1: Get pwg_token
        token, session_cookies = get_pwg_token()
        print("pwg_token retrieved:", token)

        # Step 2: Delete an image (replace IMAGE_ID with a valid ID)
        IMAGE_ID = 42
        delete_result = delete_image(IMAGE_ID, token, session_cookies)
        print(f"Image {IMAGE_ID} deletion result:", delete_result)
    except Exception as e:
        print("An error occurred:", e)
