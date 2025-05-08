
import requests

class PiwigoClient:
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.cookies = self._login()

    def _login(self):
        response = requests.post(self.url, data={
            'method': 'pwg.session.login',
            'username': self.username,
            'password': self.password,
            'format': 'json'
        })
        response.raise_for_status()
        return response.cookies

    def update_category_description(self, category_id, html_description):
        response = requests.post(self.url, data={
            'method': 'pwg.categories.setInfo',
            'category_id': category_id,
            'comment': html_description,
            'format': 'json'
        }, cookies=self.cookies)
        response.raise_for_status()
        return response.json()
