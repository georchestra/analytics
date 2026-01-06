# How to add a new app processor

## What are app processors?

_LogProcessors_ are the classes that implement app-specific logic when processing the logs.

They are located in `analytics-cli/src/georchestra_analytics_cli/access_logs/app_processors` and implement the
`AbstractLogProcessor` interface defined in
`analytics-cli/src/georchestra_analytics_cli/access_logs/log_processors/abstract.py`.

A generic app processor if provided, that does pretty much nothing.

Geoserver app processor extracts the Geoserver query elements mostly from the query parameters but also from the URL
path (e.g. workspace can be located in the params _or_ in the path) to provide a unified way of telling the parameters.

Datapi is a very simple app processor matching the https://github.com/georchestra/data-api project.

***This tutorial follows the implementation of the datapi app processor.***

Here are the main steps to consider:

- configure logging: make sure that the log records that you want to process are passed through the log chain. This will
  be configured at the gateway/security proxy level. If this step is working, you should see the log records arrive in
  the `analytics.opentelemetry_buffer` table in the timescaleDB base.
- implement the corresponding app processor in the CLI. When this works well, after running the CLI, the log records
  should be processed and written in the timescaleDB base, in the `analytics.access_logs` table
- configure some materialized views to exploit the data you have processed. Those are the views that will be used in
  Superset.
- configure the Superset dashboards.

## How does the CLI identify which app processor to use for a given log record ?

Available app processors are automatically discovered and lazy loaded when needed (cf log_parsers.BaseLogParser `parse`
function) based on the path of the request.

The CLI looks for the first level of the request's path (e.g. geoserver/, data/, geonetwork/, ...). By default, this
path is supposed to match the name of the corresponding processor.
But since sometimes, we choose to serve an app on an alternative path, it is possible to define a mapping, in the
configuration.

In the case of the dataapi, for instance, the standard path is `data`, the app processor's name will be `dataapi` to be
more explicit. We will have to declare the mapping in the configuration.
See [the configuration](#configure-the-mapping-path-processors-name)

## Adding an app processor for the dataapi

### Configure the logging in the gateway/security proxy

In the Gateway logging configuration log entries are filtered. So, if you don't adapt the config, it is most likely that
the log records matching your application will never reach the CLI.

See
the [configuration instructions regarding the Gateway](../../../installation/configuration/gateway.md#configuring-the-gateway-to-produce-enhanced-access-logs).

For instance, for the dataapi, you could use the following filter:

```yaml

logging:
  accesslog:
    enabled: true
    info:
      - .*/(?:ows|ogc|wms|wfs|wcs|wps)(?:/.*|\?.*)?$
      - .*/ogcapi/.*$
```

(ogcapi will match the dataapi)

Restart the gateway, and make sure that data api queries flow through the log chain: to Vector then into the DB, table
`opentelemetry_buffer`. From which the CLI will consume the records when run.

### Configure the mapping path / processor's name

in the configuration file, add the following section:

```yaml
# apps_mapping is a dict of app_path:app_name, used to determine which *software* is running for a given path.
# Apps which path match the app name don't have to be listed.
# App names have to match the name used in this project's app_processors subpackage.
apps_mapping:
  data: dataapi
```

We will add more configuration later in this tutorial.

### Implement the module

Create a python file called `analytics-cli/src/georchestra_analytics_cli/access_logs/app_processors/dataapi.py`. You
need to implement the `AbstractLogProcessor` interface. Look at the existing implementation of
[datapi processor](https://github.com/georchestra/analytics/tree/main/analytics-cli/src/georchestra_analytics_cli/access_logs/app_processors/dataapi.py).

### Add some app-specific configuration

For each app processor, the Config module can load some configuration that is specific to the app. It will look at the
`app_processors:` key. We will add a configuration block for the datapi, to rephrase the format of the downloadable
formats and match with the ones used in Geoserver:

```yaml

app_processors:
  ...
  datapi:
    download_formats:
      vector:
        # List of formats with a human-friendly label. Keys (format name) should match the WFS Getfeature supported
        # outputFormats but *in lowercase*
        shapefile: "Shapefile"
        json: "JSON"
        geojson: "GeoJSON"
        csv: "CSV"
        ooxml: "Excel"
```

### Testing your module

You should add some unit tests. In the analytics-cli/tests directory, add a test file. 

You can look at the
[datapi test](https://github.com/georchestra/analytics/tree/main/analytics-cli/tests/test_dataapi_app_processor.py) file
for inspiration.

You can run it using `tox`, or simply with `pytest tests/test_dataapi_log_processor.py`.

## Configure materialized views

Like for Geoserver, you can configure some continuous aggregates in your timescaleDB database, to improve and simplify
the exploitation of the log records matching your app. 

For instance, you could load the DDL from
https://github.com/georchestra/analytics/blob/main/config/analytics/db.entrypoints.d/102_analytics_dataapi_views.sql.

## Configure the Superset dashboards
See the Superset documentation.