
# Prise de notes atelier analytics du 18/10/2023


## Metrics VS Analytics

Les administrateurs techniques de plateformes ont besoin de métriques particulières afin de déterminer si la plate-forme technique est en bonne santé, ou pas, si un problème risque d'arriver dans x temps.

Les administrateurs de contenu de plateformes ont eux besoin de statistiques sur des temporalités différentes : à la semaine, au moins, à l'année et cherchent plutôt à qualifier l'usage qui est fait de la plate-forme.


## Étapes


### Étape 1 : collecte des logs par le SP / le Gateway / le frontal web

On est d'accord sur le principe que ces 3 briques doivent savoir capter les requêtes et les stocker.

Le SP sait récupérer les informations classiques (pour un serveur web) suivantes d'une requête HTTP :

-  code HTTP de réponse
-  la taille
-  le temps de réponse 

Le SP ne sait pas toujours récupérer :

- GeoIP en fonction de l'environnement (pb dans un environnement Kubernetes, peut-être Docker)




### Étape 2 : stocker les informations : écrire des logs au format CLF log format

Afin d'éviter un goulet d'étranglement sur l'écriture dans la base de données il est retenu d'écrire dans un ou des fichiers de logs temporaires. 

Ces fichiers de logs seront ensuite lus dans un autre temps (1 h ? 1/2 journée ? 1 journée ?) par un analyseur qui lui va aller écrire dans la base de données.

Une piste est de formater ces log au format [Common Log Format (CLF)](https://en.wikipedia.org/wiki/Common_Log_Format).

`172.22.0.1 - testuser|Project Steering Committee|ROLE_USER [01/Nov/2017:07:28:29 +0000] "GET 
http://geonetwork:8080/geonetwork/srv/eng/catalog.search
 HTTP/1.1" 200 - "-" "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0" - "geonetwork" "-" 211ms `




### Étape 3 : lire les logs, extraire de l'information et les stocker en base de données

Il est retenu le principe d'écrire un logiciel (Python pressenti) qui va se baser sur un ensemble de règles écrites en expression régulière.


Les informations identifiées à extraire sont :

- horodatage
- user
- organisation
- objet JSON avec les rôles geOrchestra
- url GET complète
- user agent
- nom / code de l'application. Exemple : geonetwork, geoserver, cadastrapp_api, cadastrapp_client
- objet JSON avec la logique métier de l'application
- temps de réponse
- taille de la réponse en octet
- code HTTP de la réponse
- type MIME de la réponse

L'analyseur devra gérer le temps UTC pour le covnertir en temps Time/Zone plus exploitable par les administrateurs de plate-forme.


### Étape 4 : TimescaleDB pour stocker


Pour :

- c'est du PostgreSQL : vu, connu et maîtriser par la communauté
- cela semble très performant
- les fournisseurs de solutions cloud supportent TimeScaleDB (OVH, Scaleway)

Contre :

- ?


La logique propre à chaque application / brique / module sera stocké dans un attribut JSON.

Exemples :

- L'appel de la fonction "Unité foncière de Cadastrapp" sera stockée de cette façon :
	- horodatage avec info sur la zone de temps : `2022-04-25T00:03:18.179408+02:00:`
	- user : `mreboux`
	- organisation : `Rennes Métropole`
	- rôles geOrchestra (JSON) : `["ROLE_EL_RM_PISU_DEI","ROLE_EL_APPLIS_RMTR","ROLE_EL_APPLIS_CAD_CNIL2","ROLE_USER","ROLE_EL_RM_PISU_DEI_MOE"] `
	- url GET complète : `/cadastrapp/services/getInfoUniteFonciere?parcelle=350238000KV0626`
	- user agent : `Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0`
	- application : `cadastrapp_api`
	- objet JSON avec la logique métier de l'application : `{"fonction":"getInfoUniteFonciere","commune":"35238"}`
	- temps de réponse : `211ms`
	- taille de la réponse : `27599`
	- code HTTP de la réponse : `200`

- Un appel getMap WMS GeoServer
	- horodatage avec info sur la zone de temps : `2022-04-25T00:03:18.179408+02:00:`
	- user : `mreboux`
	- organisation : `Rennes Métropole`
	- rôles geOrchestra (JSON) : `["ROLE_EL_RM_PISU_DEI","ROLE_EL_APPLIS_RMTR","ROLE_EL_APPLIS_CAD_CNIL2","ROLE_USER","ROLE_EL_RM_PISU_DEI_MOE"] `
	- url GET complète : `/geoserver/ows?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&FORMAT=image%2Fpng8&TRANSPARENT=true&LAYERS=ref_topo%3Armtr_surf_nivellement&STYLES=&SRS=EPSG%3A3857&CRS=EPSG%3A3857&TILED=false&WIDTH=512&HEIGHT=512&BBOX=-186243.3692399487%2C6124500.0570042245%2C-186098.91235613593%2C6124644.513888037`
	- user agent : `Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0`
	- application : `geoserver`
	- objet JSON avec la logique métier de l'application : 

```json
{
	"service":"wms",
	"request":"getmap",
	"format":"image/png8",
	"workspace":"ref_topo",
	"layer":"rmtr_surf_nivellement",
	"projection":"EPSG:3857",
	"size":"512x512",
	"tiled":"false",
	"bbox":"[-186243.3692399487,6124500.0570042245,-186098.91235613593,6124644.513888037]"
}
```

	- temps de réponse : `211ms`
	- taille de la réponse : `27599`
	- code HTTP de la réponse : `200`


### Étape 5 : Exploiter, visualiser

Il faut un outil de type Business Object, en open source. Donc [Apache Superset](https://superset.apache.org/) est pressenti pour être cette brique de visualisation.

On peut intégrer un mviewer dans un dashboard Superset.


## Interrogations

### Format de log : common ou combined ?

Bien écrire / déterminer les informations que l'on veut stocker. TODO


### Granularité MapStore

1 log = MapStore
ou
1 log = MapStore + fonction


### exploitation attribut JSON par TimescaleDB

Cela va déterminer le "grain" de stockage. Donc à tester vite TODO.


### Temps UTC / Temps Time/Zone

à gérer ! On va stocker