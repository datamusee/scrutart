"""Application Flask d'administration : arrêt / démarrage / redémarrage d'une
autre application Python hébergée sur le même compte o2switch.

Contrôle d'accès :
- identifiant + mot de passe (haché scrypt/pbkdf2) + code TOTP obligatoire ;
- blocage après trop d'échecs (par IP et global), codes TOTP non rejouables ;
- liste blanche d'adresses IP optionnelle ;
- session courte (inactivité et durée maximale), cookie Secure/HttpOnly/SameSite=Strict ;
- jeton CSRF sur tous les formulaires, actions uniquement en POST ;
- en-têtes de sécurité (CSP stricte, anti-iframe, HSTS, pas de cache) ;
- journal d'audit de toutes les connexions et actions.
"""
import hmac
import ipaddress
import logging
import secrets
import time
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

import config as config_mod
from backends import ErreurBackend, creer_backend, sante_http
from securite import EtatSecurite, verifier_totp

# Haché factice : la vérification du mot de passe prend le même temps
# que l'identifiant soit connu ou non.
HACHE_FACTICE = generate_password_hash(secrets.token_urlsafe(16))

LIBELLES_ACTIONS = {"start": "Démarrer", "stop": "Arrêter", "restart": "Redémarrer"}


def creer_app(conf=None):
    conf = conf or config_mod.charger()
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=conf["secret_key"],
        SESSION_COOKIE_NAME="__Host-controle" if conf.get("cookie_secure", True) else "controle",
        SESSION_COOKIE_SECURE=conf.get("cookie_secure", True),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=conf["session_max_minutes"]),
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if conf["trust_proxy"]:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    etat = EtatSecurite(conf["data_dir"])
    reseaux = [ipaddress.ip_network(r, strict=False) for r in conf["allowed_ips"]]
    cibles = {nom: (c, creer_backend(c)) for nom, c in conf["targets"].items()}

    audit = logging.getLogger("controle.audit")
    for ancien in audit.handlers[:]:
        audit.removeHandler(ancien)
        ancien.close()
    gestionnaire = logging.FileHandler(Path(conf["data_dir"]) / "audit.log", encoding="utf-8")
    gestionnaire.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    audit.addHandler(gestionnaire)
    audit.setLevel(logging.INFO)

    def ip_client():
        return request.remote_addr or "?"

    def journal(message):
        audit.info("ip=%s user=%s %s", ip_client(), session.get("user", "-"), message)

    # ------------------------------------------------------------ filtres globaux

    @app.before_request
    def filtrer_ip():
        if not reseaux:
            return
        try:
            ip = ipaddress.ip_address(ip_client())
        except ValueError:
            abort(403)
        if not any(ip in r for r in reseaux):
            journal("refus: IP hors liste blanche")
            abort(403)

    @app.before_request
    def verifier_csrf():
        if request.method == "POST":
            jeton = session.get("csrf")
            if not jeton or not hmac.compare_digest(jeton, request.form.get("csrf", "")):
                journal("refus: jeton CSRF invalide")
                abort(400)

    @app.context_processor
    def injecter_csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return {"csrf": session["csrf"]}

    @app.after_request
    def entetes_securite(rep):
        rep.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'none'")
        rep.headers["X-Frame-Options"] = "DENY"
        rep.headers["X-Content-Type-Options"] = "nosniff"
        rep.headers["Referrer-Policy"] = "no-referrer"
        rep.headers["Cache-Control"] = "no-store"
        rep.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if conf.get("cookie_secure", True):
            rep.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return rep

    # ------------------------------------------------------------ authentification

    def session_valide():
        if not session.get("user"):
            return False
        maintenant = time.time()
        if (maintenant - session.get("auth_time", 0) > conf["session_max_minutes"] * 60
                or maintenant - session.get("last_seen", 0) > conf["session_idle_minutes"] * 60):
            session.clear()
            return False
        session["last_seen"] = maintenant
        return True

    def connexion_requise(vue):
        @wraps(vue)
        def enveloppe(*args, **kwargs):
            if not session_valide():
                return redirect(url_for("connexion"))
            return vue(*args, **kwargs)
        return enveloppe

    @app.route("/login", methods=["GET", "POST"])
    def connexion():
        if request.method == "GET":
            return render_template("login.html")

        ip = ip_client()
        fenetre = conf["fenetre_echecs_minutes"] * 60
        if (etat.nb_echecs(fenetre, ip) >= conf["max_echecs_ip"]
                or etat.nb_echecs(fenetre) >= conf["max_echecs_global"]):
            journal("refus: trop de tentatives")
            return render_template("login.html",
                                   erreur="Trop de tentatives. Réessayez plus tard."), 429

        utilisateur = request.form.get("username", "")
        mdp = request.form.get("password", "")
        bon_utilisateur = hmac.compare_digest(utilisateur.encode(), conf["username"].encode())
        bon_mdp = check_password_hash(conf["password_hash"] if bon_utilisateur else HACHE_FACTICE, mdp)
        pas = verifier_totp(conf["totp_secret"], request.form.get("totp", ""))

        if not (bon_utilisateur and bon_mdp and pas is not None and etat.consommer_pas_totp(pas)):
            etat.noter_echec(ip)
            audit.info("ip=%s echec de connexion (user=%r)", ip, utilisateur[:64])
            time.sleep(1)
            return render_template("login.html", erreur="Identifiants invalides."), 401

        etat.effacer_echecs(ip)
        session.clear()
        session.permanent = True
        maintenant = time.time()
        session.update(user=utilisateur, auth_time=maintenant, last_seen=maintenant,
                       csrf=secrets.token_urlsafe(32))
        journal("connexion reussie")
        return redirect(url_for("tableau"))

    @app.route("/logout", methods=["POST"])
    def deconnexion():
        journal("deconnexion")
        session.clear()
        return redirect(url_for("connexion"))

    # ------------------------------------------------------------ pilotage

    @app.route("/")
    @connexion_requise
    def tableau():
        lignes = []
        for nom, (cible, backend) in cibles.items():
            try:
                statut = backend.statut()
            except ErreurBackend as e:
                statut = f"erreur : {e}"
            sante = sante_http(cible["health_url"]) if cible.get("health_url") else None
            lignes.append({"nom": nom, "libelle": cible.get("label", nom), "statut": statut,
                           "sante": sante, "actions": [(a, LIBELLES_ACTIONS[a]) for a in backend.actions]})
        return render_template("tableau.html", cibles=lignes)

    @app.route("/cible/<nom>/<action>", methods=["POST"])
    @connexion_requise
    def piloter(nom, action):
        if nom not in cibles:
            abort(404)
        cible, backend = cibles[nom]
        if action not in backend.actions:
            abort(400)
        if action in ("stop", "restart") and request.form.get("confirm") != nom:
            flash(f"Confirmation incorrecte : saisissez « {nom} » pour {LIBELLES_ACTIONS[action].lower()}.",
                  "erreur")
            return redirect(url_for("tableau"))
        journal(f"action={action} cible={nom} demandee")
        try:
            resultat = backend.executer(action)
            journal(f"action={action} cible={nom} ok")
            flash(f"{LIBELLES_ACTIONS[action]} {cible.get('label', nom)} : OK. {resultat[:500]}", "ok")
        except (ErreurBackend, OSError) as e:
            journal(f"action={action} cible={nom} echec: {e}")
            flash(f"{LIBELLES_ACTIONS[action]} {cible.get('label', nom)} : échec. {e}", "erreur")
        return redirect(url_for("tableau"))

    @app.errorhandler(403)
    def interdit(_e):
        return "Accès interdit", 403

    return app
