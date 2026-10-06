"""Chargement et validation de la configuration de l'application de contrôle.

La configuration est un fichier JSON situé HORS de public_html (par défaut
~/.config/controle_app/config.json, ou le chemin donné par la variable
d'environnement CONTROLE_CONFIG). Il contient des secrets : il doit être
lisible uniquement par son propriétaire (chmod 600).
"""
import json
import os
import stat
from pathlib import Path

CHEMIN_DEFAUT = Path.home() / ".config" / "controle_app" / "config.json"

BACKENDS = {"cloudlinux", "passenger", "process"}


class ErreurConfiguration(Exception):
    pass


def chemin_config():
    return Path(os.environ.get("CONTROLE_CONFIG", CHEMIN_DEFAUT)).expanduser()


def verifier_permissions(chemin):
    """Refuse un fichier de configuration lisible par le groupe ou les autres."""
    mode = chemin.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ErreurConfiguration(
            f"{chemin} est accessible au groupe ou aux autres utilisateurs "
            f"(mode {oct(mode & 0o777)}). Faites : chmod 600 {chemin}"
        )


def valider(conf):
    for cle in ("secret_key", "username", "password_hash", "totp_secret", "targets"):
        if not conf.get(cle):
            raise ErreurConfiguration(f"Clé de configuration manquante : {cle}")
    if len(conf["secret_key"]) < 32:
        raise ErreurConfiguration("secret_key trop courte (32 caractères minimum)")
    for nom, cible in conf["targets"].items():
        backend = cible.get("backend")
        if backend not in BACKENDS:
            raise ErreurConfiguration(f"Cible {nom} : backend inconnu {backend!r}")
        if backend in ("cloudlinux", "passenger") and not cible.get("app_root"):
            raise ErreurConfiguration(f"Cible {nom} : app_root requis")
        if backend == "process":
            if not isinstance(cible.get("command"), list) or not cible["command"]:
                raise ErreurConfiguration(f"Cible {nom} : command doit être une liste non vide")
            if not cible.get("pid_file"):
                raise ErreurConfiguration(f"Cible {nom} : pid_file requis")
    return conf


def charger(chemin=None, verifier_droits=True):
    chemin = Path(chemin) if chemin else chemin_config()
    if not chemin.exists():
        raise ErreurConfiguration(
            f"Fichier de configuration introuvable : {chemin}. "
            f"Lancez : python gestion.py init"
        )
    if verifier_droits:
        verifier_permissions(chemin)
    with open(chemin, encoding="utf-8") as f:
        conf = json.load(f)
    conf.setdefault("allowed_ips", [])
    conf.setdefault("trust_proxy", False)
    conf.setdefault("session_idle_minutes", 10)
    conf.setdefault("session_max_minutes", 60)
    conf.setdefault("max_echecs_ip", 5)
    conf.setdefault("max_echecs_global", 20)
    conf.setdefault("fenetre_echecs_minutes", 15)
    conf.setdefault("data_dir", str(chemin.parent))
    return valider(conf)
