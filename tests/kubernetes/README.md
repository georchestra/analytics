# Kubernetes migration lifecycle test

## Requirements

The local lifecycle test requires these commands to be installed and available
in `PATH`:

- Docker, with access to a running Docker daemon;
- [k3d](https://k3d.io/), used to create the disposable Kubernetes cluster;
- `kubectl`;
- Helm 3.

Check the local environment before starting:

```bash
docker version
k3d version
kubectl version --client
helm version
```

The test does not install missing dependencies automatically. If any required
command is unavailable, it stops before creating the cluster. The Docker-based
migration tests can still be executed without k3d using
`make test-migrations-all`.

Run the complete local Kubernetes validation with:

```bash
make test-helm-k3d
```

The test creates an isolated k3d cluster, builds and imports the local CLI
image, installs the Helm chart, waits for Alembic revision `0003`, performs two
legacy-versus-persistent validation cycles, disables the legacy TimescaleDB
jobs, verifies that they are no longer scheduled, and enables them again to
prove the operation is reversible.

The test never runs the destructive legacy aggregate removal command. The
cluster is deleted on exit. Set `KEEP_K3D_CLUSTER=1` to retain it for manual
inspection after a run.
