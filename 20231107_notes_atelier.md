
# Prise de notes atelier analytics du 07/11/2023


## Discussion autour de TimescaleDB

Les participants échangent sur leurs tests respectifs de la mise en place de TimescaleDB.

### Installation, configuration

Il resssort les éléments suivants :

- Pas de difficultés d'installation sur Linux. Pas d'appréhension pour Docker. Sur Windows il a fallu trouver une version fonctionnelle (2.11.1 sur PostgreSQL 11.8)
- **Analytics sera une base de données dédiée**. Plusieurs raisons à cela :
 - TimescaleDB installe 7 schémas spécifiques pour travailler
 - il faut une configuration postgresql.conf spécifique pour de la performance
 - les requêtes peuvent être longues et il ne s'agit pas de perturber les autres données applicatives
 - si sauvegarde de la base de données elle sera très spécifique et que vu les volumes potentiels, il faut une stratégie adaptée

Il va également falloir déterminer la période de stockage (chunk_time_interval).
**On s'accorde sur le principe de régler ce paramètre sur 1 semaine** (qui est le paramètre par défaut).

`chunk_time_interval => INTERVAL '1 week'`


### Rétention, optimisation

Les participants n'ont pas été plus loin sur les tests mais le questionnement porte sur :

- la mise en place d'une agrégation continue -> https://docs.timescale.com/use-timescale/latest/continuous-aggregates/
- la durée de rétention = la période à partir de la quelle on va "effacer" certaines informations -> https://docs.timescale.com/use-timescale/latest/data-retention/

Il semble ressortir que ce qu'il nous faut est décrit ici : [https://docs.timescale.com/use-timescale/latest/data-retention/data-retention-with-continuous-aggregates/](https://docs.timescale.com/use-timescale/latest/data-retention/data-retention-with-continuous-aggregates/).



## État du développement de l'analyseur de log


- on lit une ligne de log
- on récupère les informations de base : timestamp, username, rôles, url, application, infos HTTP
- ensuite on charge le module d'analyse dédié à l'application. Jean a développé la base du module `geoserver` et de `geonetwork`. La logique métier est analysée et stockée dans un dictionnaire Python
- on écrit ensuite un fichier CSV
- ce fichier CSV est ensuite chargé dans une table en base


## Politique de rétention des log <<< IMPORTANT

Il ressort qu'il va falloir faire des préconisations sur la politique de rétention des logs nginx / apache / HAProxy. Sinon on n'aura pas assez d'homogénéité sur les infos à traiter.

L'idée basique est de faire une rotation du log du jour sans compression. On obtient un fichier `monlog.log.1`.
Et ensuite le script va analyser ce log "de la veille".


## Gérer différents sites dans une même base

Ne pas oublier la notion de "site". Exemple à Rennes il y a 3 plates-formes geOrchestra.
Cela se traduit par un attribut `site` à ajouter.


## Gestion du projet

On décide de sortir du mode POC pour passer en mode DEV.
Donc à faire sur le repo github :

- mettre dans un dossier 'archives' les POC
- on passe en anglais
- on initialise un répertoire 'docs' avec le template de documentation geOrchestra
- préparer des labels dans les issues pour cahque 'parties' (script, timescaledb, superset)
- on fait des issues à partir de maintenant

