import requests
import configPrivee2 as configPrivee
import WPTools

api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
api_url_get = f"{configPrivee.WORDPRESS_O2_API_URL}/posts"
auth = (configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP)

def get_wordpress_page_url(title):
    wpt = WPTools.WPTools(configPrivee)
    res = wpt.getWPPageUrl(title)
    return res

if __name__ == '__main__':
    # Exemple d'utilisation
    page_titles = [ "Test SVG", "Test bidon", "Où trouver Carolus-Duran dans Wikidata, suivez le guide", "Carolus"]
    # page_titles = [ "Où trouver Carolus-Duran dans Wikidata, suivez le guide" ]
    # page_titles = [ "Canada, peintures et Wikidata" ]

    for title in page_titles:
        page_url = get_wordpress_page_url(title)
        if page_url:
            print(f"La page '{title}' existe: {page_url}")
        else:
            print(f"La page '{title}' n'existe pas.")
