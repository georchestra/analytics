# Analytics CLI

The analytics CLI is python code. One of the reasons behind the choice of python is to try to stay accessible to most 
code-aware people.

There are good reasons you might want to contribute the code (it's always a good reason anyway, but still). For 
instance, you want the CLI to be able to process log records from an app that is not yet supported. This page will try 
to get you on the right track.

If you're still having trouble figuring your way, please reach out, either by the github issues system or on 
[geOrchestra community channels](https://www.georchestra.org/community.html).

The code is located in the [analytics](https://github.com/georchestra/analytics/) repo, in the `analytics-cli` folder.

## Setup a development environment

cf https://github.com/georchestra/analytics/blob/main/analytics-cli/README.md

## CLI's entrypoint

The entrypoint is the [`__main__.py`](https://github.com/georchestra/analytics/blob/main/analytics-cli/src/georchestra_analytics_cli/__main__.py).
It uses the `click` library to handle the interactions with the user.

Depending on the command that was called, the [`AccessLogProcessor`](https://github.com/georchestra/analytics/blob/main/analytics-cli/src/georchestra_analytics_cli/access_logs/AccessLogProcessor.py)
module will rely on one of the [log_parsers](https://github.com/georchestra/analytics/tree/main/analytics-cli/src/georchestra_analytics_cli/access_logs/log_parsers) modules.

## Log parsers 
cf. [log_parsers](https://github.com/georchestra/analytics/tree/main/analytics-cli/src/georchestra_analytics_cli/access_logs/log_parsers)

Each of them implement the `BaseLogParser` class or at least the `AbstractLogParser` class.

The log parser loads its corresponding configuration from the config file. It then parses the log records, being on the timescaledb table, from a log file, or to generate fake ones.
For each log record, it tries to identify which app is behind this record. This is done in the [`_get_app_processor`](https://github.com/georchestra/analytics/blob/main/analytics-cli/src/georchestra_analytics_cli/access_logs/log_parsers/BaseLogParser.py#L29) 
function and is probably the trickiest part. 

On most cases, the app name is given by the first word in the path of the logged request. For instance, the path 
`/geoserver/admin/wms` will be explicit enough to tell this is the Geoserver app. In that case, the function above will load the eponym 
module in [app_processors](https://github.com/georchestra/analytics/tree/main/analytics-cli/src/georchestra_analytics_cli/access_logs/app_processors)
if present. It will look for the lower-cased name, so `geoserver.py` in this case.

In some cases, the app name does not match the path. For instance, the dataapi is served under `/data`. In this case, 
the correspondence needs to be explicitly provided in the config file, in the `apps_mapping` section:
```yaml
apps_mapping:
  "/data/": dataapi
```

In the geoserver case, the mapping is implicit. In the second case, it is explicit.

There is another possible situation, where collecting log records from apps served _outside_ of geOrchestra and at the 
root path. For instance a mapserver instance, served on a given subdomain, at the root of the server (let's say for the 
sake of this discussion at https://ms.georchestra.org/).
In this situation, there is no way to guess which app this might be. To support this, we need to

- enable the multidomains support for tha apps_mapping: `support_multiple_dn: true`. When activated, the mapping expects the domain to prefix the app path. A painful consequence is that any implicit mapping will be disabled and all mappings will have to be explicitly declared in the config.
- declare the mappings in the config:
```yaml
support_multiple_dn: true

apps_mapping:
  "demo.georchestra.org/geoserver/": geoserver
  "demo.georchestra.org/data/": dataapi
  "ms.georchestra.org/": mapserver
```

## App processors

For now, apart from the dataapi app processor, all the implementations are about OGC records. `geoserver`, `mapserver`,
`mapproxy` rely on the more generic `ogcserver` module and implement specific features for each of their respective 
software.

You can look at the dataapi processor for a very simple use-case. 
[A tutorial covers its implementation](./tutorials/add_a_new_app_processor/).

The app processors add an extra-level of parsing to extract the app-specific information. This information is ultimately 
stored in the `request_details` field.

### Implementing a new app processor

You can have a look at the tutorial: [dataapi tutorial](./tutorials/add_a_new_app_processor/).

You can also have a look at how the OGC apps are covered.

All app processors have to implement the abstract.py module. 

The file name needs to be lowercase, so that it can be properly detected. And if necessary, an `app_mapping` entry 
needs to provide the mapping between the path and the module's name. Then, it should be recognized automatically when 
matching log records are met.

For now, the code still needs to be included/compiled in the analytics-cli package. There is no plugin support as of now.

