import requests
import configPiwigo as cp
import datetime
import json
import time

def postImageToPiwigo(im, piwigoCategory=15, categoryName="portrait", configPiwigo=None, track=None):
    # dans la version 2, il peut y avoir plusieurs images, je prends la première
    # il faudrait prendre la meilleure, de préférence sans le cadre
    if not configPiwigo: return None
    image_path = im["images"][0]
    hh = { 'User-Agent': 'Scrutart-UA (https://scrutart.grains-de-culture.fr/; scrutart@grains-de-culture.fr)'}
    image_response = requests.get(image_path, headers=hh)
    image_data = image_response.content

    username = configPiwigo.configPiwigo["login"]
    password = configPiwigo.configPiwigo["pass"]
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
        # print("Connexion réussie!")
        titre = im["titre_fr"]
        uri = im["uri"]
        qid = uri.replace("http://www.wikidata.org/entity/", "")
        crea = im["createur"]
        creaLab = im["createurLabel"]
        categorie_id = piwigoCategory  # ID de la catégorie dans laquelle ajouter l'image
        # todo ajouter nom créateur dans description
        # todo gérer description multilingue
        description = f"""Créateur: <a href="{crea}">{creaLab}</a><div>Source Wikimedia Commons <a href='{image_path}'>{image_path}</a></div><div>Elément Wikidata <a href='{uri}'>{qid}</a></div>"""
        tags = [categoryName]  # Liste des tags à associer à l'image

        # Authentification et envoi de l'image avec des métadonnées
        payload = {
            "image": image_path,
            "method": "pwg.images.addSimple",
            "category_id": categorie_id,
            "category": categorie_id,
            "name": titre,
            "comment": description,
            "tags": ",".join(tags),  # Convertir la liste de tags en une chaîne séparée par des virgules
        }
        # Construire les données de la requête avec la pièce jointe
        files = {'image': (image_path, image_data, 'image/jpeg')}
        print(f"L'image '{titre}' va être envoyée ! ({datetime.datetime.now()})")
        response = session.post(
            piwigo_base_url + "?format=json&method=pwg.images.addSimple",
            data=payload,
            files=files
        )
        # todo ajouter des logs
        if response and response.status_code == 200:
            print(f"L'image '{titre}' a été téléchargée avec succès et les métadonnées ont été ajoutées ! ({datetime.datetime.now()})")
            if track:
                imageTracker.trackPushedImage(im, res)
                time.sleep(12)  # délai pour pas saturer l'interface Piwigo;
                # TODO on devrait plutot passer par l'APIManager pour gérer le délai
            return response
        else:
            print("Erreur :", response.status_code, response.text)
            return None

def convertFromV1To(data, versionTarget):
    targetData = data
    if "version" in data and data["version"]!="1.0.0"  and data["version"]!="1.0.1":
        return data
    if versionTarget=="2.0.0":
        listim = data["liste"]
        if not "dict" in targetData:
            targetData["dict"] = {}
        targetData["version"] = "2.0.0"
        for im in listim:
            imuri = im["uri"]
            if not imuri in targetData["dict"]:
                targetData["dict"][imuri] = {}
                targetData["dict"][imuri]["uri"] = imuri
                if "createur" in im: targetData["dict"][imuri]["createur"] = im["createur"]
                if "createurLabel" in im: targetData["dict"][imuri]["createurLabel"] = im["createurLabel"]
                if "titre_fr" in im: targetData["dict"][imuri]["titre_fr"] = im["titre_fr"]
                if "posted" in im: targetData["dict"][imuri]["posted"] = im["posted"]
                if "image" in im: targetData["dict"][imuri]["images"] = [im["image"]]
            else:
                if "image" in im: targetData["dict"][imuri]["images"].append(im["image"])
        if "liste" in targetData: targetData["liste"] = []
    return targetData

def simpleCopy(data, versionTarget):
    return data

def convertListImage(data, versionSrc, versionTarget):
    knowVersions = {
        "1.0.0": { "desc" : "version initiale composée d'une liste obtenue par téléchargement sur WDQS auquel on a ajouté un champ sparql pour garder trace de la requ^te qui a servi à générer ces données"},
        "1.0.1": { "desc" : "v1 pour la clé liste, mais avec déjà des éléments renseignés dans la clé dict construite comme dans v2"},
        "2.0.0": { "desc": "évolution de version 1, pour éviter d'envoyer plusieurs images pour une même œuvre; la liste est remplacée par un dictionnaire; c'est l'oeuvre qui est marquée comme postée, pas l'image" }
    }
    dataConverter = {
        "1.0.0": convertFromV1To,
        "1.0.1": convertFromV1To
    }
    targetData = dataConverter.get(versionSrc, simpleCopy)(data,versionTarget)
    return targetData

def getFilesList(dirToProcess):
    filesList = []
    from os import listdir
    from os.path import isfile, join
    filesList = [join(dirToProcess, f) for f in listdir(dirToProcess) if isfile(join(dirToProcess, f))]
    return filesList

class ImageTracker():
    def __init__(self, listimagespath, data, freqsav=5):
        self.idxsav = 0
        self.freqsav = freqsav
        self.listimagespath = listimagespath
        self.change = False
        self.data = data
        self.dictim = data["dict"]
        pass

    def trackPushedImage(self, imageDesc, pushedres):
        # TODO traces dans le graphe scrutartState
        # en attendant, écriture dans un fichier toutes les N images + quand on quitte l'appli
        self.change = True
        imageDesc["post_result"] = pushedres.text
        imageDesc["posted"] = True
        self.dictim[uri] = imageDesc
        self.idxsav += 1
        if self.idxsav >= self.freqsav:
            self.idxsav = 0
            with open(self.listimagespath, "w", encoding="UTF-8") as fdata:
                self.data["dict"] = self.dictim
                json.dump(data, fdata, ensure_ascii=False)

    def __del__(self):
        if self.change:
            with open(self.listimagespath, "w", encoding="UTF-8") as fdata:
                self.data["dict"] = dictim
                json.dump(self.data, fdata, ensure_ascii=False)
        pass

if __name__=="__main__":
    # choix d'un dossier dans lequel il y a des fichiers qui constituent des listes d'images
    dirToProcess = "D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\\fr\\20250507"
    filesList = getFilesList(dirToProcess)
    for filepath in filesList:
        if not "listeAlbums" in filepath: continue
        itemsToProcess = []
        # with open("D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\generationWordpress\data\listeAlbumsCreateurs.json",
        with open(filepath, encoding="UTF-8") as albumsItemsFile:
            itemsToProcess = json.load(albumsItemsFile)
        for item in itemsToProcess:
            #### remplacer ces lignes par création de catégorie si elle n'existe pas déjà
            categoryName = item["categoryName"]
            print(f"""Galerie {categoryName} ({item["qid"]})""")
            piwigoCategory = item["piwigoCategory"]
            listimagespath = item["listimagespath"]
            dictim = {}
            with open(listimagespath, "r", encoding="UTF-8") as fdata:
                data = json.loads(fdata.read())
                if (not "version" in data) or (data["version"]=="1.0.1"):
                    data = convertListImage(data, "1.0.0", "2.0.0")
                dictim = data["dict"]
            imageTracker = ImageTracker(listimagespath, data, 5)
            if dictim:
                print(datetime.datetime.now())
                for uri, im in dictim.items():
                    if not "posted" in im:
                        res = postImageToPiwigo(im, piwigoCategory, categoryName, cp, track=True)

# La description peut contenir un lien vers l'entité source, un lien vers l URL de l'image, le copyright
# il faut limiter l'api à n'accepter que certains émetteurs
