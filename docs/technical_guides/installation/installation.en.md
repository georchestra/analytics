# Installation


## Apache Superset

It was already listed as a prerequisite, but chances are it's not yet installed on your platform.
It is used for the last and most remarkable stage: dashboards !

geOrchestra maintains a [dedicated doc](https://docs.georchestra.org/superset/en/latest/) on how to deploy and configure Apache Superset, please refer to it  for deployment.

## TimescaleDB

This is a database solution, targeting massive time-series data. It is actually an extension over PostgreSQL. Since we already deal with PostgreSQL in geOrchestra, this makes TimescaleDB a very good match for storing and managing our analytics data.

TimescaleDB provides documentation about how to self-host an instance: https://docs.timescale.com/self-hosted/latest/. Or you can also opt for a SAAS database (paid option of course).

Like plain PostgreSQL, it is possible to deploy a light database service or a full-fledged HA service, on-premise or as a SAAS, depending on your choices and needs. _**This will be up to you to decide how you want to host it.**_

The docker compose and helm chart will come with an optional built-in light installation of TimescaleDB (no HA, no QoS warranty).

## OpenTelemetry support

[OpenTelemetry](https://opentelemetry.io/) is an open standard for observability data. It is used in this module to collect the logs from your gateway/security proxy service.

Installation implies:

- configure the Gateway/security proxy to use the OpenTelemetry java agent and expose the enhanced access logs (see [Configuring access logs](configuration/index.md))
- run an OpenTelemetry-capable service, [Vector](https://vector.dev/docs/reference/configuration/sources/opentelemetry/), in charge of collecting the logs and shipping them to the database.

[Vector](https://vector.dev/docs) can be installed:

- [as a single binary](https://vector.dev/docs/administration/management/#linux)
- [run as a systemd service](https://vector.dev/docs/administration/management/#linux)
- deployed using docker (already configured in the provided docker-compose.yml)
- deployed using kubernetes (already included in the geOrchestra Helm chart as an optional feature)

TODO: implement docker-compose and feature in helm chart

Vector comes with a yaml configuration file. For the docker and k8s setups, a default config file will be provided.

A sample configuration file is provided in the [vector configuration page](configuration/vector.md).

## Python cron task

Part of the logs processing will be done by a Python script. Since you want it to be run on a regular basis, you will have to make it run as a cron task

TODO: document

TODO: consider https://github.com/christopher-besch/docker_cron for the docker compose ?
