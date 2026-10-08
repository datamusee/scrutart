"""Application de TEST minimale, SANS contrôle d'accès, avec diagnostics détaillés.

But : vérifier sur o2switch que l'arrêt / démarrage / redémarrage d'une autre
application Python (déclarée dans « Setup Python App ») fonctionne, et sinon
comprendre pourquoi. À supprimer dès le test terminé.

Variable d'environnement (définie dans Setup Python App) :
  CIBLE_APP_ROOT : dossier de l'application à piloter, relatif au dossier
                   personnel, tel qu'affiché dans Setup Python App (ex. "scrutart").

Les valeurs des variables d'environnement des applications ne sont jamais
affichées (seulement leurs noms), car la page n'est pas protégée.
"""
import getpass
import html
import json
import os
import shutil
import sys
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, request

app = Flask(__name__)

ICI = Path(__file__).resolve().parent
JOURNAL = ICI / "diagnostic.log"
HOME = Path(os.environ.get("HOME") or Path.home())
FICHIER_CIBLE = ICI / "cible.txt"
SELECTOR = shutil.which("cloudlinux-selector") or "/usr/sbin/cloudlinux-selector"
ACTIONS = ("start", "stop", "restart")
MASQUE = "***masqué***"


# ------------------------------------------------------------------ outils

def lire_cible():
    """Renvoie (valeur brute, source) de CIBLE_APP_ROOT.

    Les variables saisies dans Setup Python App sont écrites dans .htaccess
    (SetEnv) : selon la configuration, Passenger les place dans os.environ ou
    seulement dans l'environnement WSGI de chaque requête (request.environ).
    On cherche donc aux deux endroits, puis dans le fichier cible.txt.
    """
    if os.environ.get("CIBLE_APP_ROOT"):
        return os.environ["CIBLE_APP_ROOT"], "os.environ"
    try:
        valeur = request.environ.get("CIBLE_APP_ROOT")
    except RuntimeError:  # hors requête
        valeur = None
    if valeur:
        return valeur, "request.environ (SetEnv du .htaccess)"
    if FICHIER_CIBLE.exists():
        return FICHIER_CIBLE.read_text(encoding="utf-8").strip(), f"fichier {FICHIER_CIBLE}"
    return None, None


def nom_cible():
    return (lire_cible()[0] or "").strip().strip("/")


def htaccess_mentionnant(nom):
    """Lignes des .htaccess du compte qui mentionnent la variable."""
    trouve = []
    for motif in (".htaccess", "*/.htaccess", "public_html/*/.htaccess", "*/public_html/.htaccess"):
        for f in HOME.glob(motif):
            try:
                for n, ligne in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if nom in ligne:
                        trouve.append(f"{f}:{n}: {ligne.strip()}")
            except OSError as ex:
                trouve.append(f"{f}: illisible ({ex})")
    return "\n".join(trouve) or "aucun .htaccess ne mentionne " + nom


def bloc_env_htaccess():
    """Contexte autour du bloc de variables CloudLinux dans le .htaccess (noms seulement)."""
    sorties = []
    for motif in (".htaccess", "*/.htaccess", "public_html/*/.htaccess", "*/public_html/.htaccess"):
        for f in HOME.glob(motif):
            try:
                lignes = f.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            if not any("CIBLE_APP_ROOT" in l or "testControleMinimal" in l for l in lignes):
                continue
            extrait = []
            for l in lignes:
                l = l.strip()
                if l.startswith(("SetEnv", "PassengerEnvVar")):
                    morceaux = l.split(None, 2)
                    l = " ".join(morceaux[:2]) + (" <valeur>" if len(morceaux) > 2 and morceaux[1] != "CIBLE_APP_ROOT"
                                                  else (" " + morceaux[2] if len(morceaux) > 2 else ""))
                if l.startswith(("#", "<", "SetEnv", "PassengerEnvVar", "Passenger")):
                    extrait.append(l)
            sorties.append(f"--- {f}\n" + "\n".join(extrait))
    return "\n".join(sorties) or "aucun .htaccess pertinent trouvé"

def journaliser(texte):
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n{texte}\n")


