import os
import requests
from pathlib import Path

from flask import Flask, render_template, url_for
import os
import requests
import json
import src.generationWordpress.WikimediaAccess as wikidataObject

app = Flask(__name__)
# Monte le dossier `static` pour servir les fichiers statiques
# app.mount("/static", StaticFiles(directory="static"), name="static")

IMAGE_FOLDER = 'static/images'
# Dossier de cache pour les images téléchargées
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# classes à lire dans un fichier de configuration
classes = {
    "genre": {
                "pids": ["P136"],
                "title": "Genre",
                "sparqlTemplate": """
                    select distinct ?image
                    where
                    {
                      values ?entityClass { __ENTITYTYPES__ }
                      values ?entityValue { __ENTITYVALUES__ }
                      ?s ?entityClass ?entityValue;
                         wdt:P31 wd:Q3305213;
                         wdt:P18 ?image
                    }
                    limit __LIMIT__ offset __OFFSET__
                """,
                "elmts": {
                   "portrait": { "qids": ["Q134307", "Q60133444", "Q192110"], "labels": { "fr": "portrait", "en": "portrait"}},
                   "marine": {"qids": ["Q158607"], "labels": {"fr": "marine", "en": "marine"}},
               }
            },
    "movement": {
                "pids": ["P135"],
                "title": "Mouvement",
                "sparqlTemplate": "",
                "elmts": {
                }
            },
    "depicts" : { "pids": ["P180"], "title": "Illustre"},
}

def buildImageList(entityClass, entityValue):
    wo = wikidataObject.WikidataObject("Q")
    entitytypes = "wdt:"+"wdt:".join(classes[entityClass]["pids"])
    entityvalues = "wd:"+" wd:".join(classes[entityClass]["elmts"][entityValue]["qids"])
    sparqlQuery = classes[entityClass]["sparqlTemplate"].replace("__LIMIT__", str(20)).replace("__OFFSET__", str(0))\
                        .replace("__ENTITYTYPES__", entitytypes).replace("__ENTITYVALUES__", entityvalues)
    print(sparqlQuery)
    sparqlres = wo.sparqlQuery(sparqlQuery)
    imglist = []
    if sparqlres and hasattr(sparqlres, "bindings"):
        if len(sparqlres.bindings):
            list = sparqlres.bindings
            i = 1
            for elmt in list:
                url = elmt["image"].value
                if (".jpg" in url) or (".png" in url):
                    imgobj = { "name": "Image "+str(i), "url": url }
                    imglist.append(imgobj)
                    i = i + 1
    return imglist

# Liste de paires (nom, url) pour les images
images_list = buildImageList("genre", "portrait")

def cache_image(image_name, image_url):
    """Télécharge l'image si elle n'est pas déjà en cache."""
    image_path = os.path.join(IMAGE_FOLDER, image_name)

    # Si l'image n'existe pas localement, la télécharger
    if not os.path.exists(image_path):
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(image_path, 'wb') as file:
                file.write(response.content)
    return url_for('static', filename=f'images/{image_name}')

def download_image(url):
    """Télécharge une image depuis l'URL et la stocke en cache si elle n'existe pas."""
    try:
        image_name = url.split("/")[-1]
        image_path = CACHE_DIR / image_name

        # Si l'image n'est pas en cache, on la télécharge
        if not image_path.exists():
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with open(image_path, "wb") as f:
                f.write(response.content)

        return f"/cache/{image_name}"
    except Exception as e:
        print(f"Erreur lors du téléchargement de l'image {url}: {e}")


@app.route('/gallery/<entitytype>/<entityvalue>')
def galleryType(entitytype, entityvalue):
    print(f"Type {entitytype}: {entityvalue}")
    return f"<h1>{entitytype}: {entityvalue}</h1>"

@app.route('/gallerylist')
def gallerylist():
    cached_images =[]
    for image in images_list:
        cachedimage = { 'name':image["name"], 'path': cache_image(image["name"], image["url"]), 'url': image["url"] }
        cached_images.append(cachedimage)
        print(cachedimage)
    return json.dumps(cached_images)

@app.route('/')
def gallery():
    # Vérifie si les images sont en cache, sinon les télécharge
    cached_images =[]
    for image in images_list:
        cachedimage = (image["name"], cache_image(image["name"], image["url"]), image["url"] )
        cached_images.append(cachedimage)
        print(cachedimage)
    return render_template('index.html')


if __name__ == '__main__':
    # Création du dossier de cache si nécessaire
    os.makedirs(IMAGE_FOLDER, exist_ok=True)
    # buildImageList("genre","portrait")
    # Monter le dossier `cache` pour servir les images mises en cache
    # app.mount("/cache", StaticFiles(directory=str(CACHE_DIR)), name="cache")

    app.run(debug=True)

