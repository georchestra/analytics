# Configuring the analytics dashboard

The `dashboards` folder of this repo contains an export fo the analytics dashboard.

## Importing the dashboard

A Superset dashboard export file includes the definition for the depending items, like charts, datasets and databases.
If you properly followed the installation and configuration procedures for the Analytics stack, most of those items
should match.

_However_, the one item than might not match is the _database_ definition: the hostname of the machine serving your
timescaledb database will depend varying on the installation method, mostly.
For the dashboard to import successfully, you need to adapt the database hostname to the one used in your
infrastructure.

Since a Superset dashboard export file is basically a zipped archive, you can unzip it, manually edit the database
config and re-zip it. And import it.  
This is the recommended approach. You will at least need to update the hostname, and probably the credentials too.

Apart from the database configuration, the rest should be fine and import seamlessly.

## Using the dashboard

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

