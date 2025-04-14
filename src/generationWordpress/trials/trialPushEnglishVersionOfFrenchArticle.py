import requests
import json
import src.generationWordpress.configPrivee2 as configPrivee

# Informations d'authentification
WP_URL = f"{configPrivee.WORDPRESS_O2_API_URL}"

# Article source en français
ARTICLE_ID_FR = 770  # ID test général en français
LANGUAGE_FR = "fr"
LANGUAGE_EN = "en"

# Headers d'authentification
auth = (configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP)
headers = {"Content-Type": "application/json"}

# Étape 1 : Récupérer l'article en français
response = requests.get(f"{WP_URL}/posts/{ARTICLE_ID_FR}", auth=auth)
if response.status_code != 200:
    raise Exception("Erreur lors de la récupération de l'article français")

article_fr = response.json()

# Étape 2 : Créer la version anglaise de l'article
data_en = {
    "title": f"{article_fr['title']['rendered']} (English)",
    "content": article_fr["content"]["rendered"],
    "status": "draft",  # "publish" si vous  voulez  le publier immédiatement
    "lang": LANGUAGE_EN,  # Définition de la langue anglaise avec Polylang
    "translations": {LANGUAGE_FR: ARTICLE_ID_FR},  # Lier les versions
}

#response = requests.post(f"{WP_URL}/posts", headers=headers, auth=auth, data=json.dumps(data_en))

if response.status_code == 201:
    print("Article anglais créé avec succès :", response.json()["id"])
    article_en_id = response.json()["id"]
    print("Erreur lors de la création de l'article anglais :", response.text)

article_en_id = 1407
translations_en = {
    LANGUAGE_EN: article_en_id
}
translations_fr = {
    LANGUAGE_FR: ARTICLE_ID_FR,
}
translations = {
    LANGUAGE_FR: ARTICLE_ID_FR,
    LANGUAGE_EN: article_en_id
}

# Mettre à jour l'article en français
res_fr_1 = requests.post(f"{WP_URL}/posts/{ARTICLE_ID_FR}", headers=headers, auth=auth, data=json.dumps({"translations": translations}))
with open("fr1_lnk.json", "w", encoding="utf-8") as fr1:
    json.dump(res_fr_1.json(), fr1, ensure_ascii=False)

# Mettre à jour l'article en anglais
res_en_1 = requests.post(f"{WP_URL}/posts/{article_en_id}", headers=headers, auth=auth, data=json.dumps({"translations": translations}))
with open("en1_lnk.json", "w", encoding="utf-8") as en1:
    json.dump(res_en_1.json(), en1, ensure_ascii=False)

print("🔗 Liaison des articles terminée !")
res_fr = requests.get(f"{WP_URL}/posts/{ARTICLE_ID_FR}", headers=headers, auth=auth, data=json.dumps({"lang":"fr", "translations[en]": translations_en}))
res_en = requests.get(f"{WP_URL}/posts/{article_en_id}", headers=headers, auth=auth, data=json.dumps({"lang":"en","translations[fr]": translations_fr}))
pass