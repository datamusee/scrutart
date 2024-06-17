import requests

class WPTools():
    def __init__(self, configPrivee):
        self.configPrivee = configPrivee
        self.api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
        self.api_url_get = f"{configPrivee.WORDPRESS_O2_API_URL}/posts"
        self.auth = (configPrivee.WORDPRESS_O2_USERNAME, configPrivee.WORDPRESS_O2_PASSWORD_APP)
        pass

    def getWPLink(self, title):
        data = {
            "search": title,
            "search_columns": "post_title",
            "Authorization": "Bearer"+str({self.configPrivee.WORDPRESS_O2_PASSWORD_APP})
        }
        response = requests.get(self.api_url_get, params=data, auth=self.auth).json()
        link = None
        if response and "link" in response:
            link = response[0]["link"]
        return link


    def getWPPageUrl(self, page_title, status="publish"):
        api_url = f"{self.configPrivee.WORDPRESS_O2_API_URL}/pages"

        # Paramètres de requête pour filtrer par titre de la page
        params = {
            'search': page_title,
            'status': status,
            "search_columns": "post_title",
            "Authorization": "Bearer" + str({configPrivee.WORDPRESS_O2_PASSWORD_APP})
        }

        try:
            # Effectuer la requête GET à l'API REST de WordPress
            response = requests.get(self.api_url_get, params=params, auth=self.auth)
            response.raise_for_status()  # Vérifie si la requête a réussi

            # Analyser les résultats de la requête
            pages = response.json()

            for page in pages:
                # Vérifier si le titre correspond exactement
                if page['title']['rendered'].lower() == page_title.lower():
                    return page['link']  # URL de la page trouvée
            return None  # Aucune page trouvée avec ce titre

        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la requête: {e}")
            return None

if __name__ == '__main__':
    # Exemple d'utilisation
    import configPrivee
    wpt = WPTools(configPrivee)
    page_titles = [ "Test SVG", "Test bidon", "Où trouver Carolus-Duran dans Wikidata, suivez le guide", "Carolus"]
    # page_titles = [ "Où trouver Carolus-Duran dans Wikidata, suivez le guide" ]

    for title in page_titles:
        page_url = wpt.getWPPageUrl(title)
        if page_url:
            print(f"La page '{title}' est publiée: {page_url}")
        else:
            print(f"La page '{title}' n'est pas publiée")
            page_url = wpt.getWPPageUrl(title, "draft")
            if page_url:
                print(f"La page '{title}' existe comme brouillon: {page_url}")
            else:
                print(f"La page '{title}' n'existe pas.")
        page_url = wpt.getWPPageUrl(title, "publish, draft")
        if page_url:
            print(f"La page '{title}' est publiée ou brouillon: {page_url}")
        else:
            print(f"La page '{title}' n'existe pas")
