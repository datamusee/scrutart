"""
voir code WPProcessSteps.py
voir dossier D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\ClaudeIAEdition\artistPublisher
voir dossier D:\wamp64\www\givingsense.eu\datamusee\scrutart\src\orchestrateurPrefect

but: tache de fond qui automatise des constrauctions et mises à jour de pages
lire un fichier de config de generation dans le dossier d'étape à générer
pour la page principale de l'étape,
pour chaque langue,
regarder si la page existe
si elle existe, sauver son contenu (git?)
si la page n'existe pas, la créer vide
charger le fichier de template
charger les données de la source considérée (désignée par un QID? autres façon de désigner?)
appliquer les données au template
pour la génération de liens vers une autre page de scrutart, tester si la page existe en publish ou draft
si c'est le cas, récupérer l'url, si ce n'est pas le cas la créer 'vide' et récupérer l'url à injecter dans le template
- penser à faire les logs de tout ça
- ce sera accessible via une interface web, mais l'essentiel un script lancé par un cron
- l'interface web peut permettre de voir une partie des logs (par date?) et surtout d'ajouter des éléments dans la liste
des fichiers de config de génération
- cela va donc être un service web (flask? django?) dont un script est appelé par un cron
- voir comment utiliser git pour la sauvegarde des versions des pages
"""