# Troubleshooting

Analytics is an assembly of several components, interacting in a quite loose manner. When troubleshooting, you should be able to examine each of those components in the process chain and check, one by one, that it performs as expected.

Keep in mind the workflows presented in the [Presentation section](presentation.md), it will help you understand how the components interact with each other.

## Access logs generation

We are talking about the Gateway or the Security Proxy here.

1. First step is checking that you properly configured them to produce access logs. Look at the [configuration](configuration/index.md) section for this.

2. To see the output, you cannot really rely on the stdout logs of this component, since OpenTelemetry output is independent from the console output.  
The best way is to use an Opentelemetry collector and have it send the content to the console:

- Try to get Vector working and enable the `console` sink. Make it use the `opentelemetry.logs` input. 
- For now, you can disable the `database` sink. 
- Restart Vector (to reload the config) and watch vector's console output (`tail -f` or `docker ... -f`). You should see the OpenTelemetry data flowing on your console. If not, then your Gateway/SP doesn't send properly their opentelemetry logs to Vector.
- When you get it to work, change the sink's input to your access log filter (e.g. `access_logs_filter`) instead of `opentelemetry.logs`. Restart Vector, whatch for a change. It should show only the logs matching the filter.

## Writing them to the DB

You of course need :

- Access logs to flow into Vector
- A timescaleDB database running, with the `opentelemetry_buffer` table already created
- Vector service running and collecting the access logs (see above).

If the `opentelemetry_buffer` table stays empty:

- If not enabled, enable on Vector's config the `database` sink. Adapt the connection parameters if necessary.
- Restart Vector (to reload the config).
- Check Vector's logs for any error that could hint about, for instance, a wrong database connection config.
- If it still doesn't work, did you check that the access logs do arrive up to Vector ? (see section above)

## CLI: processing the opentelemetry buffer data

The CLI processes the data from the `opentelemetry_buffer` table and feeds the processed records in `access_logs` table.

The CLI needs to run at a regular basis (it is not automatic _per-se_): you need to configure it as a CRON-like task. First make sure that it is indeed running regularly.

Since it is a cron-like task, the `access_logs` table will only be updated on those occasions.

If it doesn't, check the CLI logs for hints about what can cause errors.

## CLI: writing file-based access logs to the DB

When processing file-based access logs, the CLI doesn't use the buffer table, it is specific to Opentelemetry workflow.

The CLI writes directly the data into the `access_logs` table. 

If it stays empty, watch the CLI's logs, there is probably an error somewhere. 