def env_propre():
    """Environnement pour cloudlinux-selector : sans les variables du virtualenv
    de cette application (PYTHONPATH, VIRTUAL_ENV...), qui peuvent le perturber,
    car il est lui-même écrit en Python."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("PYTHON") and k not in ("VIRTUAL_ENV", "PASSENGER_APP_ENV")}
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin"
    env.setdefault("HOME", str(HOME))
    env.setdefault("USER", getpass.getuser())
    return env


def executer(args, mode_env="propre", delai=180):
    """Exécute une commande et renvoie un dict détaillé (jamais d'exception)."""
    env = env_propre() if mode_env == "propre" else dict(os.environ)
    debut = time.time()
    r = {"commande": " ".join(args), "mode_env": mode_env}
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=delai, env=env)
        r.update(code=res.returncode, stdout=res.stdout, stderr=res.stderr)
    except FileNotFoundError as e:
        r.update(code=None, exception=f"Programme introuvable : {e}")
    except PermissionError as e:
        r.update(code=None, exception=f"Permission refusée : {e}")
    except subprocess.TimeoutExpired:
        r.update(code=None, exception=f"Délai dépassé ({delai} s)")
    except Exception as e:
        r.update(code=None, exception=f"{type(e).__name__}: {e}")
    r["duree"] = f"{time.time() - debut:.1f} s"
    try:
        r["json"] = json.loads(r.get("stdout") or "")
    except ValueError:
        r["json"] = None
    return r


def masquer(noeud, cle=""):
    """Remplace les valeurs des variables d'environnement par leurs seuls noms."""
    if "env" in cle.lower() and isinstance(noeud, dict):
        return {k: MASQUE for k in noeud}
    if isinstance(noeud, dict):
        return {k: masquer(v, k) for k, v in noeud.items()}
    if isinstance(noeud, list):
        return [masquer(v, cle) for v in noeud]
    return noeud


def masquer_texte(r):
    """Version de stdout affichable (JSON masqué si possible)."""
    if r.get("json") is not None:
        return json.dumps(masquer(r["json"]), indent=2, ensure_ascii=False)
    return r.get("stdout", "")


def applications(donnees, chemin=""):
    """Trouve dans la sortie de `cloudlinux-selector get` toutes les applications
    (dictionnaires contenant 'app_status'), avec leur clé (= app_root)."""
    trouve = []
    if isinstance(donnees, dict):
        for k, v in donnees.items():
            if isinstance(v, dict) and "app_status" in v:
                trouve.append((k, v))
            else:
                trouve += applications(v, f"{chemin}/{k}")
    elif isinstance(donnees, list):
        for v in donnees:
            trouve += applications(v, chemin)
    return trouve


def url_app(info):
    domaine = info.get("domain")
    if not domaine:
        return None
    return f"https://{domaine}/{(info.get('app_uri') or '').strip('/')}"


def test_http(url):
    if not url:
        return "pas d'URL connue"
    req = urllib.request.Request(url, headers={"Cache-Control": "no-cache",
                                                "User-Agent": "testControleMinimal"})
    debut = time.time()
    try:
        with urllib.request.urlopen(req, timeout=20) as rep:
            corps = rep.read(300).decode("utf-8", "replace")
            return f"HTTP {rep.status} en {time.time() - debut:.1f} s — début : {corps[:150]!r}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} en {time.time() - debut:.1f} s"
    except Exception as e:
        return f"injoignable : {type(e).__name__}: {e}"


def processus(app_root):
    """Processus de l'utilisateur dont la ligne de commande mentionne l'application."""
    r = executer(["ps", "-u", getpass.getuser(), "-o", "pid,etime,args"], delai=15)
    lignes = (r.get("stdout") or "").splitlines()
    if not lignes:
        return f"ps indisponible : {r.get('exception') or r.get('stderr')}"
    entete, corps = lignes[0], lignes[1:]
    utiles = [l for l in corps if app_root and app_root in l and "ps -u" not in l]
    return "\n".join([entete] + utiles) if utiles else f"aucun processus contenant « {app_root} »"


def etat_cible(app_root):
    """Statut selon cloudlinux-selector + processus + réponse HTTP."""
    r = executer([SELECTOR, "get", "--json", "--interpreter", "python"])
    apps = dict(applications(r.get("json")))
    info = apps.get(app_root)
    return {
        "statut": info.get("app_status") if info else "application non trouvée dans `get`",
        "http": test_http(url_app(info)) if info else "-",
        "processus": processus(app_root),
    }


# ------------------------------------------------------------------ affichage

def e(x):
    return html.escape(str(x))


