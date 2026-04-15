# Analytics dashboards

This folder lists Superset dashboard configurations for the usage analytics.

Please look at the 
[online documentation](https://docs.georchestra.org/analytics/en/latest/technical_guides/installation/configuration/superset/) 
for details on how to import and use it.

## Updating the dashboard

When updating the dashboard definition, it is important that the names are not timestamped (prevents automated updates, 
like it's done by the [Ansible playbook](https://github.com/georchestra/ansible/blob/master/roles/analytics/tasks/dashboard.yml)).

To ensure this:

- export the updated dashboard from Superset
- extract the archive
- rename the dashboard folder to `Usage_Statistics_dashboard`
- zip it into `Usage_Statistics_dashboard.zip` archive
- delete the previous export