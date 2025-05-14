# Analytics CLI: a utility python CLI module

CLI functions:

- analytics-cli logfile2db myfile.log: parse an access log file (archive, reverse-proxy access logs etc) and write the output in the access_logs table. Applied processes:
    - Parse the line using a regular expression (can be customized)
    - extract the common data (user, roles, org, path etc.)
    - determines the kind of application (geoserver, geonetwork etc) and apply the dedicated parsing module (if available)
    - writes it all in a temporary CSV file that is then inserted in the database table
- analytics-cli dbbuffer2db: process the rows from the buffer table (TODO: document explicitly the structure) and write the output in the access_logs table

## Processing the database buffer table

## Parsing archive file-based logs

## Extending the support for other usage data