def bloc_commande(r):
    ok = r.get("code") == 0
    resultat_json = (r.get("json") or {}).get("result") if isinstance(r.get("json"), dict) else None
    lignes = [
        f"<p><b>$ {e(r['commande'])}</b> <small>(environnement {e(r['mode_env'])}, {e(r['duree'])})</small></p>",
        f"<p>code retour : <b class='{'ok' if ok else 'ko'}'>{e(r.get('code'))}</b>"
        + (f" — champ result : <b>{e(resultat_json)}</b>" if resultat_json else "") + "</p>",
    ]
    if r.get("exception"):
        lignes.append(f"<p class='ko'>Exception : {e(r['exception'])}</p>")
    if isinstance(r.get("json"), dict) and r["json"].get("result") not in (None, "success"):
        lignes.append(f"<p class='ko'>Message du sélecteur : {e(r['json'].get('result'))}</p>")
    lignes.append(f"<details open><summary>stdout</summary><pre>{e(masquer_texte(r)) or '(vide)'}</pre></details>")
    lignes.append(f"<details open><summary>stderr</summary><pre>{e(r.get('stderr')) or '(vide)'}</pre></details>")
    return "\n".join(lignes)


def section_environnement():
    brute, source = lire_cible()
    CIBLE = nom_cible()
    dossier = HOME / CIBLE if CIBLE else None
    noms_os = sorted(k for k in os.environ if "CIBLE" in k)
    noms_req = sorted(k for k in request.environ if "CIBLE" in k)
    sel = Path(SELECTOR)
    lignes = [
        ("Utilisateur", f"{getpass.getuser()} (uid {os.getuid()})"),
        ("HOME", HOME),
        ("Dossier de cette app", ICI),
        ("Python", sys.executable),
        ("PATH", os.environ.get("PATH")),
        ("CIBLE_APP_ROOT (brut)", repr(brute) if brute is not None
         else "NON DÉFINIE — voir les lignes suivantes ; contournement : créer le fichier cible.txt"),
        ("Source de la valeur", source or "-"),
        ("Variables *CIBLE* dans os.environ", noms_os or "aucune"),
        ("Variables *CIBLE* dans request.environ", noms_req or "aucune"),
        ("Fichier cible.txt (secours)", f"{FICHIER_CIBLE} — {'présent' if FICHIER_CIBLE.exists() else 'absent'}"),
        ("CIBLE_APP_ROOT (normalisé)", repr(CIBLE)),
        ("Dossier cible", f"{dossier} — {'existe' if dossier and dossier.is_dir() else 'INTROUVABLE'}"
         if dossier else "-"),
        ("passenger_wsgi.py dans la cible", (dossier / "passenger_wsgi.py").exists() if dossier else "-"),
        ("cloudlinux-selector", f"{SELECTOR} — existe : {sel.exists()}, exécutable : {os.access(sel, os.X_OK)}"),
    ]
    return "<table>" + "".join(f"<tr><th>{e(a)}</th><td>{e(b)}</td></tr>" for a, b in lignes) + "</table>"


def section_applications(r):
    CIBLE = nom_cible()
    apps = applications(r.get("json"))
    if not apps:
        return "<p class='ko'>Aucune application trouvée dans la sortie de <code>get</code> (voir la sortie brute plus bas).</p>"
    lignes = ["<table><tr><th>app_root</th><th>statut</th><th>URL</th><th>startup</th><th>python</th><th></th></tr>"]
    for racine, info in apps:
        cible = racine.strip("/") == CIBLE
        boutons = " ".join(
            f"<form method='post' action='/action'><input type='hidden' name='app_root' value='{e(racine)}'>"
            f"<input type='hidden' name='action' value='{a}'><button>{a}</button></form>" for a in ACTIONS)
        lignes.append(
            f"<tr class='{'cible' if cible else ''}'><td>{e(racine)}{' ◀ CIBLE' if cible else ''}</td>"
            f"<td>{e(info.get('app_status'))}</td><td>{e(url_app(info))}</td>"
            f"<td>{e(info.get('startup_file'))}:{e(info.get('entry_point'))}</td>"
            f"<td>{e(info.get('python_version'))}</td><td>{boutons}</td></tr>")
    lignes.append("</table>")
    if CIBLE and not any(rac.strip("/") == CIBLE for rac, _ in apps):
        proches = [rac for rac, _ in apps if CIBLE.lower() in rac.lower() or rac.lower() in CIBLE.lower()]
        lignes.append(f"<p class='ko'>CIBLE_APP_ROOT={CIBLE!r} ne correspond à AUCUNE application ci-dessus. "
                      f"La valeur doit être exactement celle de la colonne app_root."
                      + (f" Valeurs proches : {e(', '.join(proches))}" if proches else "") + "</p>")
    return "\n".join(lignes)


