import requests
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session

# Replace these values with your actual OAuth2 credentials
client_id = '2wP6cyikOYjGbditlbyn9ii12'
client_secret = 'QeXKP4Ubhj0ncOXsFpGwI1FVDzSmU0r4A1z9KOo0H51pt7RRu2'
redirect_uri = 'http://127.0.0.1:5000/oauth'
authorization_base_url = 'https://api.twitter.com/oauth/authorize'
token_url = 'https://api.twitter.com/login/oauth/access_token'

# Step 1: Obtain authorization grant (code)
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=['read:user'])
authorization_url, state = oauth.authorization_url(authorization_base_url)

print(f'Please go to {authorization_url} and authorize access.')
authorization_response = input('Paste the full redirect URL here: ')

# Step 2: Exchange authorization grant for access token
oauth.fetch_token(token_url, authorization_response=authorization_response, auth=HTTPBasicAuth(client_id, client_secret))

# Step 3: Make a request to the API
api_url = 'https://api.github.com/user'
response = oauth.get(api_url)

if response.status_code == 200:
    user_data = response.json()
    print(f'Successfully authenticated as {user_data["login"]}.')
else:
    print(f'Failed to authenticate. Status code: {response.status_code}, Message: {response.text}')
