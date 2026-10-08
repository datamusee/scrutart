# testControleMinimal — test rapide, SANS contrôle d'accès

Sert uniquement à vérifier que `cloudlinux-selector` permet d'arrêter, démarrer
et redémarrer une autre application Python sur o2switch. **À supprimer après le test.**

1. Copier ce dossier dans `~/testControleMinimal`.
2. cPanel › Setup Python App › Create application : *Application root* `testControleMinimal`,
   un sous-domaine ou une URL peu devinable, *startup file* `passenger_wsgi.py`,
   *entry point* `application`.
3. Ajouter la variable d'environnement `CIBLE_APP_ROOT` = dossier de l'application à piloter
   (tel qu'affiché dans Setup Python App, ex. `scrutart`), puis `pip install -r requirements.txt`
   dans le virtualenv et *Restart*.
4. Ouvrir l'URL : la page affiche la sortie brute de `cloudlinux-selector get` (statut de toutes
   les applications) ; les boutons `start`, `stop`, `restart` affichent la commande, le code retour
   et la sortie.
5. **Supprimer l'application** dans Setup Python App une fois le test fini.
