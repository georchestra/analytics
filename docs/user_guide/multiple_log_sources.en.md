# Collecting access logs from several sources

Usage analytics rely on access log data. By default, this data is collected from the geOrchestra Gateway.

The way the Gateway is configured will determine which geOrchestra apps will be monitored and accessible for the
dataviz.
This is covered in the section about
the [gateway configuration in the install doc](../technical_guides/installation/configuration/gateway.md).

But you can also collect data from other sources, external apps.

## Collect Opentelemetry data

The recommended way to do this is to configure your apps or reverse-proxy to send expose their access logs using
OpenTelemetry.

You can then configure Vector, the small software in charge of collecting the OpenTelemetry logs, to collect those
additional sources and send them to the same database table, `opentelemetry_buffer`.

## Processing the logs

If the app you are trying to add is already covered by the analytics CLI, you should be good to go. If not, you will
have to contribute some code into the analytics CLI to support this new app. This is covered in
the [Contribute section](../technical_guides/contribute/analytics-cli.md)

## Supporting apps served on other subdomains, at root path

When collecting data from external apps, some apps served at the root of a subdomain. This is quite different from the
geOrchestra core apps, where we _know_ that the first item in the path will allow us to identify the kind of software
serving it.
This introduces the need for a more subtle way of identifying which app is serving a given request.

In the CLI, the support of such external apps is supported by the combination config + a richer way to identify the
apps.
Config allows to enable the multiple domains support (`support_multiple_dn: true`). When this is set to `true`, then the
`apps_mapping` config will expect identifiers that include the domain, e.g.

```yaml
# Enable mutliple domains/external apps support
support_multiple_dn: true

# App mappings have to include the domain. And be explicit for any app we want to support, 
# including the ones that were otherwise implicitly discovered, e.g. geoserver
apps_mapping:
  "demo.georchestra.org/catalog/": "geonetwork"
  "demo.georchestra.org/geoserver/": "geoserver"
  "mapserv.georchestra.org/": "mapserver"
  "mapproxy.georchestra.org/": "mapproxy"
```

The processing of file-based logs also supports this to a certain extent. You can only process records from one app at a
time. And you have to tell which app by providing extra_info parameters, for instance
`--extra_info server_address=ms.georchestra.org --extra_info app_id=mapserver`.

When collecting OpenTelemetry data from several sources, you might want to configure Vector to add the domain
information into the Opentelemetry attributes data.