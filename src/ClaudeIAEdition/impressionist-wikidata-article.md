# Les Impressionnistes dans Wikidata : Cartographie Complète d'un Mouvement

*Note: Les chiffres présentés dans cet article correspondent à la situation au 22 août 2025*

L'impressionnisme reste l'un des mouvements artistiques les plus populaires au monde, mais comment se reflète cette popularité dans les bases de données culturelles ? Je vais analyser dans cet article la présence des quatre maîtres fondateurs de l'impressionnisme dans Wikidata : Claude Monet, Pierre-Auguste Renoir, Edgar Degas et Camille Pissarro.

Cette analyse s'appuie sur des requêtes SPARQL permettant d'interroger les données de Wikidata. Un lien est fourni pour exécuter chaque requête dans WDQS, l'outil d'interrogation SPARQL de Wikidata.

## Vue d'ensemble : Un patrimoine numérique colossal

### Claude Monet (Q296) : Le maître incontesté

Il y a **1190 œuvres** de [Claude Monet](http://www.wikidata.org/entity/Q296) référencées dans Wikidata.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%28COUNT%28%3Fs%29%20AS%20%3Fc%29%20WHERE%20%7B%20%3Fs%20wdt%3AP170%20wd%3AQ296%20%7D))*

Pour une galerie d'images représentative, consultez la [Galerie Claude Monet](https://galeries.grains-de-culture.fr/index.php?/category/309).

Un article spécifique est dédié à la création de Monet [Où trouver Claude Monet dans Wikidata, suivez le guide](https://scrutart.grains-de-culture.fr/ou-trouver-claude-monet-dans-wikidata-suivez-le-guide/)

### Pierre-Auguste Renoir (Q39931) : L'humaniste prolifique

**1359 œuvres** de [Pierre-Auguste Renoir](http://www.wikidata.org/entity/Q39931) sont présentes dans Wikidata.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%28COUNT%28%3Fs%29%20AS%20%3Fc%29%20WHERE%20%7B%20%3Fs%20wdt%3AP170%20wd%3AQ39931%20%7D))*

Pour une galerie d'images représentative, consultez la [Galerie Auguste Renoir](https://galeries.grains-de-culture.fr/index.php?/category/329).

### Edgar Degas (Q46373) : Le perfectionniste du mouvement

Les œuvres d'[Edgar Degas](http://www.wikidata.org/entity/Q46373) comptent **745 entrées** dans Wikidata.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%28COUNT%28%3Fs%29%20AS%20%3Fc%29%20WHERE%20%7B%20%3Fs%20wdt%3AP170%20wd%3AQ46373%20%7D))*

Pour une galerie d'images représentative, consultez la [Galerie Edgar Degas](https://galeries.grains-de-culture.fr/index.php?/category/41).

Un article spécifique est dédié à la création de Degas [Où trouver Edgar Degas dans Wikidata, suivez le guide](https://scrutart.grains-de-culture.fr/ou-trouver-edgar-degas-dans-wikidata-suivez-le-guide/)

### Camille Pissarro (Q134741) : Le mentor discret

**853 œuvres** de [Camille Pissarro](http://www.wikidata.org/entity/Q134741) sont documentées dans Wikidata.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%28COUNT%28%3Fs%29%20AS%20%3Fc%29%20WHERE%20%7B%20%3Fs%20wdt%3AP170%20wd%3AQ134741%20%7D))*

Pour une galerie d'images représentative, consultez la [Galerie Camille Pissarro](https://galeries.grains-de-culture.fr/index.php?/category/40).

Un article spécifique est dédié à la création de Pissarro [Où trouver Camille Pissarro dans Wikidata, suivez le guide](https://scrutart.grains-de-culture.fr/ou-trouver-camille-pissarro-dans-wikidata-suivez-le-guide/)

## Analyse comparative : Répartition par types d'œuvres

La diversité créative de chaque artiste se reflète notamment dans la répartition par types d'œuvres :

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%3Fartist%20%3FartistLabel%20%3Ftype%20%3FtypeLabel%20%28COUNT%28%3Fs%29%20AS%20%3Fcount%29%20WHERE%20%7B%0A%20%20VALUES%20%3Fartist%20%7B%20wd%3AQ296%20wd%3AQ39931%20wd%3AQ46373%20wd%3AQ134741%20%7D%0A%20%20%3Fs%20wdt%3AP170%20%3Fartist%20%3B%0A%20%20%20%20%20wdt%3AP31%20%3Ftype%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22fr%2Cen%22%20%7D%0A%7D%0AGROUP%20BY%20%3Fartist%20%3FartistLabel%20%3Ftype%20%3FtypeLabel%0AORDER%20BY%20%3Fartist%20DESC%28%3Fcount%29))*

**Monet** :  essentiellement présent grâce à 1182 peintures ou séries de peintures.

**Renoir** : Champion incontesté avec 1251 peintures, 33 sculptures, 26 estampes, 19 dessins, 11 pastels et quelques autre types d'œuvres;  témoignent de sa production intensive et variée.

**Degas** : Équilibre remarquable avec 401 peintures, 116 dessins, 84 pastels, 82 sculptures, 47 estampes et d'autres types d'œuvres, reflétants sa diversité technique.

**Pissarro** : 764 peintures, 38 estampes et 35 dessins, et quelques autres types d'œuvres.

## Richesse descriptive : Analyse des propriétés

### Propriétés les plus utilisées

Pour l'ensemble des quatre artistes, **504 propriétés différentes** sont utilisées pour décrire leurs œuvres.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%28COUNT%28DISTINCT%20%3Fp%29%20AS%20%3Fc%29%20WHERE%20%7B%0A%20%20VALUES%20%3Fartist%20%7B%20wd%3AQ296%20wd%3AQ39931%20wd%3AQ46373%20wd%3AQ134741%20%7D%0A%20%20%3Fs%20wdt%3AP170%20%3Fartist%20%3B%0A%20%20%20%20%20%3Fp%20%5B%5D%20.%0A%7D))*

### Propriétés les plus présentes

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%3Fprop%20%3FpropLabel%20%28COUNT%28distinct%20%3Fs%29%20AS%20%3Fcount%29%20WHERE%20%7B%0A%20%20VALUES%20%3Fartist%20%7B%20wd%3AQ296%20wd%3AQ39931%20wd%3AQ46373%20wd%3AQ134741%20%7D%0A%20%20%23VALUES%20%3Fp%20%7B%20wdt%3AP1071%20wdt%3AP921%20wdt%3AP135%20wdt%3AQ134741%20%7D%0A%20%20%3Fs%20wdt%3AP170%20%3Fartist%20%3B%0A%20%20%20%20%20%3Fp%20%5B%5D%20.%0A%20%20%3Fprop%20wikibase%3AdirectClaim%20%3Fp%20.%0A%20%20FILTER%28%21CONTAINS%28STR%28%3Fp%29%2C%20%22schema%3A%22%29%29%0A%20%20FILTER%28%21CONTAINS%28STR%28%3Fp%29%2C%20%22wikiba.se%3A%22%29%29%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22fr%2Cen%22%20%7D%0A%7D%0AGROUP%20BY%20%3Fprop%20%3FpropLabel%0AORDER%20BY%20DESC%28%3Fcount%29%0ALIMIT%2050)*

| Propriété                 | Usage | Description                                     |
|---------------------------|-------|-------------------------------------------------|
| créateur (P170)           | 4147  | Relation artiste-œuvre (propriété fondamentale) |
| nature de l'élément (P31) | 4146  | Type d'œuvre (peinture, dessin, sculpture...)   |
| image (P18)               | 3757  | Reproduction visuelle disponible                |
| collection (P195)         | 3947  | Institution de conservation                     |
| matériau (P186)           | 3598  | Support et techniques utilisées                 |
| lieu (P276)               | 3537  | Lieu où se trouve l'œuvre                       |
| hauteur (P2048)           | 3514  | Mesures physiques de l'œuvre                    |
| largeur (P2049)           | 3486  | Mesures physiques de l'œuvre                    |
| date de création (P571)   | 3849  | Chronologie précise                             |
| genre (P136)              | 1578  | Classification stylistique                      |
| dépeint (P180)            | 1551  | Elément visuel présent dans l'image             |
| inventaire (P217)         | 3276  | Numéro d'inventaire institutionnel              |
| titre (P1476)             | 1952  | Dénomination officielle                         |
| propriétaire (P127)       | 752   | Détenteur légal                                 |

L'usage est le nombre d'œuvres qui utilisent la propriété; celle-ci peut être utilisée plusieurs fois sur une même oeuvre)

Quelques autres propriétés doivent être aussi observées:

| Propriété                   | Usage | Description |
|-----------------------------|-------|-------------|
| lieu de création (P1071)    | 151   | Géolocalisation de la création |
| sujet principal (P921)      | 275   | Thème représenté |
| mouvement artistique (P135) | 200   | ici, impressionnisme                            |
| exposition (P608)           | 356   | Historique d'expositions                        |

On voit sur ces quatre propriétés que des éléments importants de description ne sont présents que sur moins de 10% des oeuvres observées.
Il y a clairement là des voies de progression.

On notera que seulement 200 œuvres sur plus de 4000 sont explicitement associées à un mouvement artistique.
Avec des variantes de la requête précédente -que je vous laisserais trouver ou que vous pouvez me demander- on peut voir 
que seulement 195 oeuvres sont associées à l'impressionisme; 16 sont associées à d'autres mouvements, dont certaines à plusieurs mouvements.

## Analyse chronologique : L'évolution du mouvement

Une visualisation temporelle révèle les périodes de création les plus intenses :

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/#%23title%3A%20%C5%92uvres%20cr%C3%A9%C3%A9es%20par%20ann%C3%A9e%20%281850%E2%80%931930%29%20%E2%80%94%20Monet%2C%20Renoir%2C%20Degas%2C%20Pissarro%0A%23defaultView%3ABarChart%0Aselect%20%3Fyearstr%20%3Fcount%20%3FartistLabel%20where%20%7B%0A%20%20%7B%0ASELECT%20%3Fyearstr%20%3FartistLabel%20%28COUNT%28DISTINCT%20%3Fs%29%20AS%20%3Fcount%29%20%0A%20%20%20%20%20%20%20%20%20%20%20%20%20WHERE%20%7B%0A%20%20VALUES%20%3Fartist%20%7B%20wd%3AQ296%20wd%3AQ39931%20wd%3AQ46373%20wd%3AQ134741%20%7D%20%20%23%20Monet%2C%20Renoir%2C%20Degas%2C%20Pissarro%0A%0A%20%20%3Fs%20wdt%3AP170%20%3Fartist%20%3B%0A%20%20%20%20%20wdt%3AP571%20%3Fdate%20.%0A%0A%20%20BIND%28YEAR%28%3Fdate%29%20AS%20%3Fyear%29%0A%20%20FILTER%28%3Fyear%20%3E%3D%201850%20%26%26%20%3Fyear%20%3C%3D%201930%29%0A%20%20bind%28str%28%3Fyear%29%20as%20%3Fyearstr%29%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22fr%2Cen%22.%20%7D%0A%7D%0AGROUP%20BY%20%3Fyearstr%20%3FartistLabel%0A%7D%0A%20%20%7D)*

On peut modifier la requête en ne laissant qu'un artiste à la fois. Cela permet quelques observations.

**Observations clés :**
- **Années 1871-1891** : années de création plus intense pour Monet
- **Années 1874-1919** : Renoir crée généralement plus de 20 oeuvres par an, jusqu'à 57 en 1890
- **Années 1870-1903** : Pissarro crée plus de 17 oeuvres par an, jusqu'à 43, avec un creu de 1886 à 1891 semble-t-il due à une transition stylistique 
- **Années 1855-1900** : Degas a créé de 10 à 15 oeuvres par an, avec quelques années moins productives et une période un peu plus intense vers 1880

## Présence dans Wikimedia Commons

### Disponibilité des reproductions

**3761 images** haute qualité sont disponibles dans Wikimedia Commons pour l'ensemble des quatre artistes.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%3Fartist%20%3FartistLabel%20%28COUNT%28distinct%20%3Fs%29%20AS%20%3Fimages%29%20WHERE%20%7B%0A%20%20VALUES%20%3Fartist%20%7B%20wd%3AQ296%20wd%3AQ39931%20wd%3AQ46373%20wd%3AQ134741%20%7D%0A%20%20%3Fs%20wdt%3AP170%20%3Fartist%20%3B%0A%20%20%20%20%20%28wdt%3AP18%7Cwdt%3AP7420%29%20%3Fimage%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22fr%2Cen%22%20%7D%0A%7D%0AGROUP%20BY%20%3Fartist%20%3FartistLabel%0AORDER%20BY%20DESC%28%3Fimages%29)*

**Taux de couverture visuelle :**
- **Monet** : 96,89% (1153/1190 œuvres)
- **Renoir** : 86,46% (1175/1359 œuvres) 
- **Degas** : 84,02% (626/745 œuvres)
- **Pissarro** : 94,6% (807/853 œuvres)

On constate une bonne disponibilité des images des oeuvres pour ces artistes.

## Présence dans les Wikipedia

### Articles dédiés aux œuvres

**2401 articles Wikipedia** (toutes langues confondues) sont consacrés à des œuvres spécifiques de ces quatre maîtres.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%3Fartist%20%3FartistLabel%20%28COUNT%28DISTINCT%20%3Fwiki%29%20AS%20%3Farticles%29%20WHERE%20%7B%0A%20%20VALUES%20%3Fartist%20%7B%20wd%3AQ296%20wd%3AQ39931%20wd%3AQ46373%20wd%3AQ134741%20%7D%0A%20%20%3Fs%20wdt%3AP170%20%3Fartist%20.%0A%20%20%3Fwiki%20schema%3Aabout%20%3Fs%20.%0A%20%20FILTER%28CONTAINS%28STR%28%3Fwiki%29%2C%20%22wikipedia.org%22%29%29%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22fr%2Cen%22%20%7D%0A%7D%0AGROUP%20BY%20%3Fartist%20%3FartistLabel%0AORDER%20BY%20DESC%28%3Farticles%29))*

