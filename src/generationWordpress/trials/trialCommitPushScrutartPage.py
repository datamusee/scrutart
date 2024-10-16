"""
but
tester le commit puis le push vers
https://github.com/datamusee/scrutart
de pages
et la récupération de pages avec gestion des différences et alerte sur les modifications 'externes' exemple: manuelles
afin d'automatiser le process en sécurisant les versions et en repérant les améliorations manuelles sur certaines pages
en vue de les généraliser

trial inspiré de https://thepythoncode.com/article/using-github-api-in-python
mais a échoué sur create_file
nouvelle inspiration
https://devopslearning.medium.com/day-13-101-days-of-devops-github-api-using-python-and-pygithub-module-c1bcbaaeada7
mais ça ne dit rien sur les commits, essentiellement des choses pour créer, détruire, parcourir les repositories

utilisé
https://stackoverflow.com/questions/71887432/how-to-append-to-a-file-using-pygithub
"""
import requests
from pprint import pprint
import base64
from github import Github, InputGitAuthor, Auth
from pprint import pprint
from ..configPrivee import TOKEN_GITHUB

token = TOKEN_GITHUB # limité au 14 juillet 2024......

def print_repo(repo):
    # repository full name
    print("Full name:", repo.full_name)
    # repository description
    print("Description:", repo.description)
    # the date of when the repo was created
    print("Date created:", repo.created_at)
    # the date of the last git push
    print("Date of last push:", repo.pushed_at)
    # home website (if available)
    print("Home Page:", repo.homepage)
    # programming language
    print("Language:", repo.language)
    # number of forks
    print("Number of forks:", repo.forks)
    # number of stars
    print("Number of stars:", repo.stargazers_count)
    print("-"*50)
    # repository content (files & directories)
    #print("Contents:")
    #for content in repo.get_contents(""): # echoue sur un repository vide
    #    print(content)
    try:
        # repo license
        print("License:", base64.b64decode(repo.get_license().content.encode()).decode())
    except:
        pass

git = Github(token)
repo = git.get_repo("datamusee/scrutart")
file = repo.get_contents("README.md", ref="main")

repo.update_file(file.path, "troisième test", "J'aimerais créer un dossier", file.sha, branch="main")
# tentative de création de fichier
repo.update_file("dossierTest/fichierTest", "test de création", "Problème avec le sha?", file.sha, branch="main")
# github username
username = "datamusee"
password = "qjaafccnuasqjaafccnuas"
# url to request
url = f"https://api.github.com/users/{username}"
# make the request and return the json
user_data = requests.get(url).json()
# pretty print JSON data
pprint(user_data)

# pygithub object
auth = Auth.Login("user_login", "password")
g = Github(auth=auth)
# get that user
user = g.get_user()

