# Expressions régulières

Here the patterns to use in regular expressions to extract informations from a line log. Depends on the source of the log.


## security-proxy

### Generalities

The ISO date + time of the access : `^(\b\d{4}-\d{2}-\d{2})\ (\d{2}:\d{2}:\d{2}\b)`. Group 1 = date, group 2 = time.


### identity and georchestra roles

The user login : group 1 of `\[INFO\]\ (.*)\|[0-9]`.

The user organism : group 1 of `\|(![0-9]|!http|[a-zA-Z_]*)\|(.*)`.

The list of the geOrchestra roles : group 2 of `\|(![0-9]|!http|[a-zA-Z_]*)\|(.*)`


### GeoServer




## gateway

