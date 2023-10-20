# geOrchestra Analytics ingestion script

_Process geOrchestra http logs and feed a postgresql/timescaleDB database for analytics purpose_

## Context

In 2023, members of the geOrchestra community decided to revamp the old Analytics module that did only collect OGC usage data.

During the 2023 conference then codesprints and workshops, it was decided to follow this workflow
- make Security proxy/Gateway produce access logs that would conform with classic httpd access logs (but adding user identification info)
- those logs would be processed on a regular (daily?) basis by a script that would filter them, extract some common + app-specific logic and push those usage data into a timescaleDB database
- this data could then be transformed into  beautiful _and meaningfull_ graphs using a BI tool like Apache Superset.

This codebase covers the processing script.

## Run 

### Get prepared

**Requirements**: this package uses functions that were introduced in python 3.11. You will need python 3.11 or later 
to run them.

Create a virtualenv and install dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Process logs

Process log data matching the default logformat:
```bash
python cli.py process-logs sample_data/sp_sample_gs_logs.log
# We don't provide database connection info, so it will stop at writing a CSV file. The path will be displayed by the script
```

Process log data matching the default logformat:
```bash
python cli.py process-logs \
    --log_format "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" %{counter}n \"%{app}n\" \"%{host}n\" %{ms}Tms" \
    sample_data/traefik_georhena_sample_logs.log
```

Process log data and push it into a DB table:
```bash
# You can start a simple postgresql DB by running:
docker compose -p georchestra_dev_analytics -f ./db/docker-compose.yml up -d

python cli.py process-logs \
    --log_format "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" %{counter}n \"%{app}n\" \"%{host}n\" %{ms}Tms" \
    --pghost localhost --pgport 55432 --pgname georchestra \
    --pguser georchestra --pgpassword georchestra \
    --pgtable analytics.logs \
    sample_data/traefik_georhena_sample_logs.log

python cli.py process-logs \
    --log_format "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\" %{counter}n \"%{app}n\" \"%{host}n\" %{ms}Tms" \
    --pghost localhost --pgport 55432 --pgname georchestra \
    --pguser georchestra --pgpassword georchestra \
    --pgtable analytics.logs \
    /home/jean/fast/dev/geOrchestra/analytics-experiments/docker/logs/traefik/access.log
  
   
```

## Run tests
```bash
python -m unittest
```

## Contributing
 
At this stage, this is more a _proof-of-concept than anything else. Contributions and ideas are welcome, feel free to fill an issue or provide a pull-request.

### Adding app-specific log processors

This script makes the assumption that a _log_processor_ is configured for each and every app harboured by the security-proxy/gateway.

Such log_processor is expected to provide some app-specific logic. The expected functions are defined in log_processors/abstract.py. An app log_processor is expected to be present in the log_processors folder, bear the app's name, and implement the abstract AbstractLogProcessor class. You can look at existing ones for inspiration and are welcome to contribute additional processors through a PR. A PR is expected to provide also unit tests for the giving log_processor.

### Ideas for future improvements

- add other app-specific log processors (_including the geonetwork one, which is here just for illustration_)
- add a config file to define 
  - the log format, 
  - the correspondance between the app name in the url path and the log processor module to use, 
  - the patterns to use for the _is_relevant_ function
- monitor and optimize performance
- see if we couldn't get the logs from streaming source and publish on-the-go
- _other ideas ?_ Please fill an issue