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

See on the [user guide](../../../user_guide/superset_dashboard.md) for more information on how to use the dashboard.
