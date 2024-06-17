import requests
import requests
import generationDocuments.generationWordpress.configPrivee as configPrivee

#api_url = f"{configPrivee.WORDPRESS_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_PASSWORD_APP}"
#auth = (configPrivee.WORDPRESS_USERNAME, configPrivee.WORDPRESS_PASSWORD_APP)
auth = (configPrivee.WORDPRESS_O2_USERNAME, configPrivee.WORDPRESS_O2_PASSWORD_APP)

def createPageWP(titre, contenu, statut="draft"):
    data = {
        "title": titre,
        "content": contenu,
        "status": statut,
        "lang":"fr"
    }
    api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
    response = requests.post(api_url, json=data, auth=auth)
    #response = requests.get(configPrivee.WORDPRESS_API_URL)
    return response.json()

def updatePageWP(id, contenu, statut="draft"):
    data = {
        "content": contenu,
        "status": statut,
        "lang":"fr"
    }
    # api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/pages/{id}?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
    api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts/{id}"
    response = requests.put(api_url, json=data, auth=auth)
    #response = requests.get(configPrivee.WORDPRESS_API_URL)
    return response.json()

if __name__=="__main__":
    # préparer deux pages vides avec seulement un titre chacune
    titre1 = "Test de page 1 avec lien vers page 2"
    titre2 = "Test de page 2 avec lien vers page 1"
    contenuSansLien1 = "Exemple de contenu 1"
    contenuSansLien2 = "Exemple de contenu 2"
    # installer ces pages sur WP et récupérer leurs urls
    r1 = createPageWP(titre1, contenuSansLien1)
    r2 = createPageWP(titre2, contenuSansLien2)
    # préparer le contenu de chacune des pages chaque page référençant l'autre
    link1 = f"{configPrivee.WORDPRESS_O2_BASE_URL}?p="+str(r1["id"])
    link2 = f"{configPrivee.WORDPRESS_O2_BASE_URL}?p="+str(r2["id"])
    contenuAvecLienVersPage2 = """
    <!-- wp:paragraph -->
    <p>Lien vers <a href="{lienpage}" title="">page 2</a></p>
    <!-- /wp:paragraph -->
    """.format(lienpage=link2)
    contenuAvecLienVersPage1 = """
    <!-- wp:paragraph -->
    <p>Lien vers <a href="{lienpage}" title="">page 1</a></p>
    <!-- /wp:paragraph -->
    """.format(lienpage=link1)
    # injecter les deux pages dans WP
    u1 = updatePageWP(r1["id"], contenuAvecLienVersPage2)
    u2 = updatePageWP(r2["id"], contenuAvecLienVersPage1)
    pass