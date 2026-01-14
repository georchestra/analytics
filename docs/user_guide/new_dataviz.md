# Customizing the dashboard

If you have sufficient rights, you can customize the dashboard. You can change the graphs, add new ones etc.

Beware that we are likely to provide updates of this dashboard in the future, and customizing it might complicate
further updating the dashboard. We would rather advise that you create a separate dashboard for your custom dataviz.

Creating dashboards and graphs is a Superset-related matter. Please refer to the corresponding doc.

## Database tables

!!! warning "`access_logs` table"

    If you plan on creating new graphs, you will have access to the same underlying data. We advise _against_ using the raw
    `access_logs` table, for the following reasons:
    
    - it is not aggregated nor optimized and will, in time, contain _a lot_ of data. Superset will have a hard time
      compiling the requested data, it might represent big queries that can get slow and demanding on the database.
    - its content will be trimmed after a while. By default, the retention time for this table is 3 years. Data that is
      older than that will be deleted from this table, and will only be available as aggregated data in the monthly views.
      This might sound like a bad idea, but is a necessary compromise when dealing with huge datasets.

Instead, _**we recommend that you use the aggregated views**_, for instance the ogc_summary_* views. They provide hourly,
daily and monthly aggregations, with each their retention time. The reason behind it being to provide accurate data on
short term, keep old-term data at lesser resolution and keep the whole reasonably small for storage.

Depending on the time scale you look for, you will use hourly view, daily view, monthly view.

If the provided views do not cover your needs, you can [create additional views](./aggregated_views.md). Please consider
sharing them with the community if you think it can be of common use.

