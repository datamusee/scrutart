"""Outil en ligne de commande (à lancer en SSH sur le serveur).

  python gestion.py init            crée le fichier de configuration (secrets, mot de passe, TOTP)
  python gestion.py mot-de-passe    change le mot de passe
  python gestion.py totp            régénère le secret TOTP
  python gestion.py verifier        vérifie la configuration et affiche le statut des cibles
"""
import argparse
import getpass
import json
import os
import secrets
import sys

from werkzeug.security import generate_password_hash

import config as config_mod
from backends import ErreurBackend, creer_backend
from securite import nouveau_secret_totp, uri_totp

LONGUEUR_MIN_MDP = 14

EXEMPLE_CIBLES = {
    "monapp": {
        "label": "Mon application",
        "backend": "cloudlinux",
        "app_root": "monapp",
        "health_url": "https://monapp.mondomaine.fr/",
    }
}


def demander_mot_de_passe():
    while True:
        mdp = getpass.getpass(f"Mot de passe ({LONGUEUR_MIN_MDP} caractères minimum) : ")
        if len(mdp) < LONGUEUR_MIN_MDP:
            print("Trop court.")
            continue
        if mdp != getpass.getpass("Confirmation : "):
            print("Les deux saisies diffèrent.")
            continue
        return generate_password_hash(mdp)


def afficher_totp(secret, utilisateur):
    print("\nAjoutez ce compte dans votre application d'authentification")
    print("(Aegis, FreeOTP, Google Authenticator, Bitwarden...) :")
    print(f"  secret : {secret}")
    print(f"  URI    : {uri_totp(secret, utilisateur)}")
    print("Ne conservez pas ces valeurs ailleurs que dans l'application.\n")


def ecrire(chemin, conf):
    chemin.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2, ensure_ascii=False)
    os.chmod(chemin, 0o600)
    print(f"Configuration écrite dans {chemin} (droits 600)")


def lire_brut(chemin):
    config_mod.verifier_permissions(chemin)
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def cmd_init(chemin):
    if chemin.exists():
        sys.exit(f"{chemin} existe déjà ; utilisez les commandes mot-de-passe / totp.")
    utilisateur = input("Identifiant administrateur : ").strip()
    if not utilisateur:
        sys.exit("Identifiant vide.")
    conf = {
        "secret_key": secrets.token_urlsafe(48),
        "username": utilisateur,
        "password_hash": demander_mot_de_passe(),
        "totp_secret": nouveau_secret_totp(),
        "allowed_ips": [],
        "trust_proxy": False,
        "session_idle_minutes": 10,
        "session_max_minutes": 60,
        "targets": EXEMPLE_CIBLES,
    }
    ecrire(chemin, conf)
    afficher_totp(conf["totp_secret"], utilisateur)
    print(f"Éditez maintenant la section \"targets\" de {chemin} pour décrire votre application.")


def cmd_mot_de_passe(chemin):
    conf = lire_brut(chemin)
    conf["password_hash"] = demander_mot_de_passe()
    # Changer la clé secrète invalide toutes les sessions ouvertes.
    conf["secret_key"] = secrets.token_urlsafe(48)
    ecrire(chemin, conf)


def cmd_totp(chemin):
    conf = lire_brut(chemin)
    conf["totp_secret"] = nouveau_secret_totp()
    conf["secret_key"] = secrets.token_urlsafe(48)
    ecrire(chemin, conf)
    afficher_totp(conf["totp_secret"], conf["username"])


def cmd_verifier(chemin):
    conf = config_mod.charger(chemin)
    print("Configuration valide.")
    for nom, cible in conf["targets"].items():
        backend = creer_backend(cible)
        try:
            statut = backend.statut()
        except ErreurBackend as e:
            statut = f"erreur : {e}"
        print(f"  {nom} [{cible['backend']}] : {statut} — actions : {', '.join(backend.actions)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("commande", choices=["init", "mot-de-passe", "totp", "verifier"])
    parser.add_argument("--config", help="chemin du fichier de configuration")
    args = parser.parse_args()
    chemin = config_mod.chemin_config() if not args.config else config_mod.Path(args.config).expanduser()
    {"init": cmd_init, "mot-de-passe": cmd_mot_de_passe,
     "totp": cmd_totp, "verifier": cmd_verifier}[args.commande](chemin)


if __name__ == "__main__":
    main()
