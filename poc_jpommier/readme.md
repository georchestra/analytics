# geOrchestra Analytics ingestion script

_Process geOrchestra http logs and feed a timescaleDB database for analytics purpose_

## Context

In 2023, members of the geOrchestra community decided to revamp the old Analytics module that did only collect OGC usage data.

During the 2023 conference then codesprints and workshops, it was decided to follow this workflow
- make Security proxy/Gateway produce access logs that would conform with classic httpd access logs (but adding user identification info)
- those logs would be processed on a regular (daily?) basis by a script that would filter them, extract some common + app-specific logic and push those usage data into a timescaleDB database
- this data could then be transformed into  beautiful _and meaningfull_ graphs using a BI tool like Apache Superset.

This codebase covers the processing script.

## Run 




## Run tests
```bash
python -m unittest
```

## Contributing

This script makes the assumption that a _log_processor_ is configured for each and every app harboured by the security-proxy/gateway. such log_processor is expected to provide some app-specific logic. The expected functions are defined in log_processors/abstract.py. An app log_processor is expected to be present in the log_processors folder, bear the app's name, and implement the abstract AbstractLogProcessor class. You can look at existing ones for inspiration and are welcome to contribute additional processors through a PR. A PR is expected to provide also unit tests for the giving log_processor.