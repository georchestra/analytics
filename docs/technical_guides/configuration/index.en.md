# Configuration

Keep in mind the workflows presented in the [Presentation section](../presentation.md), it will help you understand how the components interact with each other.

You will need to follow those steps:

1. Configure Security Proxy / Gateway to produce enriched access logs exposed over OpenTelemetry protocol:
    - [Security Proxy](security_proxy.md)
    - [Gateway](gateway.md)
1. Configure the `Vector` collector to receive the logs and insert them into the database buffer table: [configuring Vector](vector.md).
1. Configure the TimescaleDB database and create the tables: [Configuring TimescaleDB](timescaledb.md).
1. Configure the CLI to process the collected access logs or to process file-based logs: [Analytics CLI](analytics-cli.md).
1. Configure your dataviz on Superset: [Configure Superset](superset.md).

If you have some trouble on the way, getting them to work, you can look at some advices in the[Troubleshooting section](../troubleshooting.md).