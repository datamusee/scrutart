"""Briques de sécurité : TOTP (RFC 6238), limitation des tentatives, journal d'audit.

L'état partagé (échecs de connexion, codes TOTP déjà utilisés) est stocké dans
une base SQLite, car Passenger peut faire tourner plusieurs processus.
"""
import base64
import hashlib
import hmac
import secrets
import sqlite3
import struct
import time
from contextlib import closing
from pathlib import Path
from urllib.parse import quote

PERIODE_TOTP = 30


# ---------------------------------------------------------------- TOTP

def nouveau_secret_totp():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def _code_totp(secret, pas):
    cle = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    mac = hmac.new(cle, struct.pack(">Q", pas), hashlib.sha1).digest()
    decalage = mac[-1] & 0x0F
    valeur = struct.unpack(">I", mac[decalage:decalage + 4])[0] & 0x7FFFFFFF
    return f"{valeur % 1_000_000:06d}"


def code_totp_courant(secret, instant=None):
    return _code_totp(secret, int((instant or time.time()) // PERIODE_TOTP))


def verifier_totp(secret, code, instant=None, tolerance=1):
    """Renvoie le pas de temps correspondant au code, ou None.

    Accepte une dérive d'horloge de ±tolerance pas de 30 s.
    """
    code = (code or "").strip().replace(" ", "")
    if len(code) != 6 or not code.isdigit():
        return None
    pas_courant = int((instant or time.time()) // PERIODE_TOTP)
    trouve = None
    for pas in range(pas_courant - tolerance, pas_courant + tolerance + 1):
        if hmac.compare_digest(_code_totp(secret, pas), code):
            trouve = pas
    return trouve


def uri_totp(secret, utilisateur, emetteur="ControleApp"):
    return (f"otpauth://totp/{quote(emetteur)}:{quote(utilisateur)}"
            f"?secret={secret}&issuer={quote(emetteur)}&digits=6&period={PERIODE_TOTP}")


# ---------------------------------------------------------------- état partagé

class EtatSecurite:
    def __init__(self, data_dir):
        Path(data_dir).mkdir(parents=True, exist_ok=True, mode=0o700)
        self.chemin = Path(data_dir) / "securite.sqlite3"
        with closing(self._connexion()) as cx, cx:
            cx.execute("CREATE TABLE IF NOT EXISTS echecs (ip TEXT, instant REAL)")
            cx.execute("CREATE TABLE IF NOT EXISTS totp (id INTEGER PRIMARY KEY CHECK (id = 1), dernier_pas INTEGER)")
        self.chemin.chmod(0o600)

    def _connexion(self):
        return sqlite3.connect(self.chemin, timeout=10)

    def nb_echecs(self, fenetre_s, ip=None):
        limite = time.time() - fenetre_s
        with closing(self._connexion()) as cx:
            if ip is None:
                (n,) = cx.execute("SELECT COUNT(*) FROM echecs WHERE instant > ?", (limite,)).fetchone()
            else:
                (n,) = cx.execute("SELECT COUNT(*) FROM echecs WHERE instant > ? AND ip = ?",
                                  (limite, ip)).fetchone()
        return n

    def noter_echec(self, ip):
        with closing(self._connexion()) as cx, cx:
            cx.execute("INSERT INTO echecs VALUES (?, ?)", (ip, time.time()))
            cx.execute("DELETE FROM echecs WHERE instant < ?", (time.time() - 86400,))

    def effacer_echecs(self, ip):
        with closing(self._connexion()) as cx, cx:
            cx.execute("DELETE FROM echecs WHERE ip = ?", (ip,))

    def consommer_pas_totp(self, pas):
        """Enregistre le pas TOTP utilisé ; refuse la réutilisation d'un code (rejeu)."""
        with closing(self._connexion()) as cx, cx:
            cx.execute("BEGIN IMMEDIATE")
            ligne = cx.execute("SELECT dernier_pas FROM totp WHERE id = 1").fetchone()
            if ligne and pas <= ligne[0]:
                return False
            cx.execute("INSERT OR REPLACE INTO totp VALUES (1, ?)", (pas,))
            return True
