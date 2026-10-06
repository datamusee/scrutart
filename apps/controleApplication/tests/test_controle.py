import json
import os
import re
import sys
import time
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config as config_mod  # noqa: E402
from app import creer_app  # noqa: E402
from securite import PERIODE_TOTP, code_totp_courant, nouveau_secret_totp, verifier_totp  # noqa: E402

MDP = "un mot de passe tres long"


@pytest.fixture
def conf(tmp_path):
    script = tmp_path / "worker.py"
    script.write_text("import time\nwhile True: time.sleep(1)\n")
    (tmp_path / "web").mkdir()
    return {
        "secret_key": "x" * 48,
        "username": "admin",
        "password_hash": generate_password_hash(MDP),
        "totp_secret": nouveau_secret_totp(),
        "allowed_ips": [],
        "trust_proxy": False,
        "cookie_secure": False,
        "session_idle_minutes": 10,
        "session_max_minutes": 60,
        "max_echecs_ip": 3,
        "max_echecs_global": 20,
        "fenetre_echecs_minutes": 15,
        "data_dir": str(tmp_path),
        "targets": {
            "worker": {"backend": "process", "command": [sys.executable, str(script)],
                       "pid_file": str(tmp_path / "worker.pid")},
            "web": {"backend": "passenger", "app_root": str(tmp_path / "web")},
        },
    }


@pytest.fixture
def client(conf):
    app = creer_app(conf)
    app.config["TESTING"] = True
    c = app.test_client()
    yield c
    # arrêt du worker éventuellement démarré
    pid_file = Path(conf["targets"]["worker"]["pid_file"])
    if pid_file.exists():
        try:
            os.killpg(int(pid_file.read_text()), 9)
        except OSError:
            pass


def jeton(client, url="/login"):
    page = client.get(url).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', page).group(1)


def connecter(client, conf, mdp=MDP, code=None, instant=None):
    return client.post("/login", data={
        "csrf": jeton(client), "username": "admin", "password": mdp,
        "totp": code or code_totp_courant(conf["totp_secret"], instant)})


def test_totp_rfc6238():
    # Vecteur de test RFC 6238 (SHA1, T=59 s) ramené à 6 chiffres
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert code_totp_courant(secret, 59) == "287082"
    assert verifier_totp(secret, "287082", instant=59) is not None
    assert verifier_totp(secret, "287082", instant=59 + 5 * PERIODE_TOTP) is None


def test_acces_refuse_sans_connexion(client):
    assert client.get("/").status_code == 302
    assert client.post("/cible/worker/start", data={}).status_code == 400  # pas de CSRF


def test_connexion_et_pilotage(client, conf):
    assert connecter(client, conf).status_code == 302
    page = client.get("/")
    assert page.status_code == 200
    assert "stopped" in page.get_data(as_text=True)

    t = jeton(client, "/")
    client.post("/cible/worker/start", data={"csrf": t})
    assert "started" in client.get("/").get_data(as_text=True)

    # arrêt sans confirmation : refusé
    client.post("/cible/worker/stop", data={"csrf": t})
    assert "started" in client.get("/").get_data(as_text=True)

    client.post("/cible/worker/stop", data={"csrf": t, "confirm": "worker"})
    assert "stopped" in client.get("/").get_data(as_text=True)

    client.post("/cible/web/restart", data={"csrf": t, "confirm": "web"})
    assert Path(conf["targets"]["web"]["app_root"], "tmp", "restart.txt").exists()

    # action non prévue pour ce backend
    assert client.post("/cible/web/stop", data={"csrf": t, "confirm": "web"}).status_code == 400
    assert client.post("/cible/inconnue/start", data={"csrf": t}).status_code == 404

    audit = Path(conf["data_dir"], "audit.log").read_text()
    assert "connexion reussie" in audit and "action=start cible=worker ok" in audit


def test_mauvais_mot_de_passe_et_blocage(client, conf):
    for _ in range(3):
        assert connecter(client, conf, mdp="faux").status_code == 401
    # même avec les bons identifiants, l'IP est bloquée
    assert connecter(client, conf).status_code == 429


def test_totp_obligatoire_et_non_rejouable(client, conf):
    assert connecter(client, conf, code="abcdef").status_code == 401
    instant = time.time()
    code = code_totp_courant(conf["totp_secret"], instant)
    assert connecter(client, conf, code=code).status_code == 302
    client.post("/logout", data={"csrf": jeton(client, "/")})
    assert connecter(client, conf, code=code).status_code == 401


def test_liste_blanche_ip(conf):
    conf["allowed_ips"] = ["192.0.2.0/24"]
    app = creer_app(conf)
    assert app.test_client().get("/login").status_code == 403


def test_entetes_securite(client):
    rep = client.get("/login")
    assert rep.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in rep.headers["Content-Security-Policy"]


def test_config_refuse_droits_trop_ouverts(tmp_path, conf):
    chemin = tmp_path / "config.json"
    chemin.write_text(json.dumps(conf))
    chemin.chmod(0o644)
    with pytest.raises(config_mod.ErreurConfiguration):
        config_mod.charger(chemin)
    chemin.chmod(0o600)
    assert config_mod.charger(chemin)["username"] == "admin"
