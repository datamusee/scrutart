# D:\wamp64\www\givingsense.eu\datamusee\python\datamusee\generationDocuments\generationWordpress\flaskServerClallbackOAuth2.py
# doit être lancé avant de lancer ce code

import time

import feedparser  # pare flux rss
import os
import json
import tweepy  # library twitter
import requests
from requests.auth import HTTPBasicAuth
from requests.auth import AuthBase, HTTPBasicAuth
from requests_oauthlib import OAuth2Session, TokenUpdated
from openai import OpenAI
from openai._exceptions import  APIError, RateLimitError, APITimeoutError
import configPrivee
from bs4 import BeautifulSoup


last_checked_entry_file = configPrivee.LAST_ENTRY_LINK

import os
from pprint import pprint
import requests


auth = tweepy.OAuth1UserHandler(
    consumer_key=configPrivee.twitter_consumer_key, consumer_secret=configPrivee.twitter_consumer_secret,
    access_token=configPrivee.twitter_access_token, access_token_secret=configPrivee.twitter_access_secret
)
print(auth.get_authorization_url())
# Enter that PIN to continue
verifier = input("PIN: ")

auth.get_access_token(verifier)

api = tweepy.API(auth)
api.update_status("test de tweet")
print(api.verify_credentials().screen_name)

#client.create_tweet(text="test de tweet", user_auth=True)

params = {'ids': ['1588915242490560512']}
headers = {'Authorization': f"Bearer {configPrivee.twitter_bearer_token}"}
r = requests.get('https://api.twitter.com/2/tweets', params=params, headers=headers)
pprint(r.json())

def save_las_checked_entry(entrylink):
    with open(last_checked_entry_file, "w") as filecheck:
        json.dump(entrylink, filecheck)

def create_tweepy_client():
    return tweepy.Client(#bearer_token=configPrivee.twitter_bearer_token,
                         consumer_key=configPrivee.twitter_consumer_key,
                         consumer_secret=configPrivee.twitter_consumer_secret,
                         access_token=configPrivee.twitter_access_token,
                         access_token_secret=configPrivee.twitter_access_secret)

def load_last_checked_entry():
    if os.path.exists(last_checked_entry_file):
        with open(last_checked_entry_file, "r") as filecheck:
            try:
                return json.load(filecheck)
            except json.JSONDecodeError:
                print("erreur de décodage du fichier json de dernière entrée consultée")
    return None


def print_entry_details(last_entry):
    print("Post title {}".format(last_entry.title))
    pass

def publish_tweet(client, response, entry):
    content = response.choices[0].message.content
    content = content.strip('\"')
    soup = BeautifulSoup(entry.content[0]['value'], features="html.parser")
    text = soup.get_text()
    tweet = content + " " + entry.link
    print(tweet)
    if configPrivee.SHOULD_TWEET:
        response = client.create_tweet(text=tweet)

def create_chat_messages(entry):
    content = entry.content[0]['value']
    # s'il y a une image, la virer
    if "<figure" in content:
        figureend = content.find("</figure>")+len("</figure>")
        if figureend:
            content = content[figureend:]
    # virer les liens
    while "<a " in content:
        astart = content.find("<a ")
        aend = content.find("</a>", astart)
        content = content[0:astart]+content[aend:]
    return [
        {"role":"system", "content":"Tu es Grains, un expert des graphes de connaissances pour l'héritage culturel français qui vulgarise son savoir"},
        {"role":"assistant","content":"Understood, I am an AI trained to generate tweet in French, maintaining the author's style"},
        {"role":"user","content":"Depuis le texte ci-après, écrit un tweet en français, dans le style de l'auteur, à la première personne, au masculin singulier"},
        {"role": "assistant", "content": "Bien sûr. je peux le faire. Merci de me donner le texte."},
        {"role":"user","content":"Je veux que le tweet incite à cliquer. Le style doit être motivant, positif, et donne envie d'en savoir plus, mais sans emphase. Ajoute des emojis si ça te parait pertinent"},
        {"role": "assistant", "content": "Compris. Je vais créer un tweet engageant et positif."},
        {"role": "user", "content": "Mets trois hashtags à la fin."},
        {"role": "assistant", "content": "C'est bon, je vais mettre trois hashtags à la fin du tweet."},
        {"role": "user", "content": "La taille finale du tweet (texte+hashtags) doit être moins que 116 caractères."},
        {"role": "assistant", "content": "Compris, je vais m'assurer que la longueur du tweet, incluant les hashtags, fait moins que 116 caractères."},
        {"role": "user", "content": f"Voilà le texte:\n====\n titre : \n {entry.title} \n texte : \n {content}\n ===="},
        {"role": "assistant", "content": "Merci, je vais générer le tweet."}
    ]


def generate_tweet(chat_messages):
    try:
        openaiclient = OpenAI(
            api_key=configPrivee.OPENAI_API_KEY
        )
        return openaiclient.chat.completions.create(
            model= "gpt-4", # "gpt-3.5-turbo",
            temperature=1,
            top_p=1.0,
            frequency_penalty=0,
            presence_penalty=0,
            messages=chat_messages
        )
    except APITimeoutError as e:
        print(f"Erreur: {e} Réessayer...")
    except RateLimitError as e:
        print(f"Erreur: attendre avant de réessayer {e} ")
        wait_time = 60 # int(e.headers.get('Retry-After', 60))
        time.sleep(wait_time)


def check_feed(client):
    NewsFeed = feedparser.parse("https://datamusee.wp.imt.fr/fr/feed/")
    last_entry = NewsFeed.entries[0]
    last_checked_entry = load_last_checked_entry()
    if last_checked_entry is None or last_entry.link != last_checked_entry:
        print_entry_details(last_entry)
        chat_messages = create_chat_messages(last_entry)
        response = generate_tweet(chat_messages)
        publish_tweet(client, response, last_entry)
        save_las_checked_entry(last_entry.link)
    else:
        print("pas de nouvelle entrée du blog")


#client = create_tweepy_client()
#check_feed(client)