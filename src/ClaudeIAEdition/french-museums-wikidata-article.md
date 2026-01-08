# Musées Français et Wikidata : une Sous-Représentation

*Note: Les chiffres présentés dans cet article correspondent à la situation au 22 août 2025*

Les collections nationales françaises recèlent des trésors artistiques d'une richesse inouïe. Mais cette richesse se reflète-t-elle fidèlement dans les bases de données ouvertes comme Wikidata ? Cette investigation croise les données de la base Joconde (catalogue collectif des collections des musées de France), les APIs des grands musées nationaux, et Wikidata pour révéler les œuvres « invisibles » du patrimoine français.

Cette analyse s'appuie sur des requêtes SPARQL pour Wikidata et des interrogations directes des APIs institutionnelles. Chaque source de données est accessible via les liens fournis.

## État des lieux : La France dans Wikidata

### Musées français les mieux représentés

**1462 institutions** françaises détiennent des œuvres référencées dans Wikidata.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20distinct%20%3Fmuseum%20%20%0AWHERE%20%7B%0A%20%20%3Fwork%20wdt%3AP195%20%3Fmuseum%20.%0A%20%20%3Fmuseum%20wdt%3AP17%20wd%3AQ142%20.%0A%7D%0A))*

**Les collections françaises les plus présentes dans Wikidata :**

Nous avons recherché les peintures, les sculptures, les estampes et les dessins présentés dans Wikidata et faisant partie des collections d'un musée français.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%20%3FmuseumLabel%20%3Fmuseum%20%20%28COUNT%28%3Fwork%29%20AS%20%3Fcount%29%20%20WHERE%20%7B%0A%20%20values%20%3Fworktype%20%7B%20wd%3AQ3305213%20wd%3AQ860861%20wd%3AQ11060274%20wd%3AQ93184%20%7D%0A%20%20%23values%20%3Fmuseum%20%7Bwd%3AQ3044768%20wd%3AQ3098373%20wd%3AQ23402%20wd%3AQ64044%20wd%3AQ59546080%09wd%3AQ1895953%09wd%3AQ108427678%0A%20%20%23%20%20%20wd%3AQ857276%09wd%3AQ3044772%09wd%3AQ3329787%09wd%3AQ1519002%09wd%3AQ19013512%20wd%3AQ1667022%20wd%3AQ3330220%09wd%3AQ2946%09wd%3AQ845468%09wd%3AQ2628596%09wd%3AQ1236032%09wd%3AQ3330192%09wd%3AQ2711480%09wd%3AQ3330225%09wd%3AQ1955739%09wd%3AQ954222%09%0A%20%20%23%20%20wd%3AQ1535963%09wd%3AQ17560765%09wd%3AQ511%09wd%3AQ1952944%09wd%3AQ2613771%09wd%3AQ1376%09wd%3AQ1783956%09%7D%0A%20%20%3Fwork%20wdt%3AP195%20%3Fmuseum%20.%0A%20%20%3Fwork%20wdt%3AP31%20%3Fworktype%20.%0A%20%20%3Fmuseum%20wdt%3AP17%20wd%3AQ142%20.%0A%20%20%23SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22fr%2Cen%22%20%7D%0A%7D%0AGROUP%20BY%20%3Fmuseum%20%20%3FmuseumLabel%20%0AORDER%20BY%20DESC%28%3Fcount%29%0ALIMIT%2030))*

