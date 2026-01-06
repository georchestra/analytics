# Analytics CLI

Analytics CLI takes a few arguments at runtime, but most of its configuration is handled in a configuration file.

## Configuration file

The executable includes a [default config file](https://github.com/georchestra/analytics/blob/main/analytics-cli/src/georchestra_analytics_cli/config/analytics_cli.yaml).
You can provide your own config file. Its entries will be _**merged**_ with the default configuration options.
So, 

- providing an empty config file is the same as not providing one (it doesn't delete the default values)
- providing a config file with only some values will use the default values for the rest of them
- if you want to override completely the config file, make a copy of the default one and change it accordingly to your needs

The default config file is heavily commented and should be self-explanatory. We will just go over a few important features here, for the rest, please refer to the default file.

### Passing environment variables

In some cases you might want to have some values taken from environment variables. For instance to get a password, in dockerized contexts.
You can look at the `database.password` key in the default config file for an example on how to do it.

### GDPR compliance
In order to ensure GDPR compliance, by default, some personally identifiable information is removed from the process
(user id, client_ip). 
You can see the list in the default file.
This ensures that you don't inadvertently collect personal information and trespass the GDPR or similar regulations.

If you want to collect this information, you can override this list in your custom config file. 

To disable it entirely, 
set
```yaml
data_privacy
  keys_blacklist: []
```

_**Be sure to check that you are still compliant with your data privacy regulations by satisfying any of the required 
expectations.**_

## Runtime options

`analytics-cli --help` will show you the available options. As a general option, you don't have much, mostly the one to provide a custom configuration file.

The CLI relies on sub-commands:

`buffer2db`

:   Process the content of the `opentelemetry_buffer` table. When relying on the main workflow, with opentelemetry logs 
    being collected by Vector and stored in the timescaledb database, this is what you will want to run:  
    `analytics-cli --config-file /path/to/your/custom/config/file.yaml buffer2db`

`file2db`

:   Process file-based log records. For now, it only supports text logs (not json), for instance CLF-like logs.  
    Parsing is based on regular expressions. You can provide a custom regex in the config file.
    List the parameters with `analytics-cli file2db --help`

`fake2db`

:   Generate fake log records and populate the timescaleDB database with them. 
    Useful for testing purposes and when designing the dashboards.
    List the parameters with `analytics-cli fake2db --help`
