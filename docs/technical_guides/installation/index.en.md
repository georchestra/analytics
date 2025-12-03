# Table of Contents

Installing the analytics component is as much configuration as installation.
This section will cover an "off the shelf" installation, that should allow you to quickly gather analytics data.

But for better control on what you collect and what you can make out of it, please follow on by reading carefully the
configuration section.

There are 3 distinct steps in setting up the analytics "module":

- Configure your Security Proxy/Gateway to generate access logs and ship them to the storage database using
  OpenTelemetry standard
- Configure the analytics database for optimal performance over time
- Load dashboards on Apache Superset and possibly create new ones