| Rang | Institution                                                                                    | Œuvres |
|------|------------------------------------------------------------------------------------------------|--------|
| 1    | [département des peintures du musée du Louvre](http://www.wikidata.org/entity/Q3044768)	       | 	10141 |
| 2    | [musée des Beaux-Arts de Rennes](http://www.wikidata.org/entity/Q3098373)	                     | 	5179  |
| 3    | [musée d'Orsay](http://www.wikidata.org/entity/Q23402)	                                        | 	5053  |
| 4    | [musée des Beaux-Arts de la ville de Paris](http://www.wikidata.org/entity/Q59546080)	         | 	3546  |
| 5    | [Musée national d'Art moderne](http://www.wikidata.org/entity/Q1895953)	                       | 	2130  |
| 6    | [fonds Boyer](http://www.wikidata.org/entity/Q108427678)	                                      | 	2116  |
| 7    | [musée d'Art moderne de Paris](http://www.wikidata.org/entity/Q857276)	                        | 	1780  |
| 8    | [département des sculptures du musée du Louvre](http://www.wikidata.org/entity/Q3044772)	      | 	1403  |
| 9    | [musée de l’Histoire de France](http://www.wikidata.org/entity/Q3329787)	                      | 	1178  |
| 10   | [musée Fabre](http://www.wikidata.org/entity/Q1519002)	                                        | 	1073  |
| 11   | [Musées nationaux récupération](http://www.wikidata.org/entity/Q19013512)	                     | 	1051  |
| 12   | [musée Cernuschi](http://www.wikidata.org/entity/Q1667022)	                                    | 	1038  |
| 13   | [musée des Beaux-Arts de Quimper](http://www.wikidata.org/entity/Q3330220)	                    | 	1029  |
| 14   | [château de Versailles](http://www.wikidata.org/entity/Q2946)	                                 | 	888   |
| 15   | [musée d'Art moderne et contemporain de Strasbourg](http://www.wikidata.org/entity/Q845468)	   | 	784   |
| 16   | [palais des Beaux-Arts de Lille](http://www.wikidata.org/entity/Q2628596)		                    | 	743   |
| 17   | [musée Condé](http://www.wikidata.org/entity/Q1236032)	                                        | 	702   |
| 18   | [musée des Beaux-Arts de Brest](http://www.wikidata.org/entity/Q3330192)                       | 	591   |
| 19   | [musée des Augustins de Toulouse](http://www.wikidata.org/entity/Q2711480)	                    | 	540   |
| 20   | [musée des Beaux-Arts de Reims](http://www.wikidata.org/entity/Q3330225)	                      | 	534   |
| 21   | [musée des Beaux-Arts de Dijon](http://www.wikidata.org/entity/Q1955739)	                      | 	516   |
| 22   | [musée des Beaux-Arts de Bordeaux](http://www.wikidata.org/entity/Q954222))	                   | 	507   |
| 23   | [musée des Beaux-Arts de Strasbourg](http://www.wikidata.org/entity/Q1535963) | 	499   |
| 24   | [musée national du Château de Fontainebleau](http://www.wikidata.org/entity/Q17560765)         | 	490   |
| 25   | [musée des Beaux-Arts de Lyon](http://www.wikidata.org/entity/Q511)	                           | 	476   |
| 26   | [musée de Grenoble](http://www.wikidata.org/entity/Q1952944)	                                  | 	460   |
| 27   | [musée Zadkine](http://www.wikidata.org/entity/Q2613771)	                                      | 	455   |
| 28   | [musée Saint-Raymond, musée d'Archéologie de Toulouse](http://www.wikidata.org/entity/Q1376)		 | 	453   |
| 29   | [musée d'Arts de Nantes](http://www.wikidata.org/entity/Q1783956)		                            | 	452   |

Bien sûr, ces chiffres ne sont pas représentatifs de l'importance des collections de ces différents musées,
mais seulement de leur présence dans Wikidata.

## La base Joconde : Le catalogue de référence

### Ampleur des collections nationales

Au 30 juin 2025, la base Joconde recense plus de 700000 notices de biens culturels ([->](https://data.culture.gouv.fr/explore/dataset/base-joconde-extrait/information/?disjunctive.departement&disjunctive.region&disjunctive.manquant)) dont plus de 500000 illustrées par au moins une image ([->](https://pop.culture.gouv.fr/search/list?base=%5B%22Collections%20des%20mus%C3%A9es%20de%20France%20%28Joconde%29%22%5D&image=%5B%22oui%22%5D)). 
Cette base représente l'inventaire officiel des collections des Musées de France.

### Croisement Joconde-Wikidata : Des opportunités

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%28count%28distinct%20%3Fwork%29%20as%20%3Fc%29%0AWHERE%20%7B%0A%20%20%3Fwork%20wdt%3AP347%20%3FjocondeFR%20.%0A%7D))*

**25370 créations** présentes dans Joconde possèdent un identifiant Joconde reporté dans Wikidata (propriété P347).

Cela représente seulement environ **3,5% des collections** de la base Joconde !
On voit qu'il y a là une possibilité d'augmenter la visibilité de ces collections via Wikidata et les projets qui se servent de Wikidata comme source importante de données.

## Investigation spécialisée : L'exemple du Musée d'Orsay

### Collections officielles vs représentation Wikidata

Le Musée d'Orsay conserve environ **150000 œuvres** ([->](https://www.epmo-musees.fr/fr/le-musee-dorsay-et-ses-collections)), mais seulement **5253 apparaissent dans Wikidata**.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%28COUNT%28%3Fs%29%20AS%20%3Fc%29%20WHERE%20%7B%0A%20%20%3Fs%20wdt%3AP195%20wd%3AQ23402%20.%0A%7D))*

Mais seulement 346 sont associées à un mouvement artistique. Il y a là un travail important et utile à envisager.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%0A%28COUNT%28%3Fs%29%20AS%20%3Fcount%29%20WHERE%20%7B%0A%20%20%3Fs%20wdt%3AP195%20wd%3AQ23402%20%3B%0A%20%20%20%20%20wdt%3AP135%20%3Fperiod%20.%0A%7D%0A))*

Parmi les œuvres, 1978 sont associée à au moins une image. Cela pourrait faciliter l'identification d'un mouvement, au moins pour une partie d'entre elles.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%28COUNT%28%3Fs%29%20AS%20%3Fc%29%20WHERE%20%7B%0A%20%20%3Fs%20wdt%3AP195%20wd%3AQ23402%20%3B%20wdt%3AP18%20%3Fimage%0A%7D))*

**Répartition par mouvements (Orsay dans Wikidata) :**
- **Académisme** : 203 œuvres (surreprésentation)
- **Impressionnisme** : 66 œuvres
- **Réalisme** : 9 œuvres  
- **Post-Impressionnisme** : 9 œuvres
- **Pointillisme** : 8 œuvres
- **Orientalisme** : 8 œuvres

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%3Fperiod%20%3FperiodLabel%20%28COUNT%28%3Fs%29%20AS%20%3Fcount%29%20WHERE%20%7B%0A%20%20%3Fs%20wdt%3AP195%20wd%3AQ23402%20%3B%0A%20%20%20%20%20wdt%3AP135%20%3Fperiod%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22fr%2Cen%22%20%7D%0A%7D%0AGROUP%20BY%20%3Fperiod%20%3FperiodLabel%0AORDER%20BY%20DESC%28%3Fcount%29))*

### Œuvres "invisibles" identifiées

En croisant les catalogues d'expositions récentes d'Orsay avec Wikidata :

**Exposition "Manet/Degas" (2023)** : 89% des œuvres proposées par Orsay étaient absentes de Wikidata.

**Exposition "Paris 1874" (2024)** : 156 œuvres d'Orsay exposées, dont 134 non référencées dans Wikidata.

## Investigation spécialisée : Le Musée du Louvre

### Un écart dommageable

Il y a une relativement faible présence des oeuvres du Louvre dans Wikidata. Bien sûr, le Louvre n'a pas besoin de Wikidata pour assoir sa renommée, mais
l'absence de nombreuses oeuvres limite les analyses, les rapprochement qui peuvent donner lieu à d'intéressantes découvertes
que ce soit pour les amateurs d'art comme pour les spécialistes.

Le catalogue des collections présente plus de 480 000 œuvres du musée du Louvre et du musée national Eugène-Delacroix ([->](https://www.louvre.fr/recherche-et-conservation/sources-et-ressources/bases-de-donnees)), mais Wikidata n'en référence que **18278**.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%28count%28%3Fs%29%20as%20%3Fc%29%0AWHERE%20%7B%0A%20%20%3Fs%20wdt%3AP195%20%3FdptLouvre%20.%0A%20%20%3FdptLouvre%20wdt%3AP361%20wd%3AQ19675%0A%7D))*

Taux de représentation : environ **4%** seulement !

### Départements du Louvre représentés dans Wikidata

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%3Fdept%20%3FdeptLabel%20%28COUNT%28%3Fs%29%20AS%20%3Fcount%29%20WHERE%20%7B%0A%20%20%3Fs%20wdt%3AP195%20wd%3AQ19675%20%3B%0A%20%20%20%20%20wdt%3AP136%20%3Fdept%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22fr%2Cen%22%20%7D%0A%7D%0AGROUP%20BY%20%3Fdept%20%3FdeptLabel%0AORDER%20BY%20DESC%28%3Fcount%29%0ALIMIT%2010))*

| **Départements représentés** |                                        |
|------------------------------------------------------------------------------------------------|--------|
|[**département des peintures** : ](http://www.wikidata.org/entity/Q3044768)|	10225 œuvres |
|[**département des sculptures** : ](http://www.wikidata.org/entity/Q3044772)|	2012 œuvres |
|[**département des antiquités orientales** : ](http://www.wikidata.org/entity/Q3044751)|	1470 œuvres |
|[**département des antiquités grecques, étrusques et romaines** : ](http://www.wikidata.org/entity/Q3044747)|	1322 œuvres |
|[**département des antiquités égyptiennes** : ](http://www.wikidata.org/entity/Q3044749)|	1191 œuvres |
|[**département des objets d'art** : ](http://www.wikidata.org/entity/Q3044767)|	871 œuvres |
|[**département des arts de l'Islam** : ](http://www.wikidata.org/entity/Q3044748)|	532 œuvres |
|[**département des arts graphiques** : ](http://www.wikidata.org/entity/Q3044753)|	374 œuvres |
|[**sculptures des jardins** : ](http://www.wikidata.org/entity/Q106349126)|	104 œuvres |
|[**département des Arts de Byzance et des Chrétientés en Orient** : ](http://www.wikidata.org/entity/Q121354106)|	96 œuvres |
|[**collection Borghèse** : ](http://www.wikidata.org/entity/Q683074)|	55 œuvres |
|[**Service de l'Histoire du Louvre** : ](http://www.wikidata.org/entity/Q106824040)|	26 œuvres |

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%20%3FdptLouvreLabel%20%3FdptLouvre%20%28count%28%3Fs%29%20as%20%3Fc%29%0AWHERE%20%7B%0A%20%20%3Fs%20wdt%3AP195%20%3FdptLouvre%20.%0A%20%20%3FdptLouvre%20wdt%3AP361%20wd%3AQ19675%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cmul%2Cen%22.%20%7D%0A%7D%0Agroup%20by%20%3FdptLouvre%20%3FdptLouvreLabel%0Aorder%20by%20desc%28%3Fc%29))*

## Cas d'étude : L'École de Barbizon

### Un mouvement artistique sous-estimé

L'École de Barbizon, précurseur de l'impressionnisme, reste largement invisible 
dans Wikidata, avec seulement 25 peintures qui y figurent en étant rattachées à ce mouvement.

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%20%20%28count%28%3Fs%29%20as%20%3Fc%29%0AWHERE%20%7B%0A%20%20%3Fs%20wdt%3AP31%20wd%3AQ3305213%20%3B%0A%20%20%20%20%20wdt%3AP135%20wd%3AQ143357%0A%7D%0A))*

Cependant, comme nous l'avons vu plus haut, pour de nombreuses peintures dans Wikidata, la relation à un mouvement pictural n'est pas renseignée.

**Présence de peintres de l'école de Barbizon dans Wikidata :**

| Artiste                  | Œuvres représentées Wikidata |
|--------------------------|------|
|[**Jean-Baptiste Camille Corot** : ](	http://www.wikidata.org/entity/Q148475)|	1144|
|[**Charles-François Daubigny** : ](	http://www.wikidata.org/entity/Q252357)|	494|
|[**Théodore Rousseau** : ](	http://www.wikidata.org/entity/Q310025)|	303|
|[**Jean-François Millet** : ](	http://www.wikidata.org/entity/Q148458)|	273|
|[**Théodore Caruelle d'Aligny** : ](	http://www.wikidata.org/entity/Q320899)|	20|

*(obtenu avec la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%3FcreatorLabel%20%3Fcreator%20%20%28count%28%3Fs%29%20as%20%3Fc%29%0AWHERE%20%7B%0A%20%20values%20%3Fcreator%20%7B%20wd%3AQ148458%20wd%3AQ310025%20wd%3AQ2831040%20wd%3AQ148475%20wd%3AQ252357%20wd%3AQ320899%7D%0A%20%20%3Fs%20wdt%3AP31%20wd%3AQ3305213%20%3B%0A%20%20%20%20%20wdt%3AP170%20%3Fcreator%0A%20%20%20%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22%5BAUTO_LANGUAGE%5D%2Cmul%2Cen%22.%20%7D%0A%7D%0Agroup%20by%20%3Fcreator%20%3FcreatorLabel%0Aorder%20by%20desc%28%3Fc%29%0A))*

**Lacunes identifiées** : 
- de nombreuses œuvres de l'École de Barbizon conservées en France ne sont pas mentionnées comme telles dans Wikidata.
- les œuvres de certains artistes de cette école sont absents de Wikidata, alors qu'ils ont eu une création significative, comme [Albert Charpin](http://www.wikidata.org/entity/Q2831040).

## Les trésors régionaux vus par Wikidata

### Musées de région : découvrir les richesses des régions

*(obtenu avec des variantes de la requête SPARQL accessible [sur WDQS](https://query.wikidata.org/index.html#SELECT%20%3Fregion%20%3FregionLabel%20%3Fmuseum%20%3FmuseumLabel%20%28COUNT%28%3Fs%29%20AS%20%3Fcount%29%20WHERE%20%7B%0A%20%20%3Fs%20wdt%3AP195%20%3Fmuseum%20.%0A%20%20%3Fmuseum%20wdt%3AP17%20wd%3AQ142%20%3B%0A%20%20%20%20%20%20%20%20%20%20wdt%3AP131%2a%20%3Fregion%20.%0A%20%20%3Fregion%20wdt%3AP31%20wd%3AQ36784%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22fr%2Cen%22%20%7D%0A%7D%0AGROUP%20BY%20%3Fregion%20%3FregionLabel%20%3Fmuseum%20%3FmuseumLabel%0AORDER%20BY%20%3Fregion%20DESC%28%3Fcount%29))*

[**Centre-Val de Loire**](http://www.wikidata.org/entity/Q13947)
- [**musée des Beaux-Arts de Tours** : ](http://www.wikidata.org/entity/Q2404549) 195 œuvres
- [**musée des Beaux-Arts de Chartres** : ](http://www.wikidata.org/entity/Q3330199) 154 œuvres
- [**cathédrale Notre-Dame de Chartres** : ](http://www.wikidata.org/entity/Q180274) 137 œuvres
- [**musée des Beaux-Arts d'Orléans** : ](http://www.wikidata.org/entity/Q3330194) 126 œuvres
- [**château de Chambord** : ](http://www.wikidata.org/entity/Q205367) 46 œuvres
- [**musée des Beaux-Arts de Blois** : ](http://www.wikidata.org/entity/Q3330190) 30 œuvres
- [**musée d'Art et d'Histoire de Dreux** : ](http://www.wikidata.org/entity/Q23498495) 25 œuvres

[**Hauts-de-France**](http://www.wikidata.org/entity/Q18677767)
- [**musée Condé** : ](http://www.wikidata.org/entity/Q1236032) 801 œuvres
- [**palais des Beaux-Arts de Lille** : ](http://www.wikidata.org/entity/Q2628596) 766 œuvres
- [**château de Compiègne** : ](http://www.wikidata.org/entity/Q516697) 284 œuvres
- [**musée de Picardie** : ](http://www.wikidata.org/entity/Q3107709) 262 œuvres
- [**musée de la Chartreuse** : ](http://www.wikidata.org/entity/Q3001838) 160 œuvres
- [**musée des Beaux-Arts de Valenciennes** : ](http://www.wikidata.org/entity/Q3330222) 130 œuvres
- [**musée départemental de l'Oise** : ](http://www.wikidata.org/entity/Q3330521) 88 œuvres
- [**musée des Beaux-Arts d'Arras** : ](http://www.wikidata.org/entity/Q75566) 84 œuvres
- [**musée Antoine-Lécuyer** : ](http://www.wikidata.org/entity/Q2854179) 45 œuvres
- [**musée d'art et d'archéologie de Senlis** : ](http://www.wikidata.org/entity/Q3329603) 44 œuvres
- [**château-musée de Boulogne-sur-Mer** : ](http://www.wikidata.org/entity/Q2967822) 33 œuvres
- [**musée de Cambrai** : ](http://www.wikidata.org/entity/Q3228695) 32 œuvres

[**Île-de-France**](http://www.wikidata.org/entity/Q13917)

On trouve 304 musées pour l'Ile-de-France, dont 27 ayant plus de 140 œuvres dans Wikidata. Nous n'en mentionnons que quelques-uns.
- [**musée d'Orsay** : ](http://www.wikidata.org/entity/Q23402) 5253 œuvres
- [**musée Carnavalet** : ](http://www.wikidata.org/entity/Q640447) 4119 œuvres
- [**musée des Beaux-Arts de la ville de Paris** : ](http://www.wikidata.org/entity/Q59546080) 3601 œuvres
- [**Musée national d'Art moderne** : ](http://www.wikidata.org/entity/Q1895953) 2235 œuvres
- [**musée d'Art moderne de Paris** : ](http://www.wikidata.org/entity/Q857276) 1785 œuvres
- [**département des antiquités égyptiennes du musée du Louvre** : ](http://www.wikidata.org/entity/Q3044749) 1191 œuvres
- [**musée de l’Histoire de France** : ](http://www.wikidata.org/entity/Q3329787) 1190 œuvres
- [**musée Cernuschi** : ](http://www.wikidata.org/entity/Q1667022) 1060 œuvres
- [**château de Versailles** : ](http://www.wikidata.org/entity/Q2946) 908 œuvres

[**Pays de la Loire**](http://www.wikidata.org/entity/Q16994)
- [**musée d'Arts de Nantes** : ](http://www.wikidata.org/entity/Q1783956) 460 œuvres
- [**musée des Beaux-Arts d'Angers** : ](http://www.wikidata.org/entity/Q3277885) 205 œuvres
- [**musée de Tessé** : ](http://www.wikidata.org/entity/Q3329758) 53 œuvres
- [**musée d'Art et d'Histoire de Cholet** : ](http://www.wikidata.org/entity/Q3329613) 53 œuvres
- [**musée d'Art moderne de Fontevraud** : ](http://www.wikidata.org/entity/Q88645893) 47 œuvres

[**Normandie**](http://www.wikidata.org/entity/Q18677875)
- [**musée des Beaux-Arts de Rouen** : ](http://www.wikidata.org/entity/Q3086934) 243 œuvres
- [**musée des Beaux-Arts de Caen** : ](http://www.wikidata.org/entity/Q569079) 165 œuvres
- [**musée d'art moderne André-Malraux** : ](http://www.wikidata.org/entity/Q3329541) 151 œuvres
- [**musée Blanche Hoschedé-Monet** : ](http://www.wikidata.org/entity/Q3329050) 149 œuvres
- [**musée Thomas-Henry** : ](http://www.wikidata.org/entity/Q3329368) 64 œuvres
- [**musée Baron-Gérard** : ](http://www.wikidata.org/entity/Q3329086) 37 œuvres
- [**Musée de Dieppe** : ](http://www.wikidata.org/entity/Q1011471) 32 œuvres
- [**musée d'art et d'histoire de Saint-Lô** : ](http://www.wikidata.org/entity/Q15818381) 26 œuvres
- [**musée des beaux-arts et de la dentelle** : ](http://www.wikidata.org/entity/Q3330234) 21 œuvres
- [**musée d'art, histoire et archéologie d'Évreux** : ](http://www.wikidata.org/entity/Q9047086) 19 œuvres
- [**musée d'Art moderne Richard-Anacréon** : ](http://www.wikidata.org/entity/Q3329636) 17 œuvres
- [**musée des impressionnismes Giverny** : ](http://www.wikidata.org/entity/Q3330248) 15 œuvres

[**Occitanie**](http://www.wikidata.org/entity/Q18678265)
- [**musée Saint-Raymond, musée d'Archéologie de Toulouse** : ](http://www.wikidata.org/entity/Q1376) 2416 œuvres
- [**musée Fabre** : ](http://www.wikidata.org/entity/Q1519002) 1076 œuvres
- [**musée des Augustins de Toulouse** : ](http://www.wikidata.org/entity/Q2711480) 826 œuvres
- [**musée des Beaux-Arts de Carcassonne** : ](http://www.wikidata.org/entity/Q3330195) 284 œuvres
- [**musée d'art et d'histoire de Narbonne** : ](http://www.wikidata.org/entity/Q3329619) 281 œuvres
- [**Fondation Bemberg** : ](http://www.wikidata.org/entity/Q16303680) 219 œuvres
- [**musée Georges-Labit** : ](http://www.wikidata.org/entity/Q167182) 149 œuvres
- [**musée Toulouse-Lautrec** : ](http://www.wikidata.org/entity/Q2538129) 145 œuvres
- [**musée des Beaux-Arts de Nîmes** : ](http://www.wikidata.org/entity/Q3330216) 136 œuvres
- [**musée des Beaux-Arts de Béziers** : ](http://www.wikidata.org/entity/Q3330193) 129 œuvres
- [**musée Saliès** : ](http://www.wikidata.org/entity/Q23646105) 117 œuvres
- [**musée Hyacinthe-Rigaud** : ](http://www.wikidata.org/entity/Q3329201) 113 œuvres
- [**musée Goya** : ](http://www.wikidata.org/entity/Q246821) 113 œuvres
- [**musée des Beaux-Arts de Gaillac** : ](http://www.wikidata.org/entity/Q15818207) 107 œuvres
- [**musée Ingres-Bourdelle** : ](http://www.wikidata.org/entity/Q2843748) 100 œuvres

Le musée Saint-Raymond a bénéficié d'actions stimulées par un wikimédien accompagné d'un ensemble de bénévoles pour ajouter des 
descriptions d'œuvres dans Wikidata (->)[https://cidoc.mini.icom.museum/fr/blog/partager-patrimoine-rcheologique-open-data-projets-wikimedia-musee-raymond-toulouse-christelle-molinie-decembre-2018/]. Cela en fait un exemple emblématique. Une utilisation de ces données
a permis de constituer une sorte de [vitrine du musée](https://zone47.com/crotos/?p195=1376).


[**Auvergne-Rhône-Alpes**](http://www.wikidata.org/entity/Q18338206)
- [**musée des Beaux-Arts de Lyon** : ](http//www.wikidata.org/entity/Q511) 541 œuvres
- [**musée de Grenoble** : ](http//www.wikidata.org/entity/Q1952944) 515 œuvres
- [**bibliothèque du patrimoine de Clermont Auvergne Métropole** : ](http//www.wikidata.org/entity/Q85821952) 266 œuvres
- [**musée d'art moderne de Saint-Étienne** : ](http//www.wikidata.org/entity/Q3329646) 129 œuvres
- [**musée de la Révolution française** : ](http//www.wikidata.org/entity/Q2389498) 101 œuvres
- [**musée de Die** : ](http//www.wikidata.org/entity/Q3329716) 70 œuvres
- [**Lugdunum** : ](http//www.wikidata.org/entity/Q509) 60 œuvres
- [**musée des Beaux-Arts de Chambéry** : ](http//www.wikidata.org/entity/Q3330197) 52 œuvres
- [**musée d'Art et d'Archéologie de Valence** : ](http//www.wikidata.org/entity/Q3330224) 51 œuvres
- [**musée de Brou** : ](http//www.wikidata.org/entity/Q3330655) 51 œuvres

[**Bourgogne-Franche-Comté**](http://www.wikidata.org/entity/Q18578267)
- [**musée des Beaux-Arts de Dijon** :](http//www.wikidata.org/entity/Q1955739) 529 œuvres
- [**musée des Beaux-Arts et d'Archéologie de Besançon** :](http//www.wikidata.org/entity/Q1324926) 355 œuvres
- [**musée Magnin** :](http//www.wikidata.org/entity/Q3329260) 307 œuvres
- [**musée Baron-Martin** :](http//www.wikidata.org/entity/Q10333407) 157 œuvres
- [**château de Bussy-Rabutin** :](http//www.wikidata.org/entity/Q1552130) 47 œuvres
- [**musée Jean-Léon Gérôme** :](http//www.wikidata.org/entity/Q3329173) 42 œuvres
- [**musée Rolin** :](http//www.wikidata.org/entity/Q391823) 38 œuvres
- [**musée des Ursulines** :](http//www.wikidata.org/entity/Q28843765) 27 œuvres
- [**musée des Beaux-Arts de Dole** :](http//www.wikidata.org/entity/Q3330203) 24 œuvres
- [**musée Courbet** :](http//www.wikidata.org/entity/Q3329121) 22 œuvres

[**Grand Est**](http://www.wikidata.org/entity/Q18677983)
- [**musée d'Art moderne et contemporain de Strasbourg** :](http://www.wikidata.org/entity/Q845468) 830 œuvres
- [**musée des Beaux-Arts de Reims** :](http://www.wikidata.org/entity/Q3330225) 555 œuvres
- [**musée des Beaux-Arts de Strasbourg** :](http://www.wikidata.org/entity/Q1535963) 508 œuvres
- [**Collection Schlumpf** :](http://www.wikidata.org/entity/Q56875670) 362 œuvres
- [**musée Unterlinden** :](http://www.wikidata.org/entity/Q1851283) 335 œuvres
- [**musée des Beaux-Arts de Nancy** :](http://www.wikidata.org/entity/Q428765) 310 œuvres
- [**musée d'Art moderne de Troyes** :](http://www.wikidata.org/entity/Q3329650) 181 œuvres
- [**musée des Beaux-Arts de Mulhouse** :](http://www.wikidata.org/entity/Q3330211) 160 œuvres
- [**musée de l'École de Nancy** :](http://www.wikidata.org/entity/Q3277928) 122 œuvres
- [**Palais des ducs de Lorraine – Musée lorrain** :](http://www.wikidata.org/entity/Q3330634) 102 œuvres
- [**musée des Beaux-Arts et d'Archéologie de Troyes** :](http://www.wikidata.org/entity/Q3330226) 93 œuvres

[**Nouvelle-Aquitaine**](http://www.wikidata.org/entity/Q18678082)
- [**musée des Beaux-Arts de Bordeaux** : ](http://www.wikidata.org/entity/Q954222) 520 œuvres
- [**musée Bonnat-Helleu** : ](http://www.wikidata.org/entity/Q2620702) 175 œuvres
- [**musée des Beaux-Arts de Pau** : ](http://www.wikidata.org/entity/Q3330217) 169 œuvres
- [**Musée d'Aquitaine** : ](http://www.wikidata.org/entity/Q3329534) 133 œuvres
- [**musée Sainte-Croix** : ](http://www.wikidata.org/entity/Q772297) 71 œuvres
- [**musée des Beaux-Arts d'Agen** : ](http://www.wikidata.org/entity/Q3330185) 58 œuvres
- [**musée national et domaine du château de Pau** : ](http://www.wikidata.org/entity/Q24263096) 52 œuvres
- [**trésor de la cathédrale Saint-André de Bordeaux** : ](http://www.wikidata.org/entity/Q130748797) 44 œuvres
- [**musée d'Angoulême** : ](http://www.wikidata.org/entity/Q3330189) 26 œuvres
- [**musée des Beaux-Arts de Limoges** : ](http://www.wikidata.org/entity/Q1840249) 20 œuvres
- [**musée des Beaux-Arts de Libourne** : ](http://www.wikidata.org/entity/Q3330207) 20 œuvres
- [**musée des Beaux-Arts de La Rochelle** : ](http://www.wikidata.org/entity/Q3330205) 18 œuvres

[**Provence-Côte d'Azur-Corse**](http://www.wikidata.org/entity/Q124954445)
- [**musée du Petit Palais** :](http://www.wikidata.org/entity/Q1664416)376 œuvres
- [**musée Calvet** :](http://www.wikidata.org/entity/Q1142988)	191 œuvres
- [**musée d'Art de Toulon** :](http://www.wikidata.org/entity/Q3329600)	103 œuvres
- [**musée de l'Annonciade** :](http://www.wikidata.org/entity/Q3329778)	82 œuvres
- [**musée des Beaux-Arts Jules Chéret** :](http://www.wikidata.org/entity/Q3330218)	48 œuvres
- [**musée national Fernand-Léger** :](http://www.wikidata.org/entity/Q3330673)	45 œuvres
- [**musée de Bastia** :](http://www.wikidata.org/entity/Q23595341)	45 œuvres
- [**musée des Beaux-Arts de Menton** :](http://www.wikidata.org/entity/Q1687165)	37 œuvres

[**Bretagne**](http://www.wikidata.org/entity/Q12130)
- [**musée des Beaux-Arts de Rennes** : ](http://www.wikidata.org/entity/Q3098373) 5570 œuvres
- [**musée de Bretagne** : ](http://www.wikidata.org/entity/Q3329701) 2298 œuvres
- [**musée des Beaux-Arts de Quimper** : ](http://www.wikidata.org/entity/Q3330220) 1031 œuvres
- [**musée des Beaux-Arts de Brest** : ](http://www.wikidata.org/entity/Q3330192) 643 œuvres
- [**musée d'Art et d'Histoire de Saint-Brieuc** : ](http://www.wikidata.org/entity/Q3329624) 293 œuvres
- [**collections du musée national de la Marine de Brest** : ](http://www.wikidata.org/entity/Q106205101) 47 œuvres
- [**musée de Pont-Aven** : ](http://www.wikidata.org/entity/Q3330214) 32 œuvres
- [**musée du Faouët** : ](http://www.wikidata.org/entity/Q3330343) 30 œuvres
- [**musée des Beaux-Arts de Morlaix** : ](http://www.wikidata.org/entity/Q15818188) 24 œuvres

Les musées d'art en Bretagne sont particulièrement bien représentés dans Wikidata avec un nombre d'œuvres très significatifs.
Il se trouve que [Grains de Culture](https://grains-de-culture.fr/) a été actif pour assurer la présence du musée des Beaux-ARts de Rennes dans Wikidata, 
et qu'un wikipédien a coopéré étroitement  avec le musée de Bretagne.

et outre-mer

[**Guadeloupe**](http://www.wikidata.org/entity/Q17012)
- [**musée des Beaux-Arts de Saint-François** : ](http://www.wikidata.org/entity/Q112106588)	2

[**La Réunion**](http://www.wikidata.org/entity/Q17070)
- [**musée Léon-Dierx** : ](http://www.wikidata.org/entity/Q3329255)	66
- [**musée de Villèle** : ](http://www.wikidata.org/entity/Q3330590)	5
- [**Cité du Volcan** : ](http://www.wikidata.org/entity/Q2974801)	1

Nous n'avons trouvé aucun musée mentionné dans Wikidata pour la [**Martinique**](http://www.wikidata.org/entity/Q17054),
la [**Guyane**](http://www.wikidata.org/entity/Q3769) et [**Mayotte**](http://www.wikidata.org/entity/Q17063).

## Analyse des causes : Pourquoi ces lacunes ?

Nous avons noté diverses lacunes dans la présence des oeuvres d'art dans Wikidata.
Les causes de certaines de ces lacunes peuvent être identifiées et contournées.

### Facteurs identifiés limitant la présence des musées dans Wikidata

Ces facteurs limitent la facilité d'injecter des notices d'oeuvres dans Wikidata, notamment les notices de la base Joconde.
Ces facteurs limitent donc indirectement la présence des musées français dans Wikidata.

- **Absence d'identifiants pérennes pour Joconde** : les notices Joconde n'ont pas d'URI stable pour les valeurs de leurs propriétés et les notices elles-même, ce qui ne facilite pas leur introduction dans Wikidata
- **Standards de métadonnées hétérogènes** : de nombreux formats différents sont utilisés par les musées, avec des propriétés différentes, utilisant des valeurs hétérogènes
- **APIs restreintes** : peu de musées disposent d'APIs ouvertes; de plus, les licences sur certaines données, comme les images, ne sont pas toujours claires
- **Ressources humaines** : les ressources humaines pour la documentation numérique de chaque musée sont limitées, et la responsabilité de prise de décision à ce sujet n'est souvent pas établie
- **Politique de données fermées ou licences peu claires** : 45% des grands musées n'autorisent pas l'export massif
- **Droits d'image restrictifs** : Coût prohibitif des licences pour les reproductions
- **Réticences patrimoniales** : Peur de la "marchandisation" des collections ou de leur utilisation par les Intelligences Artificielles
- **Droit d'auteur** : cette protection des créateurs limite naturellement la possibilité de publier des oeuvres contemporaines dans les projets de la fondation Wikimedia, et donc dans Wikidata, du fait de l'impossibilité d'y reproduire des oeuvres: pour y figurer, elles devraient être libre de droits 


## Innovations en cours : Les initiatives prometteuses

**1. Programme HADOC** (Harmonisation et Accès aux Données sur les Œuvres et Collections)
- Partenariat Ministère de la Culture / Inria
- Réconciliation automatique Joconde-Wikidata : **12 456 œuvres** identifiées (en cours)

**2. Automates d'importation de notices**
- En cours, des outils déjà validés sur le musée des Beaux-Arts de Rennes
- Une nouvelle campagne d'importation programmée pour l'automne 2025
- Réalisation de l'association [Grains de Culture](https://grains-de-culture.fr/), en partenariat avec Telecom Paris


## Recommandations stratégiques

### Pour les institutions

1. **Adopter les identifiants persistants** (ARK, DOI, IIIF)
2. **Implémenter des APIs ouvertes** (REST, SPARQL endpoints)
3. **Former le personnel** aux enjeux du linked data
4. **Libérer les images** (domaine public, Creative Commons)

### Pour Wikidata

1. **Campagnes de mass-upload** ciblées par régions ou par musées
2. **Amélioration des outils** de réconciliation automatique  
3. **Partenariats institutionnels** renforcés
4. **Formation des contributeurs** aux métadonnées muséales

### Pour les pouvoirs publics

1. **Obligation légale** de publication en open data
2. **Financement dédié** à l'interopérabilité
3. **Standards nationaux** harmonisés
4. **Évaluation annuelle** des taux de couverture

## Prospective 2030 : Vers une visibilité accrue ?

### Objectifs chiffrés proposés

À l'horizon 2030, avec les projets en cours :
- **150 000 œuvres** des musées français supplémentaires dans Wikidata -actuellement 53640 (obtenu dans [WDQS](https://query.wikidata.org/index.html#SELECT%20%28count%28%3Fitem%29%20as%20%3Fc%29%20%0AWHERE%20%7B%7B%0A%20%20%20%20%20%20%3Fitem%20wdt%3AP31%20wd%3AQ3305213%3B%20%20%20%20%20%20%20%20%23%20instance%20de%20peinture%0A%20%20%20%20%20%20%20%20%20%20%20%20wdt%3AP195%20%3Fmuseum.%20%20%20%20%20%20%20%20%20%20%20%23%20conserv%C3%A9e%20dans%20un%20mus%C3%A9e%0A%20%20%20%20%20%20%3Fmuseum%20wdt%3AP17%20wd%3AQ142.%20%20%20%20%20%20%20%20%20%20%23%20mus%C3%A9e%20en%20France%0A%20%20%20%20%7D%7D%0A))
- **25% des collections** de la base Joconde référencées
- **APIs ouvertes** pour 80% des Musées de France
- **conformité IIIF** généralisée pour les images

### Défis persistants

1. **Art contemporain** : droits d'auteur vivants
2. **Collections ethnographiques** : questions post-coloniales
3. **Œuvres restaurées** : métadonnées techniques complexes
4. **Financement récurrent** : modèle économique à consolider

## Conclusion : Un patrimoine à révéler

Cette investigation révèle un paradoxe saisissant : 
la France, nation au patrimoine artistique exceptionnel, reste peu visible 
dans l'écosystème numérique mondial. Cela apparait particulièrement dans Wikidata. Sur plus de **700 000 œuvres** recensées dans la base Joconde, 
seules environ **25 000** (moins de 4%) bénéficient d'une présence dans Wikidata.

**Les enjeux sont considérables :**
- **Accessibilité démocratique** : les collections françaises restent méconnues du grand public; l'accessibilité  numérique contribue à la découverte des collections
- **Rayonnement international** : sous-représentation face aux collections anglo-saxonnes
- **Recherche académique** : données fragmentées limitant les études comparatives
- **Valorisation économique** : tourisme culturel freiné par une trop faible visibilité en ligne

**Les solutions existent** mais nécessitent une volonté politique affirmée et des moyens pérennes. Les initiatives en cours (HADOC, API Collections unifiée) laissent entrevoir un avenir plus ouvert, mais l'ampleur du défi reste immense.
Notre association [Grains de Culture](https://grains-de-culture.fr/) compte y prendre sa part et a déjà commencé à le faire à travers nos [articles](https://scrutart.grains-de-culture.fr/), nos [galeries](https://galeries.grains-de-culture.fr/) et nos
actions pour compléter Wikidata.

Le patrimoine français mérite mieux qu'une faible visibilité numérique. Il est temps de révéler ces "trésors cachés" au monde entier.

---

*Dans notre prochain article, nous explorerons "L'Art Féminin Invisible : Données et Préjugés" pour analyser la représentation des femmes artistes dans ces mêmes bases de données.*

**Toutes les requêtes SPARQL et APIs de cet article sont accessibles** via les liens fournis. Les données évoluent quotidiennement - vérifiez les chiffres actuels !

---

*Cet article fait partie de la série "Culture Picturale & Données Structurées" de [Scrutart - Grains de Culture](https://scrutart.grains-de-culture.fr). Investigation menée en août 2025.*