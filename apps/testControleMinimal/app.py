"""Application de TEST minimale, SANS contrôle d'accès.

But : vérifier sur o2switch que l'arrêt / démarrage / redémarrage d'une autre
application Python (déclarée dans « Setup Python App ») fonctionne.
À supprimer dès le test terminé : n'importe qui connaissant l'URL peut agir.

Variable d'environnement (à définir dans Setup Python App) :
  CIBLE_APP_ROOT : dossier de l'application à piloter, relatif au dossier
                   personnel, tel qu'affiché dans Setup Python App (ex. "scrutart").
"""
import getpass
import html
import os
import shutil
import subprocess

from flask import Flask, abort

app = Flask(__name__)

APP_ROOT = os.environ.get("CIBLE_APP_ROOT", "scrutart")
SELECTOR = shutil.which("cloudlinux-selector") or "/usr/sbin/cloudlinux-selector"
ACTIONS = ("start", "stop", "restart")


def executer(args):
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=120)
        return f"$ {' '.join(args)}\ncode retour : {res.returncode}\n\n{res.stdout}\n{res.stderr}"
    except Exception as e:
        return f"$ {' '.join(args)}\nERREUR : {type(e).__name__}: {e}"


def page(resultat=""):
    boutons = "".join(
        f'<form method="post" action="/{a}" style="display:inline"><button>{a}</button></form> '
        for a in ACTIONS)
    return f"""<!doctype html><meta charset="utf-8"><title>Test contrôle</title>
<h1>Test de pilotage de « {html.escape(APP_ROOT)} »</h1>
<p>utilisateur : {html.escape(getpass.getuser())} — sélecteur : {html.escape(SELECTOR)}</p>
<p>{boutons} <a href="/">statut</a></p>
<pre>{html.escape(resultat)}</pre>"""


@app.route("/")
def accueil():
    return page(executer([SELECTOR, "get", "--json", "--interpreter", "python"]))


@app.route("/<action>", methods=["POST"])
def piloter(action):
    if action not in ACTIONS:
        abort(404)
    return page(executer([SELECTOR, action, "--json", "--interpreter", "python",
                          "--app-root", APP_ROOT]))
