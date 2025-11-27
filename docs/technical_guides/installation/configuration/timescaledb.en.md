# Configuring TimescaleDB

## TimescaleDB basic configuration

Like any PostgreSQL, there is quite a lot you can configure: pg_hba.conf, number of simultaneous connections, global
tuning. Proceed for that as you would for any PostgreSQL database.  
Additionally, you might want to read:

- [Timescaledb install](https://docs.timescale.com/self-hosted/latest/install/)
- [Timescaledb config](https://docs.timescale.com/self-hosted/latest/configuration/timescaledb-config/)

## Configure for geOrchestra Analytics

For Analytics, we need some (hyper)tables to be present as well as some continuous aggregates based on them. In a
nutshell, a hypertable is a new table type introduced by timescale-BD, optimized to handle massive time-stamped data.
Continuous aggregates are a feature of timescale-BD, that allows to compute aggregates on a regular basis, based on
the data stored in a hypertable.

We provide only some aggregates, but feel free to add your own.

About the retention policies applied on the tables, the compression etc, we can only propose some settings, but you
might want to adapt them to your needs and expectations.

!!! warning "Warning"

    The timzone you are in will be of great importance for the continuous aggregates. Make sure you read the [Configuring your timezone](#timezone) chapter.

### Tables

#### `opentelemetry_buffer` table

This is the table that Vector will write to. It receives the Opentelemetry access log data, without any more process.

It will be used as the source for the Python CLI when processing the access logs.

You need at least the `opentelemetry_buffer` table to be present, so that Vector can write to it. The python CLI should
be able to create it on the fly at its first run, but for now it is missing some performance optimization like having
the table set as `unlogged`.

The analytics git repository provides you with a creation script to run against your database:
[analytics.opentelemetry_buffer creation script](https://github.com/georchestra/analytics/blob/main/config/analytics/db.entrypoints.d/100_analytics_init.sql#L3)

If you looks at the structure, you will notice that it matches with the structure of access logs provided by
OpenTelemetry standard. This is the
structure that the Python CLI will expect to get as input. Please don't mess with this structure.
If you need to add more data, please place them into one of the json objects, for instance `attributes` or `scope`.

#### `access_logs` table

The `analytics.access_logs` table is fed by the python CLI. For now, the CLI doesn't create it if not present, so you'll
have to create it manually on the DB _before_ running the CLI for the first time.
Here the creation script:

[analytics.access_logs creation script](https://github.com/georchestra/analytics/blob/main/config/analytics/db.entrypoints.d/100_analytics_init.sql#L21)

Please note that this table is a TimescaleDB _hypertable_, i.e. optimized for massive time-scaled data. To know more
about this, see [hypertables](https://docs.timescale.com/use-timescale/latest/hypertables/).

`request_details` is a jsonb object, this will, as a base, contain all the request parameters. This is also where the
app-specific processors of the CLI will add any interesting information it can extract (based on each app
vendor-specific logic).

!!! note "Note"

    Be mindful if adding json(b) objects inside this `request_details` jsonb object, because it might then be 
    complicated to process when creating the continous aggregates: TimescaleDB doesn't, as of now, support 
    sub-queries in the definition of the continuous aggregates.

## Loading the default table definitions

### Configuring your timezone

The default tables definitions are configured for the French metropolitan timezone (`Europe/Paris`). If you are not in
this timezone, you will have to adapt the `time_bucket` function used in the continuous aggregates.

#### Why is that ?

TimescaleDB is an extension of PostgreSQL that helps you handle very large time-scaled data. One of the ways it does
that is by offering you the possibility to define what they call continuous aggregates. In a nutshell, they are
materialized views over your big hypertables, that aggregates the records into temporal "buckets": 1-hour bucket, 1-day
bucket, 1-month bucket etc.

At me monthly scale, timezone won't matter much, but at the daily scale, supposing your are on UTC+6 for instance, it
will have a huge impact: actions logged on a given day might very well appear in the bucket of the previous day. Which
will mess up your analytics.

With hourly buckets, it might be even worse: your pike of activity at 18:00 will actually be stored in the noon bucket.
Well, you see the picture.

#### How to configure it properly ?

Luckily for us, timescaleDB handles this scenario with a
[built-in feature](https://www.tigerdata.com/blog/nightmares-of-time-zone-downsampling-why-im-excited-about-the-new-time_bucket-capabilities-in-timescaledb).
We just have to configure it right.

In the aggregates' definition, if you look for the views, you will see `time_bucket()` calls, in the form of
`time_bucket(INTERVAL '1 d', bucket, 'Europe/Paris')`. The third argument should be your timezone. If necessary, change
all the occurrences of `Europe/Paris` in this file before loading it in the DB

### On docker

For now, We haven't yet managed to load them by default on startup. You will have to load them manually once you started
the docker compo:

```bash
# Set your timezone if not metropolitan France
#my_tz='Antarctica/Troll'
#sed -i "s|Europe/Paris|$my_tz|g" config/analytics/db.entrypoints.d/*.sql

# Then load the definitions into the DB
for f in `ls -1 config/analytics/db.entrypoints.d/*.sql`; do 
  docker compose exec -T timescaledb psql -U tsdb -d analytics < $f
done
```

## Performance

Cf [https://docs.timescale.com/self-hosted/latest/configuration/timescaledb-config/](https://docs.timescale.com/self-hosted/latest/configuration/timescaledb-config/)

### Opentelemetry_buffer table

Having the table set as `unlogged` provides a better performance, at the cost of loosing its data in case of a database
crash. Since this is just analytics concern, it can be considered a reasonable compromise to ensure better performance.
But feel free to remove this feature if you prefer.
