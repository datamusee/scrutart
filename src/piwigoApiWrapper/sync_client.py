
import requests
from .exceptions import PiwigoAPIException
from collections import OrderedDict

class SyncClient:
    def __init__(self, url, username=None, password=None):
        self.url = url.rstrip('/') + '/ws.php'
        self.session = requests.Session()
        if username and password:
            self.login(username, password)

    def login(self, username, password):
        data = {
            'format': 'json',
            'method': 'pwg.session.login',
            'username': username,
            'password': password,
        }
        r = self.session.post(self.url, data=data)
        r.raise_for_status()
        # json_data = r.json()
        #if json_data.get('stat') != 'ok':
        if not r.ok:
            raise PiwigoAPIException(r.text)

    def call(self, method: str, params: dict = None, http_method: str = "POST") -> dict:
        params = params or {}
        data = OrderedDict()
        data['method'] = method
        data['format'] = 'json'
        for k, v in params.items():
            data[k] = v

        headers = {'Accept': 'application/json'}

        if http_method.upper() == "POST":
            response = self.session.post(self.url, params=data, headers=headers)
        else:
            response = self.session.get(self.url, params=data, headers=headers)

        response.raise_for_status()

        try:
            result = response.json()
        except Exception as e:
            raise PiwigoAPIException(f"Erreur lors du décodage JSON : {e}\nRéponse brute :\n{response.text}")

        if result.get('stat') != 'ok':
            raise PiwigoAPIException(result)
        return result

    def __getattr__(self, name):
        def dynamic_method(**kwargs):
            method_name = name.replace('_', '.')
            return self.call(method_name, kwargs)

        return dynamic_method

    def upload_image(self, filepath, category=None, name=None):
        with open(filepath, 'rb') as file:
            files = {'image': (filepath, file)}
            data = {
                'method': 'pwg.images.addSimple',
                'format': 'json',
                'category': category,
                'name': name or filepath
            }
            response = self.session.post(self.url, data=data, files=files)
            response.raise_for_status()
            result = response.json()
            if result.get('stat') != 'ok':
                raise PiwigoAPIException(result)
            return result
