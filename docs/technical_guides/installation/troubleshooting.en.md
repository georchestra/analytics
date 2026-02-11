# Troubleshooting

Analytics is an assembly of several components, interacting in a quite loose manner. When troubleshooting, you should be
able to examine each of those components in the process chain and check, one by one, that it performs as expected.

Keep in mind the workflows presented in the [Presentation section](presentation.md), it will help you understand how the
components interact with each other.

## Access logs generation

We are talking about the Gateway or the Security Proxy here.

1. First step is checking that you properly configured them to produce access logs. Look at
   the [configuration](configuration/index.md) section for this.

2. To see the output, you cannot really rely on the stdout logs of this component, since OpenTelemetry output is
   independent from the console output.  
   The best way is to use an Opentelemetry collector and have it send the content to the console:

- Try to get Vector working and enable the `console` sink. Make it use the `opentelemetry.logs` input.
- For now, you can disable the `database` sink.
- Restart Vector (to reload the config) and watch vector's console output (`tail -f` or `docker ... -f`). You should see
  the OpenTelemetry data flowing on your console. If not, then your Gateway/SP doesn't send properly their opentelemetry
  logs to Vector.
- When you get it to work, change the sink's input to your access log filter (e.g. `access_logs_filter`) instead of
  `opentelemetry.logs`. Restart Vector, whatch for a change. It should show only the logs matching the filter.

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

The CLI needs to run at a regular basis (it is not automatic _per-se_): you need to configure it as a CRON-like task.
First make sure that it is indeed running regularly.

Since it is a cron-like task, the `access_logs` table will only be updated on those occasions.

If it doesn't, check the CLI logs for hints about what can cause errors.

## CLI: writing file-based access logs to the DB

When processing file-based access logs, the CLI doesn't use the buffer table, it is specific to Opentelemetry workflow.

The CLI writes directly the data into the `access_logs` table.

If it stays empty, watch the CLI's logs, there is probably an error somewhere.

## The dashboards don't show the latest data

The graphs based on the hourly dataset should be encompassing the data from the last _finished_ hour (completed hour).
However, between the timezone settings on each step and the "automated" data aggregations in timescaledb, glitches can
occur one place or the other.

If you are in that situation where things don't look right, here is what you should check:

- First thing to check is the refresh state in the Superset dashboard. Dashboards don't necessarily update frequently.
  It can be that your dashboard is simply being cached by Superset. Try the buttons on the top right corner and select "
  Update Dashboard". Your can also set the desired refresh frequency.
- Timezone: we did our best for the processes to be timezone-aware. Your log records should be timezone-aware too. If
  not, there might be some mixup. Check in the DB, in the `access_logs` table, that the times were not altered during
  import.
- It the data seems up to date in the `access_logs` table, check that the `ogc_summary_hourly` table too looks up to
  date. Since this is aggregated data, it might be a bit challenging to compare with the source `access_logs` table, but
  by calling a few specific layers for instance, you should be able to track this.
  If it is not up-to-date, it is possible that the aggregates' refresh happens _before_ the CLI commited the new
  records, hence postponing the update for one hour. At some point the refresh will be called just after the CLI call,
  but for now, you will want to change the time at which the materialized views are updated. This is configured in the
  DB, in the `add_continuous_aggregate_policy`  sections.
- If everything looks good on the database side, then you will want to check on the Superset side.
    - Dashboards don't necessarily update frequently. It can be that your dashboard is simply being cached by Superset.
      Try the buttons on the top right corner and select "Update Dashboard".
    - If this is still not good, it is possible that your time settings in Superset are not correct.

## Checking timescaledb's continuous aggregates configuration

### Continuous aggregates refresh schedule

You can run the following query:

```sql
SELECT j.hypertable_name,
       j.job_id,
       config,
       schedule_interval,
       job_status,
       last_run_status,
       last_run_started_at,
       js.next_start,
       total_runs,
       total_successes,
       total_failures
FROM timescaledb_information.jobs j
         JOIN timescaledb_information.job_stats js
              ON j.job_id = js.job_id
WHERE j.proc_name = 'policy_refresh_continuous_aggregate';
```

### Continuous aggregates retention policy

You can run the following query:

```sql
SELECT j.hypertable_name,
       j.job_id,
       config,
       schedule_interval,
       job_status,
       last_run_status,
       last_run_started_at,
       js.next_start,
       total_runs,
       total_successes,
       total_failures
FROM timescaledb_information.jobs j
         JOIN timescaledb_information.job_stats js
              ON j.job_id = js.job_id
WHERE j.proc_name = 'policy_retention';
```

ref. https://www.tigerdata.com/docs/use-timescale/latest/data-retention/create-a-retention-policy#see-scheduled-data-retention-jobs

## Missing some attributes

Some attributes may not be present in the logs shipped through OpenTelemetry.

### Header information (User-Agent, Referer)

Check that the Gateway is properly configured to send these headers. Refs:

- https://docs.georchestra.org/analytics/en/latest/technical_guides/installation/configuration/gateway/#enabling-enhanced-access-logs
- https://docs.georchestra.org/gateway/en/latest/user_guide/logging/

The Referer information might also be very limited, or even missing anyhow. This will depend highly on the configuration
of all the intermediate proxies : your main reverse-proxy, the Gateway etc.
For instance, on the Gateway, you might want to check the `spring.cloud.gateway.filter.secure-headers.referrer-policy`
configuration parameter, usually defined
in [Gateway's application.yaml](https://github.com/georchestra/datadir/blob/master/gateway/application.yaml).
[Depending on the value set for that param](https://developer.mozilla.org/fr/docs/Web/HTTP/Reference/Headers/Referrer-Policy),
the content of the Referer header will vary.
The default value on the geOrchestra datadirs is `strict-origin` which will limit the transmitted information to the
domain. You might want to set it to `strict-origin-when-cross-origin` to get more detailed information at least when on
the same domain.