**Répartition :**
- **Monet** : 925 articles (Les Nymphéas, La Cathédrale de Rouen...)
- **Renoir** : 773 articles (Le Déjeuner des canotiers, La Loge...)
- **Degas** : 373 articles (L'Absinthe, La Classe de danse...)
- **Pissarro** : 330 articles (Boulevard Montmartre, Les Toits rouges...)

Dans toutes ces pages, on a surement des informations complémentaires pour enrichir les données de
Wikidata et des liens vers des sources qui peuvent être exploitées.

## Institutions détentrices : Cartographie mondiale

### Top 10 des collections

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%3Fcollection%20%3FcollectionLabel%20%28COUNT%28%3Fs%29%20AS%20%3Fcount%29%20WHERE%20%7B%0A%20%20VALUES%20%3Fartist%20%7B%20wd%3AQ296%20wd%3AQ39931%20wd%3AQ46373%20wd%3AQ134741%20%7D%0A%20%20%3Fs%20wdt%3AP170%20%3Fartist%20%3B%0A%20%20%20%20%20wdt%3AP195%20%3Fcollection%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22fr%2Cen%22%20%7D%0A%7D%0AGROUP%20BY%20%3Fcollection%20%3FcollectionLabel%0AORDER%20BY%20DESC%28%3Fcount%29%0ALIMIT%2020))*