def page(contenu):
    return f"""<!doctype html><html lang="fr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Test contrôle</title>
<style>
body{{font:15px/1.4 system-ui,sans-serif;margin:16px;max-width:1100px}}
table{{border-collapse:collapse;margin:8px 0}} th,td{{border:1px solid #ccc;padding:4px 8px;text-align:left;vertical-align:top}}
pre{{background:#f4f4f4;padding:8px;overflow:auto;max-height:420px;white-space:pre-wrap}}
.ok{{color:#1a7f37}} .ko{{color:#c62828;font-weight:bold}} tr.cible{{background:#fff6d6}}
form{{display:inline}} h2{{margin-top:28px;border-bottom:1px solid #ccc}}
</style>
<p><a href="/">↻ Recharger le diagnostic</a> — <a href="/journal">journal</a></p>
{contenu}</html>"""


# ------------------------------------------------------------------ routes

@app.route("/")
def accueil():
    r = executer([SELECTOR, "get", "--json", "--interpreter", "python"])
    contenu = [
        "<h1>Diagnostic de pilotage</h1>",
        "<h2>1. Environnement</h2>", section_environnement(),
        "<h2>1 bis. .htaccess mentionnant CIBLE_APP_ROOT</h2>",
        f"<pre>{e(htaccess_mentionnant('CIBLE_APP_ROOT'))}</pre>",
        "<details><summary>Configuration Passenger / variables dans ces .htaccess "
        "(valeurs des autres variables masquées)</summary>",
        f"<pre>{e(bloc_env_htaccess())}</pre></details>",
        "<h2>2. Applications vues par cloudlinux-selector</h2>", section_applications(r),
    ]
    CIBLE = nom_cible()
    if CIBLE:
        contenu += [f"<h2>3. Cible « {e(CIBLE)} » : processus</h2><pre>{e(processus(CIBLE))}</pre>"]
    contenu += [
        "<h2>4. Commande <code>get</code> brute</h2>", bloc_commande(r),
        "<h2>5. Test de cloudlinux-selector avec l'environnement non nettoyé</h2>",
        "<p>Si cette commande échoue alors que celle du §4 réussit (ou l'inverse), "
        "c'est l'environnement Python de cette application qui perturbe le sélecteur.</p>",
        bloc_commande(executer([SELECTOR, "get", "--json", "--interpreter", "python"], mode_env="brut")),
    ]
    return page("\n".join(contenu))


@app.route("/action", methods=["POST"])
def action():
    action = request.form.get("action")
    app_root = request.form.get("app_root", "")
    if action not in ACTIONS:
        abort(400)
    # n'accepte que les app_root effectivement déclarés (pas d'argument arbitraire)
    connues = [rac for rac, _ in applications(
        executer([SELECTOR, "get", "--json", "--interpreter", "python"]).get("json"))]
    if app_root not in connues:
        abort(400, f"app_root inconnu : {app_root!r}")

    avant = etat_cible(app_root)
    r = executer([SELECTOR, action, "--json", "--interpreter", "python", "--app-root", app_root])
    time.sleep(3)
    apres = etat_cible(app_root)

    texte = (f"ACTION {action} sur {app_root}\n$ {r['commande']}\ncode={r.get('code')} durée={r['duree']}\n"
             f"exception={r.get('exception')}\nstdout=\n{masquer_texte(r)}\nstderr=\n{r.get('stderr')}\n"
             f"AVANT : {avant}\nAPRÈS : {apres}")
    journaliser(texte)

    def tableau(etat):
        return ("<table>" + "".join(f"<tr><th>{k}</th><td><pre>{e(v)}</pre></td></tr>" for k, v in etat.items())
                + "</table>")

    changement = avant["statut"] != apres["statut"]
    return page("\n".join([
        f"<h1>{e(action)} sur « {e(app_root)} »</h1>",
        f"<p class='{'ok' if changement else 'ko'}'>Statut selon le sélecteur : "
        f"{e(avant['statut'])} → {e(apres['statut'])}"
        f"{'' if changement else ' (inchangé)'}</p>",
        "<h2>Avant</h2>", tableau(avant),
        "<h2>Commande</h2>", bloc_commande(r),
        "<h2>Après (3 s plus tard)</h2>", tableau(apres),
        "<p>Note : après un <b>stop</b>, la réponse HTTP de la cible devrait changer (erreur, page "
        "par défaut ou liste du dossier). Si elle ne change pas, vérifier le cache du navigateur "
        "et le fichier .htaccess du dossier racine du domaine.</p>",
    ]))


@app.route("/journal")
def journal():
    contenu = JOURNAL.read_text(encoding="utf-8")[-50000:] if JOURNAL.exists() else "(vide)"
    return page(f"<h1>Journal ({e(JOURNAL)})</h1><pre>{e(contenu)}</pre>")
