# Creating additional DB aggregated views

Aggregated views are a TimescaleDB feature. Their reason to exist is to provide a means to query data from a table that
is quickly an ever-increasing over time. At some point, the source table gets bloated and the database unresponsive.
Aggregated views are a part of TimescaleDB's response to this challenge. To read more about it, please fetch
the [TigerData documentation](https://www.tigerdata.com/docs/use-timescale/latest/continuous-aggregates).

## Creating an aggregated view
First, you need a write access to the DB.

Then, you should read the [official documentation](https://www.tigerdata.com/docs/use-timescale/latest/continuous-aggregates) to know more about it.

At last, you can get inspired by the OGC_summary views, their DDL can be found on the 
[project's repository](https://github.com/georchestra/analytics/blob/main/config/analytics/db.entrypoints.d/101_analytics_ogc_views.sql).

Some things that you need to consider when creating an aggregated view:

- the time bucket grain
- the timezone to use on the time bucket. Depending on the time resolution, it might be of importance or not. A few-hours shift might go unnoticed on monthly aggregates. On hourly aggregates it should even be unrelevant. On daily aggregates though, it might be of importance, whether this activity peak happened early in the morning or, maybe, late in the evening the previous day.
- compression, if enabled, should improve storage, specially on long-term aggregates
- continuous aggregate policy determines which frequency the view wil be updated at, and the period of time covered for the refresh.