1. **Musée d'Orsay** (Paris) : 300 œuvres
2. **Metropolitan Museum of Art** (New York) : 189 œuvres  
3. **National Gallery** (Londres) : 639 œuvres
4. **Art Institute of Chicago** : 70 œuvres
5. **Musée Marmottan Monet** (Paris) : 104 œuvres
6. **Philadelphia Museum of Art** : 57 œuvres
7. **Boston Museum of Fine Arts** : 71 œuvres
8. **Fondation Barnes** : 106 œuvres
9. **Collection Rosenwald** : 70 œuvres
10. **Clark Art Institute** : 56 œuvres


## Lacunes identifiées et opportunités d'enrichissement

### Œuvres sous-documentées

Une analyse reste à faire sur la présence des propriétés les plus pertinentes sur les œuvres.
Une partie des oeuvres ne disposent que des propriétés minimales (créateur, type, titre)
et de quelques propriétés 'techniques' comme des liens vers d'autres bases de données.
Il serait surement intéressant de renseigner, chaque fois que c'est pertinent, la propriété 'sujet principal'.

### Priorités d'enrichissement

1. **Images manquantes** : 314 œuvres sans reproduction (moins de 10%)

## Comparaison avec d'autres sources : Joconde et collections nationales

La base Joconde est une base de données officielles qui recense une large part des collections nationales françaises; elle décrit environ 600000 créations. Dans Wikidata, **26131 œuvres** présentent un identifiant Joconde.
Seulement 314 sont associées à un des artistes qui nous concernent ici.
Il y a probablement là une importante source d'enrichissement de Wikidata à partir de données de référence, même si une sélection est à envisager parmi les 600000 créations: certaines sont peu documentées, certaines sont peut-être mineures, ...

