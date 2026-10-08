# testControleMinimal — test rapide, SANS contrôle d'accès, avec diagnostics

Sert uniquement à vérifier que `cloudlinux-selector` permet d'arrêter, démarrer
et redémarrer une autre application Python sur o2switch. **À supprimer après le test.**

## Installation

1. Copier ce dossier dans `~/testControleMinimal`.
2. cPanel › Setup Python App › Create application : *Application root* `testControleMinimal`,
   une URL peu devinable, *startup file* `passenger_wsgi.py`, *entry point* `application`.
3. Variable d'environnement `CIBLE_APP_ROOT` = dossier de l'application à piloter
   (exactement la valeur *Application root* de Setup Python App, ex. `scrutart`),
   puis `pip install -r requirements.txt` dans le virtualenv et **Restart**
   (une variable ajoutée n'est prise en compte qu'après le redémarrage).

   Setup Python App écrit les variables dans le `.htaccess` (`SetEnv`) ; selon la configuration,
   elles arrivent dans `os.environ` ou seulement dans chaque requête (`request.environ`).
   L'application cherche aux deux endroits. **Secours** : créer un fichier `cible.txt` dans
   `~/testControleMinimal` contenant juste le nom du dossier cible (ex. `scrutart`).

## Ce que montre la page

1. **Environnement** : utilisateur, HOME, valeur exacte de `CIBLE_APP_ROOT` et d'où elle vient
   (os.environ, request.environ ou cible.txt), existence du dossier cible, présence et droits
   de `cloudlinux-selector`.
   **1 bis** : les `.htaccess` du compte qui mentionnent `CIBLE_APP_ROOT` et leur bloc de
   configuration Passenger / variables (valeurs des autres variables masquées).
2. **Applications vues par le sélecteur** : tableau de toutes les applications Python du compte
   (app_root, statut, URL…), la cible surlignée, avec des boutons start / stop / restart
   pour chacune. Avertissement si `CIBLE_APP_ROOT` ne correspond à aucune.
3. **Processus** de la cible (`ps`).
4. **Sortie brute** de `cloudlinux-selector get` (valeurs des variables d'environnement masquées).
5. Même commande **sans nettoyer l'environnement** : si §4 et §5 diffèrent, c'est le virtualenv
   de cette application qui perturbe le sélecteur.

Après une action : statut / processus / réponse HTTP de la cible **avant et après**, commande exacte,
code retour, stdout, stderr. Tout est aussi ajouté à `diagnostic.log` (lien « journal »).

## Fin du test

Supprimer l'application dans Setup Python App et le dossier `~/testControleMinimal`.
