# Collecting access logs

_**From the Security Proxy/Gateway to the storage database.**_


_Note_: This is the part of the data flow where diversity happens.



## Conservative workflow

This usecase considers a classic approach where the Secuirty Proxy/Gateway app writes access logs in *files*. Those files are traditionnally rotated to avoid them getting huge.

We can consider for instance setting the file rotation to a daily basis. Which means that after midnight, the access logs from the previous day are not written to anymore. They are thus ready for processing.

A python CLI module can then be configured to process_line this rotated access logs file. It filters the relevant lines, extracts the relevant information and feeds the data into the storage database.

TODO:
- schema
- recommendations on supported log formats (examples, how to configure)
- example CLI command
- link to the CLI's doc

### Configuring file-based access logs on the Security Proxy
TODO

### Configuring file-based access logs on the Gateway
TODO

### Rotating access log files
TODO

## Cloud "light" workflow (small to medium infrastructure)
In modern "cloud" infrastructures, writing log files is not the preferred option. It is considered better practice to collect them and store them on an online service.

In this usecase, the suggested option is to configure the Security Proxy/Gateway's logging library to write the access logs into a JDBC target. Both Logback and log4j2 support this. This allows to write the access ogs directly into the storage database. Since there will be some processing to be performed, the target table will act as a buffer, with temporary content, ready for processing.

A cron task (python CLI) will then retrieve the entries from this table and process_line them for storage (in the storage Hypertable in the same DB).

TODO: schema

### Configuring JDBC access logs on the Security Proxy
TODO

### Configuring JDBC access logs on the Gateway
TODO

### Process the buffer table (cron task)
TODO


## Cloud workflow (large infrastructure)

In the case of large cloud infrastructure, it might be preferable to rely on dedicated software to collect and dispatch the logs. The combination of [OpenTelemetry](https://opentelemetry.io/) and [vector](https://vector.dev/) can achieve this. OpenTelemetry not only can gather logs, but also traces and metrics. Its usefulness lies in this extended collection capacity (for purposes other than usage analytics).
This will work only on the Gateway.

Instead of configuring the logging package with a JDBC output, one can keep the standard `stdout` output for the Gateway's logs and enable OpenTelemetry feature in the Gateway.
OpenTelemetry collector, as its name suggest, collect those logs and provide them to vector, who knows how to "talk" with OpenTelemetry data. Vector then writes the results into a buffer table like in previous usecase.
A cron task (python CLI) will then retrieve the entries from this table and process_line them for storage (in the storage Hypertable in the same DB).


![workflow](../../d2/workflow_cloud.svg)

It will soon be easy to configure with the geOrchestra Helm chart. Please hold on. (TODO)

Until this is available, you still can configure it _the hard way_:
(TODO: addlinks to advanced config)

1. Configure access logs on the Gateway
2. Enable OpenTelemetry on the Gateway
3. Set up OpenTelemetry collector
4. Set up Vector
5. Set up the timescaleDB database


### Process the buffer table (cron task)
TODO


## Home-made scenario

It is easily feasible to replace those steps by your own workflow. The only strong requirement is that at the end of this processing flow, your access logs entries end up, properly formatted, in the storage Hypertable in the TimescaleDB database (see TimescaleDB for the expected formatting).
