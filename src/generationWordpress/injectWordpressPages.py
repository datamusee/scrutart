import requests
import configPrivee2 as configPrivee

#api_url = f"{configPrivee.WORDPRESS_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_PASSWORD_APP}"
#auth = (configPrivee.WORDPRESS_USERNAME, configPrivee.WORDPRESS_PASSWORD_APP)
api_url = f"{configPrivee.WORDPRESS_O2_API_URL}/posts?Authorization=Bearer{configPrivee.WORDPRESS_O2_PASSWORD_APP}"
auth = (configPrivee.WORDPRESS_O2_API2USERNAME, configPrivee.WORDPRESS_O2_API2PASSWORD_APP)
data = {
    "title": "Article de test d'automation 4",
    "content": "Article 3 injecté avec injectWordpressPages.py",
    "status": "draft",
    "slug": "article-test-automation",
    "lang":"fr"
}

response = requests.post(api_url, json=data, auth=auth)
#response = requests.get(configPrivee.WORDPRESS_API_URL)

print(response.json())