Dossier destiné à recevoir les différents types de pages organisés par types et par langues

Au premier niveau, nous aurons une organisation par type désigné par QID

Au deuxième niveau, nous aurons le classement par langue donné par son code de langue: fr, en...

 Lorsqu'un QID a pour propriété P31 (instance of) 'être humain' (Q5), on cherche son occupation et on génère des pages en fonction de l'occupation; par exemple, on aura un emplate pour peintre, un pour sculpteur...

 Pour les depicts (dépeint), les valeurs n'ont pas de P31 homogène. Nous allons donc procéder par une liste de valeurs de la propriété depicts (P180). Nous classerons donc ces pages par la propriété qui les désignent.
 
Il est surement judicieux d'utiliser le modèle de méthode factory pour ajouter facilement de nouvelles catégories: nouvelles occupations, nouveau genre...
voir https://medium.com/@jdgb.projects/factory-method-pattern-in-python-94965735f497
