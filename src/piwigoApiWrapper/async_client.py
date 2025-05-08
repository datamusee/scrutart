
import httpx
from .exceptions import PiwigoAPIException

class AsyncClient:
    def __init__(self, url, username=None, password=None):
        self.url = url.rstrip('/') + '/ws.php'
        self.client = httpx.AsyncClient()
        self.username = username
        self.password = password

    async def login(self):
        data = {
            'method': 'pwg.session.login',
            'username': self.username,
            'password': self.password,
            'format': 'json'
        }
        response = await self.client.post(self.url, data=data)
        result = response.json()
        if result.get('stat') != 'ok':
            raise PiwigoAPIException(result)

    async def call(self, method: str, params: dict = None, http_method: str = "POST") -> dict:
        params = params or {}
        data = {'method': method, 'format': 'json', **params}
        if http_method == "POST":
            response = await self.client.post(self.url, data=data)
        else:
            response = await self.client.get(self.url, params=data)
        result = response.json()
        if result.get('stat') != 'ok':
            raise PiwigoAPIException(result)
        return result

    def __getattr__(self, name):
        async def wrapper(**kwargs):
            method_name = name.replace('_', '.')
            return await self.call(method_name, kwargs)
        return wrapper

    async def upload_image(self, filepath, category=None, name=None):
        with open(filepath, 'rb') as file:
            files = {'image': (filepath, file.read())}
            data = {
                'method': 'pwg.images.addSimple',
                'format': 'json',
                'category': category,
                'name': name or filepath
            }
            response = await self.client.post(self.url, data=data, files=files)
            result = response.json()
            if result.get('stat') != 'ok':
                raise PiwigoAPIException(result)
            return result
