# Presentation

## Component Architecture

Two scenarii will be considered:

- collecting usage data from the Security Proxy / Gateway access logs
- collecting usage data from file-based access logs data (e.g. reverse-proxy access logs)

### Scenario 1: Automated workflow

_Collecting usage data from the Security Proxy / Gateway access logs_

#### Workflow

![workflow](../../d2/workflow_standard.svg)

#### Checklist

- Read the full installation doc before proceeding
- Preparation
    - [x] [Superset up and running](./configuration/superset.md)
      - [x] [Timescale DB up and running](./installation.md#timescaledb)
        - [x] [Use gateway v. >= 2.0.3](./prerequisites.md#gateway-version)
- Configuration
    - [x] [Have gateway expose logs using OpenTelemetry](./configuration/gateway.md)
        - [x] Run and configure Vector:
            - [Run vector](./installation.md#opentelemetry-support)
            - [Configure vector](./configuration/vector.md)
        - [x] [Set up the analytics CLI as a cron task](./configuration/analytics-cli.md)
        - [x] [Import Analytics dashboards in Superset](./configuration/superset.md)]
- [Troubleshooting](./troubleshooting.md)

### Scenario 2: Manual, file-based workflow

_Manually pushing access log files_

#### Workflow

The Security Proxy/Gateway are the place where most of the information is available
(user information, http requests, response time and success) so this is the first
place to look at.

It is also possible to read access logs from a classic reverse proxy like Apache,
nginx etc. The only difference is that you won't get the user information (id, roles, org).

But you will also probably want to feed the database with historic access logs collected over time to preseed the
database with as much information as possible.

![workflow](../../d2/workflow_manual.svg)

This scenario will skip the OpenTelemetry part: the logs will be directly processed by the Analytics CLI and pushed on
the database. Main related documentation pages:

- [TimescaleDB configuration](./configuration/timescaledb.md)
- [Analytics CLI configuration](./configuration/analytics-cli.md)
- [Superset configuration](./configuration/superset.md)
- TODO: check the list of related pages

#### Checklist

-  Read the full installation doc before proceeding
- Preparation
    - [x] [Superset up and running](./configuration/superset.md)
    - [x] [Timescale DB up and running](./installation.md#timescaledb)
- Configuration
    - [x] [Configure the analytics CLI](./configuration/analytics-cli.md)
    - [x] [Import Analytics dashboards in Superset](./configuration/superset.md)]
- [Troubleshooting](./troubleshooting.md)