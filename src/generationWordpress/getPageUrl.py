import requests
import configPrivee

api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
api_url_get = f"{configPrivee.WORDPRESS_O2_API_URL}/posts"
auth = (configPrivee.WORDPRESS_O2_USERNAME, configPrivee.WORDPRESS_O2_PASSWORD_APP)


if __name__ == '__main__':
    # Exemple d'utilisation
#    page_titles = [ "Test SVG", "Test bidon", "Où trouver Carolus-Duran dans Wikidata, suivez le guide", "Carolus"]
    page_titles = [ "Où trouver Carolus-Duran dans Wikidata, suivez le guide" ]

    for title in page_titles:
        page_url = get_wordpress_page_url(title)
        if page_url:
            print(f"La page '{title}' existe: {page_url}")
        else:
            print(f"La page '{title}' n'existe pas.")
