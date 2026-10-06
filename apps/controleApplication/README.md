# controleApplication — arrêter / démarrer / redémarrer une application Python sur o2switch

Petite application Flask d'administration qui pilote **une autre application Python**
hébergée sur le même compte o2switch, avec un contrôle d'accès renforcé.

## Sécurité mise en place

| Mesure | Détail |
|---|---|
| Double facteur obligatoire | identifiant + mot de passe (haché, scrypt) + code TOTP (Aegis, FreeOTP, Google Authenticator…) |
| Anti-rejeu TOTP | un code déjà utilisé est refusé (état partagé en SQLite entre les processus Passenger) |
| Anti-force brute | 5 échecs / 15 min par IP, 20 échecs / 15 min au total → blocage ; délai d'1 s par échec |
| Liste blanche IP (option) | `allowed_ips` : `["203.0.113.4", "198.51.100.0/24"]` |
| Session courte | expiration après 10 min d'inactivité et 60 min au maximum ; cookie `__Host-`, `Secure`, `HttpOnly`, `SameSite=Strict` |
| CSRF | jeton sur tous les formulaires ; les actions ne passent que par POST |
| Confirmation | arrêter / redémarrer demande de retaper le nom de l'application |
| En-têtes | CSP stricte (aucun script), `X-Frame-Options: DENY`, HSTS, `Cache-Control: no-store`, `noindex` |
| Pas d'injection | les commandes viennent uniquement du fichier de configuration, sans shell |
| Secrets hors web | configuration dans `~/.config/controle_app/config.json`, refusée si elle n'est pas en `chmod 600` |
| Audit | toutes les connexions (réussies ou non) et actions dans `~/.config/controle_app/audit.log` |

## Modes de pilotage (« backends »)

| backend | pour quoi | actions |
|---|---|---|
| `cloudlinux` | application déclarée dans cPanel › **Setup Python App** (cas standard o2switch) ; utilise `cloudlinux-selector start/stop/restart` | démarrer, arrêter, redémarrer |
| `passenger` | redémarrage simple par `touch <app_root>/tmp/restart.txt` | redémarrer |
| `process` | script lancé en arrière-plan (robot, worker…), suivi par fichier PID | démarrer, arrêter, redémarrer |

## Installation sur o2switch

1. **Sous-domaine dédié**, par ex. `admin-xyz.mondomaine.fr` (nom peu devinable), avec certificat
   SSL actif (cPanel › *Let's Encrypt / AutoSSL*). L'application doit être servie **à la racine**
   du sous-domaine (le cookie `__Host-` l'exige) et **uniquement en HTTPS**.

2. **Copier le dossier** `controleApplication/` dans `~/controleApplication` (hors `public_html`).

3. cPanel › **Setup Python App** › *Create application* :
   - Python 3.10 ou plus,
   - *Application root* : `controleApplication`,
   - *Application URL* : le sous-domaine,
   - *Application startup file* : `passenger_wsgi.py`, *entry point* : `application`.

   Puis, en SSH, activer l'environnement (commande affichée en haut de la page de l'application)
   et installer les dépendances :
   ```bash
   source ~/virtualenv/controleApplication/3.11/bin/activate
   cd ~/controleApplication
   pip install -r requirements.txt
   ```

4. **Initialiser la configuration** (toujours en SSH) :
   ```bash
   python gestion.py init
   ```
   Choisir un identifiant et un mot de passe long (≥ 14 caractères), puis ajouter le secret TOTP
   affiché dans l'application d'authentification du téléphone.

5. **Décrire l'application à piloter** dans `~/.config/controle_app/config.json` :
   ```json
   "targets": {
     "scrutart": {
       "label": "Application Scrutart",
       "backend": "cloudlinux",
       "app_root": "scrutart",
       "health_url": "https://scrutart.mondomaine.fr/"
     }
   }
   ```
   `app_root` est le chemin de l'application **relatif au dossier personnel**, tel qu'il apparaît
   dans *Setup Python App*. Exemple pour un robot lancé en tâche de fond :
   ```json
   "robot": {
     "backend": "process",
     "command": ["/home/USER/virtualenv/robot/3.11/bin/python", "/home/USER/robot/main.py"],
     "cwd": "/home/USER/robot",
     "pid_file": "/home/USER/robot/robot.pid",
     "log_file": "/home/USER/robot/robot.log"
   }
   ```
   Plusieurs cibles peuvent être déclarées.

6. **Vérifier** :
   ```bash
   python gestion.py verifier
   ```
   Cette commande appelle réellement `cloudlinux-selector` et doit afficher le statut de la cible.
   Tester aussi à la main une fois : `cloudlinux-selector restart --json --interpreter python --app-root scrutart`.

7. **Redémarrer** l'application de contrôle (bouton *Restart* de Setup Python App) et se connecter.

### Durcissement complémentaire recommandé

- **Liste blanche IP** (`allowed_ips`) si votre adresse est fixe. o2switch propose aussi un
  filtrage par IP dans cPanel (*Outil de sécurité* / *IP Blocker*).
- **Seconde barrière HTTP** : cPanel › *Confidentialité des répertoires* (authentification
  Basic sur le dossier du sous-domaine), avec un autre mot de passe.
- Si l'adresse vue par l'application est toujours celle d'un proxy (toutes les entrées de
  `audit.log` avec la même IP), mettre `"trust_proxy": true` ; sinon laisser `false`
  (sinon un attaquant pourrait falsifier son IP via `X-Forwarded-For`).
- Changer le mot de passe : `python gestion.py mot-de-passe` ; perte du téléphone :
  `python gestion.py totp`. Les deux commandes invalident les sessions ouvertes.
  Redémarrer ensuite l'application de contrôle.

## Paramètres de `config.json`

| clé | défaut | rôle |
|---|---|---|
| `allowed_ips` | `[]` (aucun filtrage) | adresses / réseaux autorisés |
| `trust_proxy` | `false` | lire l'IP cliente dans `X-Forwarded-For` |
| `session_idle_minutes` | `10` | expiration après inactivité |
| `session_max_minutes` | `60` | durée maximale d'une session |
| `max_echecs_ip` / `max_echecs_global` | `5` / `20` | seuils de blocage |
| `fenetre_echecs_minutes` | `15` | fenêtre de comptage des échecs |
| `data_dir` | dossier de la configuration | base SQLite de sécurité et `audit.log` |

## Tests

```bash
pip install pytest
python -m pytest tests
```
