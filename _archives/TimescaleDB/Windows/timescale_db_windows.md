
# Installer TimescaleDB sur Windows

# Configuration

- Windows 10 / Windows 10 wokstation
- PostgreSQL 13.8
- PostGIS 3.2


## Installation

Selon [https://docs.timescale.com/self-hosted/latest/install/installation-windows/](https://docs.timescale.com/self-hosted/latest/install/installation-windows/)


Aller sur [https://docs.timescale.com/self-hosted/latest/install/installation-windows/#windows-releases](https://docs.timescale.com/self-hosted/latest/install/installation-windows/#windows-releases) et récupérer l'installeur pour PostgreSQL 13.

Dézipper.

Aller dans le répertoire et faire un clic-droit sur le fichier `setup.exe` pour le lancer en tant qu'administrateur (ou pas selon la configuration de votre poste et/ou le résultat souhaité).

```
2023/10/26 16:27:35 WELCOME to TimescaleDB Windows installer!
2023/10/26 16:27:35 Will use pg_config found at:  C:\applications\postgresql\13.8\bin\pg_config.exe
2023/10/26 16:27:36 Will copy dll files to:  C:/APPLIC~1/POSTGR~1/13.8/lib
2023/10/26 16:27:36 timescaledb-tune is a program that modifies your postgresql.conf configuration to be optimized for your machine's resources.
Do you want to run timescaledb-tune.exe now? [(y)es / (n)o]: y
Please enter the path to your postgresql.conf:
H:\postgresql_data\13\data\postgresql.conf
== Using postgresql.conf at this path:
H:\postgresql_data\13\data\postgresql.conf

== Writing backup to:
C:\Users\M8CF9~1.REB\AppData\Local\Temp/timescaledb_tune.backup202310261629

== shared_preload_libraries needs to be updated
== Current:
#shared_preload_libraries = ''
== Recommended:
shared_preload_libraries = 'timescaledb'
-- Is this okay? [(y)es/(n)o]: y
SUCCESS: shared_preload_libraries will be updated

-- Tune memory/parallelism/WAL and other settings? [(y)es/(n)o]: y
== Recommendations based on 15.78 GB of available memory and 8 CPUs for PostgreSQL 13

== Memory settings recommendations
== Current:
shared_buffers = 128MB
#effective_cache_size = 4GB
#maintenance_work_mem = 64MB
#work_mem = 4MB
== Recommended:
shared_buffers = 512MB
effective_cache_size = 12118MB
maintenance_work_mem = 2019MB
work_mem = 6675kB
-- Is this okay? [(y)es/(s)kip/(q)uit]: y
SUCCESS: memory settings will be updated

== Parallelism settings recommendations
== Current:
MISSING: timescaledb.max_background_workers
#max_worker_processes = 8
#max_parallel_workers_per_gather = 2
#max_parallel_workers = 8
== Recommended:
timescaledb.max_background_workers = 16
max_worker_processes = 27
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
-- Is this okay? [(y)es/(s)kip/(q)uit]: y
SUCCESS: parallelism settings will be updated

== WAL settings recommendations
== Current:
#wal_buffers = -1
min_wal_size = 80MB
== Recommended:
wal_buffers = 16MB
min_wal_size = 512MB
-- Is this okay? [(y)es/(s)kip/(q)uit]: y
SUCCESS: WAL settings will be updated

== Background writer settings recommendations
SUCCESS: background writer settings are already tuned

== Miscellaneous settings recommendations
== Current:
#default_statistics_target = 100
#random_page_cost = 4.0
#checkpoint_completion_target = 0.5
#max_locks_per_transaction = 64
#autovacuum_max_workers = 3
#autovacuum_naptime = 1min
== Recommended:
default_statistics_target = 100
random_page_cost = 1.1
checkpoint_completion_target = 0.9
max_locks_per_transaction = 128
autovacuum_max_workers = 10
autovacuum_naptime = 10
-- Is this okay? [(y)es/(s)kip/(q)uit]: y
SUCCESS: miscellaneous settings will be updated
== Saving changes to: H:\postgresql_data\13\data\postgresql.conf
2023/10/26 16:32:40 Installing TimescaleDB library files...
2023/10/26 16:32:40 Success!
2023/10/26 16:32:40 Installing TimescaleDB control file...
2023/10/26 16:32:40 Success!
2023/10/26 16:32:40 Installing TimescaleDB SQL files...
2023/10/26 16:32:40 Success!
TimescaleDB installation completed successfully.
Press ENTER/Return key to close...
```


Se connecter à la base de données `georchestra` et rajouter l'extension : 

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;

WELCOME TO
 _____ _                               _     ____________  
|_   _(_)                             | |    |  _  \ ___ \ 
  | |  _ _ __ ___   ___  ___  ___ __ _| | ___| | | | |_/ / 
  | | | |  _ ` _ \ / _ \/ __|/ __/ _` | |/ _ \ | | | ___ \ 
  | | | | | | | | |  __/\__ \ (_| (_| | |  __/ |/ /| |_/ /
  |_| |_|_| |_| |_|\___||___/\___\__,_|_|\___|___/ \____/
               Running version 2.11.1
For more information on TimescaleDB, please visit the following links:

 1. Getting started: https://docs.timescale.com/timescaledb/latest/getting-started
 2. API reference documentation: https://docs.timescale.com/api/latest
 3. How TimescaleDB is designed: https://docs.timescale.com/timescaledb/latest/overview/core-concepts
```

Puis créer le schéma `analytics`, à côté des autres schémas déjà présents :

```sql
CREATE SCHEMA analytics AUTHORIZATION georchestra;
```


## Utilisation sur les tables ogcstatistics

On crée une table unique :

```sql
DROP TABLE IF EXISTS analytics.ogc_services;
CREATE TABLE analytics.ogc_services (
   site integer NOT NULL
  , "timestamp" timestamp with time zone NOT NULL
  , org text NULL
  , user_name text NULL
  , roles text NULL
  , service text NULL
  , request text NULL
  , layer text NULL
);

CREATE INDEX ogc_services_idx_site ON analytics.ogc_services (site) ;
CREATE INDEX ogc_services_idx_org ON analytics.ogc_services (org) ;
CREATE INDEX ogc_services_idx_user_name ON analytics.ogc_services (user_name) ;
CREATE INDEX ogc_services_idx_service ON analytics.ogc_services (service) ;
CREATE INDEX ogc_services_idx_layer ON analytics.ogc_services (layer) ;
```

On crée une hypertable avec un intervalle de temps pour le stockage de 7 jours / 1 semaine :

```sql
DROP TABLE IF EXISTS analytics.ogc_services;
SELECT create_hypertable(
  'analytics.ogc_services',
  'timestamp',
   chunk_time_interval => INTERVAL '1 week'
);
```

On remplit :

```sql
INSERT INTO analytics.ogc_services
  (site, "timestamp", org, user_name, roles, service, layer, request) 
  SELECT 2, "date", org, user_name, roles, service, layer, request
  FROM ogcstatistics.ogc_services_log_y2023m9 
;
```


Ensure that you set the datatype for the time column as timestamptz and not timestamp. For more information, see PostgreSQL timestamp.

https://docs.timescale.com/use-timescale/latest/schema-management/indexing/

https://docs.timescale.com/use-timescale/latest/continuous-aggregates/about-continuous-aggregates/

https://docs.timescale.com/use-timescale/latest/ingest-data/import-csv/