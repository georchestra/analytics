# From 0.1.0 to 0.2.0

## Database

There have been some changes in the definition of the access_log table: new fields were added. Here's how to update it:

- Delete the depending aggregated views:

```sql
DROP
MATERIALIZED VIEW analytics.geoserver_summary_monthly CASCADE;
DROP
MATERIALIZED VIEW analytics.geoserver_summary_daily CASCADE;
DROP
MATERIALIZED VIEW analytics.geoserver_summary_hourly CASCADE;
```

- Add the new fields:

```sql
ALTER TABLE analytics.access_logs
    ADD COLUMN client_ip text;
ALTER TABLE analytics.access_logs
    ADD COLUMN server_address text;
ALTER TABLE analytics.access_logs
    ADD COLUMN app_id text;
```

- optionally set default values:

```sql
SET timescaledb.max_tuples_decompressed_per_dml_transaction TO 0;
UPDATE analytics.access_logs
SET server_address = 'your fqdn';
UPDATE analytics.access_logs
SET app_id = '/geoserver/'
WHERE app_name = 'geoserver'; 
```

- set the 'ogc' tag in jsonb `request_details` field:

```sql
UPDATE analytics.access_logs
SET request_details = jsonb_set(request_details, ARRAY['tags'], array_to_json(ARRAY['ogc'])::jsonb)
WHERE app_name IN ('geoserver', 'mapserver', 'mapproxy'); 
```

- Recreate the aggregated views: run the content of the `config/analytics/db.entrypoints.d/101_analytics_ogc_views.sql`
  file

## Dashboard

Import the dashboard provided in the `dashboards` folder. You will want to follow the import instructions, specifically
adjust the definition of the database inside the zip archive. 