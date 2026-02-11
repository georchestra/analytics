# From 0.2.0 to 1.0.0

## Database
There shouldn't be any structural change

- Delete the depending aggregated views:

```sql
DROP MATERIALIZED VIEW analytics.ogc_summary_monthly CASCADE;
DROP MATERIALIZED VIEW analytics.ogc_summary_daily CASCADE;
DROP MATERIALIZED VIEW analytics.ogc_summary_hourly CASCADE;
```

- Recreate the aggregated views: run the content of the `config/analytics/db.entrypoints.d/101_analytics_ogc_views.sql`
  file


## Dashboard

Import the dashboard provided in the `dashboards` folder. You will want to follow the import instructions, specifically
adjust the definition of the database inside the zip archive. 