## Conclusion : Un patrimoine numérique impressionnant mais perfectible

Cette analyse révèle la richesse exceptionnelle de la documentation Wikidata sur l'impressionnisme : **3,158 œuvres** de quatre maîtres, décrites avec **187 propriétés différentes**, illustrées par **1,823 images** haute qualité.

**Points forts identifiés :**
- Forte présence dans Wikipedia (plus de 2000 articles)
- Bonne couverture iconographique de l'impressionisme

**Axes d'amélioration prioritaires :**
- Couverture de Monet: les catalogues actuels indiquent de 2000 à 3000 créations;  œuvres sont référencées dans Wikidata
- Combler les 10% d'œuvres sans image
- Enrichir la documentation des œuvres 
- Intégrer de nouvelles œuvres des collections nationales manquantes

L'impressionnisme dans Wikidata constitue un cas d'école pour la valorisation numérique du patrimoine artistique, démontrant à la fois les possibilités immenses des bases de données ouvertes et les défis persistants de l'exhaustivité documentaire.

---

*Pour aller plus loin, consultez notre série "Culture Picturale & Données" : le prochain article explorera les "Musées Français vs Wikidata : L'Art Sous-Représenté".*

**Toutes les requêtes SPARQL de cet article sont exécutables directement** via les liens WDQS fournis. N'hésitez pas à les adapter pour vos propres recherches !

---

*Cet article fait partie de la série "Vulgarisation Culture Picturale" de [Scrutart - Grains de Culture](https://scrutart.grains-de-culture.fr). Données analysées le 22 août 2025.*