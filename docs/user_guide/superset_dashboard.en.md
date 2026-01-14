# Usage analytics dashboard on Apache Superset

A default dashboard is provided. It features some charts around OGC usage.

![Dashboard screenshot](../images/ogcstats.png)

## Using the default dashboard

For now, it only covers OGC services. More tabs might be added over time.

In the OGC services tab, there are two subtabs: `Currently` and `Daily data`. They look very similar.
Actually, this is the idea. But since they rely on different datasets, they have to be separate.

### 'Currently'

In this tab, you can view recent usage, by the hour.

The `Currently` tab relies on the hourly data extracted from the access logs. The time grain is the hour. It covers the
time extent configured in your timescaleDB views. By default it is 3 weeks. Data that are older than that are deleted
and you can only access them as daily aggregated data.

Several graphs provide dynamic filtering: if you click on an organization for instance, it will activate a filter on the
other graphs, limiting their underlying dataset to the ones concerning this organization.

There is also a time filter. On the left panel, you can change the timeframe of the graphs.

### 'Daily data'

In this tab, you can view longer-term usage, by the day.

The `Daily data` tab provides the same graphs, but based on the daily aggregation view. The time grain is the day. It
covers the
time extent configured in your timescaleDB views. By default it is 2 years. Data that are older than that are deleted
and you can only access them as monthly aggregated data.

The graphs provide the same dynamic filtering as explained above.

There is also a time filter. On the left panel, you can change the timeframe of the graphs. This is a different filter
than for the `Currently` tab, since it applies on a different dataset. The left panel will tell you which filter is in
range (appropriate).

## Customizing the dashboard
If the provided graphs are not enough, you can go [for a custom dataviz](./new_dataviz.md).
