# External real-dump rehearsal

Real database dumps are intentionally not committed to this repository. They
may be large and may contain personal or operational data.

Use the synthetic fixtures for pull-request and CI validation. Before a release,
repeat the same sequence against a securely stored external dump:

1. restore with the source PostgreSQL and TimescaleDB versions;
2. upgrade the TimescaleDB server and extension to the supported target;
3. run `tools/database-migrations/preflight.sh`;
4. run `tools/database-migrations/migrate-existing.sh`;
5. compare counts, ranges, request totals, and compatibility views;
6. test downgrade and reapplication on the disposable copy.

Never upload customer dumps as CI artifacts or repository fixtures.
