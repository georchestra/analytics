
# Réflexions sur un module "georchestra-statistics" dans geOrchestra


Prise de notes / jeté de notes réalisé lors du code sprint du geOcom 2023, le 01/06/2023.



## Eléments à prendre en compte dans la réflexion

### Données sources

Passer par les logs du SP / Gateway : 

   * Approche générique
   * Homogénéïté 
   * Exaustivité de la source (par rapport aux metrics des différents modules)
   * Certains modules n'ont pas de metrics (besoin d'aller à la source)


Etudier possibilité (à terme) d'intégrer les logs de SDI-Concistency-Check



### Historisation des logs

Durée de conservation

Aggrégation des données à conserver/analyser

Volume de données à stocker



### Contraintes techniques et architecture 

Rester sur une approche relativement "générique" et facilement déployables (dans l'approche de geOrchestra). Exemple: toutes les plateformes ne disposent pas d'un stockage S3.



Il apparaît évident que nous allons probablement coder / configurer un "machin" qui va servir de loganalizer des logs bruts du GateWay. En sortie il sortira un log / fichier qui contiendra les infos utiles par modules geOrchestra. Ce module sera ensuite lu par le "produit" qui va analyser cette donnée brute.





### Type de stockage + structure

Pose la question :

   * Des volumes
   * Des performances
   * De l'accessibilité/exploitabilité par les solution de reporting
   * Des conséquences techniques (sujet transversal)


Solutions évoquées

   * Elastic Search
   * PostGreSQL
   * TSDB
   * ...


### Outil de reporting

Solutions évoquées : (cf. ressources)

   * Matomo => trop spécifique aux sites internet
   * Développement à façon => quelle techno ? Question de la mise à jour/maintenance ?
   * Plateforme de type Matomo ou Superset
   * Graphana


### Indicateurs à suivre

Cf. "Besoins des admins de plateformes"



## Besoins des admins de plate-formes



Cas 1 : je veux savoir quelles ont été les n couches les plus utilisées la semaine dernière / le mois dernier / sur une période donnée. Mais je veux pouvoir :

   * exclure les couches de cache (TMS / WMTS)
   * filtrer par workspace
   * filtrer par organisme


Cas 2 : je veux voir l'évolution de l'utilisation de la fonction "export de bordereaux par lot" de cadastrapp depuis 2020. Au global puis en discriminant par organisme.



Cas 3 : Pour un utilisateur donné je veux voir l'évolution de sa consommation d'une couche précise et/ou d'une liste de 3 couches (car représentatives d'une thématique particulière).



Cas 4 : Pour un utilisateur donné je veux voir l'évolution de son utilisation d'un contexte MapStore sur le dernier trimestre



Cas 5 : je veux connaître le nombre de téléchargement d'une ressource à partir de son URL (ex.: fichier de données au format ZIP). Exemple Data Grand Est, l'url du lien est affichée sur data.gouv.fr et fait référence à un fichier stocker sur le serveur datagrandest.fr /mnt/apache\_nas\_data/...



Cas  6 : pour GeoNetwork je veux avoir un camenbert qui donne la répartition sur une période de temps donnée entre les appels HTML et les appels XML pour visualiser une métadonnée. Les appels HTML correspondent à un utilisateur qui va sur l'UI de GN pour lire la métadonnée- complète tandis que l'appel XML correspond à un client (MapStore, Mviewer, autre) qui fait appel à la MD et la montre dans l'outil client.



Cas 7 : données d'utilisation (à définir...) des outils (mapstore2, mviewer, ...) par contexte ou carte.

(= fréquence d'accence d'accès à l'URL du contexte ou de la carte ?)



Cas 8 : activation/désactivation des plugin dans MapStore (plugin les plus utilisés/non utilisés)



Cas 9 : statistiques sur l'annuaire/console => nombre de connexion par user / user qui ne sont pas connectés depuis un certain temps (x mois / x année)



*Cas X : connaître le nombre de métadonnées de GN et donénes dans GS présentant une erreur [cf. sdi-consistency-check]*









## Ressources



### Matomo

[https://fr.matomo.org/faq/general/how-do-i-run-the-log-file-importer-script-with-default-options/](https://fr.matomo.org/faq/general/how-do-i-run-the-log-file-importer-script-with-default-options/)

[https://fr.matomo.org/faq/general/import-additional-data-including-bots-static-files-and-http-errors-tracking/](https://fr.matomo.org/faq/general/import-additional-data-including-bots-static-files-and-http-errors-tracking/)

[https://github.com/matomo-org/matomo-log-analytics/](https://github.com/matomo-org/matomo-log-analytics/)



georchestra\_ogc\_stats\_analyze

[https://github.com/MaelREBOUX/georchestra\_ogc\_stats\_analyze](https://github.com/MaelREBOUX/georchestra\_ogc\_stats\_analyze)



### GoAccess

[https://goaccess.io/features](https://goaccess.io/features)



### Benthos

[https://www.benthos.dev/](https://www.benthos.dev/)

[https://studio.benthos.dev/](https://studio.benthos.dev/)



Timescale + Apache Superset

[https://i.imgur.com/8n4UwfB.png](https://i.imgur.com/8n4UwfB.png)



### Python

[https://akshayranganath.github.io/Using-Python-Pandas-for-Log-Analysis/](https://akshayranganath.github.io/Using-Python-Pandas-for-Log-Analysis/)

[https://www.youtube.com/watch?v=MbflVr-MBm0](https://www.youtube.com/watch?v=MbflVr-MBm0)






### Elasticsearch / Logstash / Kibana



(Pierre Mauduit) Dans le cadre du codesprint, j'ai fait quelques essais, je voulais voir sur une plateforme avec une fréquentation modérée (georhena) ce que cela prenait comme ressources de charger dans un index elasticsearch les logs de traefik disponibles sur le serveur, j'ai utilisé une compo docker à moi, que je déploie quand j'ai besoin d'ingester facilement des données dans un elasticsearch, puis faire un peu de visualisation dans ces données ([https://github.com/pmauduit/minimalist-elk)](https://github.com/pmauduit/minimalist-elk)).



#### Logs



203MB de logs (mix de fichier textes et de fichiers gzippés)

amplitude de temps: Jun 18, 2022 @ 10:17:57.000 -> Jun 21, 2023 @ 10:21

Temps de processing (ingestion dans logstash): 15:53 -> 16:24 ~ 30 Minutes



#### Volumétrie



Taille de l'index ES après ingestion: 927.8MB

nombre de documents (~ hits / lignes): 5,175,098

En supprimant les erreurs de parsing au niveau logstash ("grok parse failure"): 5,172,388

 

Bizarrement il manque mai 2023, mais cela n'est pas génant pour juste extrapoler.

Kibana fournit ensuite une interface pour explorer ses données, mais tout est à construire afin de faire parler ces données. Il pourrait être également intéressant de faire revivre cette contribution: [https://github.com/elastic/logstash-contrib/blob/master/lib/logstash/filters/wms.rb](https://github.com/elastic/logstash-contrib/blob/master/lib/logstash/filters/wms.rb) (damn, 10 ans déjà).
