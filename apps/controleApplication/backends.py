"""Moyens de piloter l'application cible.

- cloudlinux : application déclarée dans « Setup Python App » de cPanel
  (cas standard chez o2switch), pilotée avec `cloudlinux-selector`.
- passenger  : redémarrage seul, par `touch <app_root>/tmp/restart.txt`.
- process    : script Python lancé en arrière-plan (worker, robot...),
  suivi par un fichier PID.

Aucune donnée venant de la requête HTTP n'est transmise aux commandes :
tout provient du fichier de configuration, et subprocess est appelé sans shell.
"""
import json
import os
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

DELAI_COMMANDE = 120


class ErreurBackend(Exception):
    pass


def _executer(args):
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=DELAI_COMMANDE)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ErreurBackend(f"Échec de {args[0]} : {e}") from e
    sortie = (res.stdout + res.stderr).strip()
    if res.returncode != 0:
        raise ErreurBackend(f"Code retour {res.returncode} : {sortie[-2000:]}")
    return sortie


def sante_http(url, delai=10):
    """Interroge l'URL de santé de la cible ; renvoie un texte court."""
    try:
        with urllib.request.urlopen(url, timeout=delai) as rep:
            return f"HTTP {rep.status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except Exception as e:  # réseau, DNS, délai...
        return f"injoignable ({type(e).__name__})"


class BackendCloudLinux:
    actions = ("start", "stop", "restart")

    def __init__(self, cible):
        self.app_root = cible["app_root"]
        self.binaire = (cible.get("selector")
                        or shutil.which("cloudlinux-selector")
                        or "/usr/sbin/cloudlinux-selector")

    def _cmd(self, action):
        return [self.binaire, action, "--json", "--interpreter", "python",
                "--app-root", self.app_root]

    def executer(self, action):
        return _executer(self._cmd(action))

    def statut(self):
        sortie = _executer([self.binaire, "get", "--json", "--interpreter", "python"])
        try:
            donnees = json.loads(sortie)
        except ValueError:
            return "inconnu"
        trouve = _chercher_statut(donnees, self.app_root.strip("/"))
        return trouve or "inconnu"


def _chercher_statut(noeud, app_root):
    """Parcourt la sortie JSON de `cloudlinux-selector get` à la recherche de l'application."""
    if isinstance(noeud, dict):
        for cle, val in noeud.items():
            if isinstance(val, dict) and (
                    cle.strip("/") == app_root or str(val.get("app_root", "")).strip("/") == app_root):
                statut = val.get("app_status") or val.get("status")
                if statut:
                    return statut
            res = _chercher_statut(val, app_root)
            if res:
                return res
    elif isinstance(noeud, list):
        for val in noeud:
            res = _chercher_statut(val, app_root)
            if res:
                return res
    return None


class BackendPassenger:
    actions = ("restart",)

    def __init__(self, cible):
        self.app_root = Path(cible["app_root"]).expanduser()

    def executer(self, action):
        if action != "restart":
            raise ErreurBackend("Ce backend ne sait que redémarrer")
        tmp = self.app_root / "tmp"
        tmp.mkdir(exist_ok=True)
        (tmp / "restart.txt").touch()
        return "Redémarrage demandé à Passenger (au prochain appel HTTP)"

    def statut(self):
        return "géré par Passenger"


class BackendProcessus:
    actions = ("start", "stop", "restart")

    def __init__(self, cible):
        self.commande = cible["command"]
        self.cwd = cible.get("cwd")
        self.pid_file = Path(cible["pid_file"]).expanduser()
        self.log_file = Path(cible.get("log_file") or self.pid_file.with_suffix(".log")).expanduser()
        self.env = {**os.environ, **cible.get("env", {})}

    def _pid(self):
        try:
            pid = int(self.pid_file.read_text().strip())
            os.kill(pid, 0)
            return pid
        except (OSError, ValueError):
            return None

    def statut(self):
        pid = self._pid()
        return f"started (PID {pid})" if pid else "stopped"

    def _demarrer(self):
        if self._pid():
            return "Déjà démarré"
        with open(self.log_file, "ab") as log:
            proc = subprocess.Popen(self.commande, cwd=self.cwd, env=self.env,
                                    stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                    start_new_session=True)
        self.pid_file.write_text(str(proc.pid))
        return f"Démarré (PID {proc.pid})"

    def _arreter(self):
        pid = self._pid()
        if not pid:
            return "Déjà arrêté"
        os.killpg(pid, signal.SIGTERM)
        for _ in range(100):
            if not self._pid():
                break
            time.sleep(0.1)
        else:
            os.killpg(pid, signal.SIGKILL)
        self.pid_file.unlink(missing_ok=True)
        return f"Arrêté (PID {pid})"

    def executer(self, action):
        if action == "start":
            return self._demarrer()
        if action == "stop":
            return self._arreter()
        if action == "restart":
            return f"{self._arreter()} ; {self._demarrer()}"
        raise ErreurBackend(f"Action inconnue : {action}")


def creer_backend(cible):
    return {
        "cloudlinux": BackendCloudLinux,
        "passenger": BackendPassenger,
        "process": BackendProcessus,
    }[cible["backend"]](cible)
