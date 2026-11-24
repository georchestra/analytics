#!/bin/sh

set -eu

cluster="${K3D_CLUSTER:-analytics-migrations-test}"
context="k3d-$cluster"
namespace="${K8S_NAMESPACE:-analytics-test}"
release="${HELM_RELEASE:-analytics}"
image="${ANALYTICS_CLI_IMAGE:-georchestra/analytics-cli:2.2.0}"

cleanup() {
    if [ "${KEEP_K3D_CLUSTER:-0}" != "1" ]; then
        k3d cluster delete "$cluster" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT INT TERM

for command in docker k3d kubectl helm; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "Missing required command: $command" >&2
        exit 1
    }
done

if k3d cluster list --no-headers 2>/dev/null | awk '{print $1}' | grep -Fxq "$cluster"; then
    echo "Refusing to reuse existing k3d cluster: $cluster" >&2
    exit 1
fi

docker build --target dev -t "$image" analytics-cli
k3d cluster create "$cluster" --agents 1 --no-lb --wait
k3d image import "$image" -c "$cluster"

helm upgrade --install "$release" helm/analytics \
    --kube-context "$context" \
    --namespace "$namespace" \
    --create-namespace \
    --set timescaledb.storage.size=1Gi \
    --set cli.image="$image" \
    --set cli.imagePullPolicy=Never \
    --wait --wait-for-jobs --timeout 10m

kubectl --context "$context" -n "$namespace" wait \
    --for=condition=available deployment/"$release-timescaledb" \
    deployment/"$release-vector" --timeout=5m
kubectl --context "$context" -n "$namespace" wait \
    --for=condition=complete job/"$release-db-migrate-1" --timeout=5m

run_lifecycle_job() {
    name="$1"
    action="$2"
    case "$action" in
        validate)
            cli_commands="analytics-cli legacy-ogc validate"
            ;;
        disable)
            cli_commands="analytics-cli legacy-ogc validate && analytics-cli legacy-ogc disable"
            ;;
        enable)
            cli_commands="analytics-cli legacy-ogc enable"
            ;;
        *)
            echo "Unsupported lifecycle action: $action" >&2
            exit 2
            ;;
    esac

    kubectl --context "$context" -n "$namespace" apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: $name
spec:
  backoffLimit: 2
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: lifecycle
          image: $image
          imagePullPolicy: Never
          command: ["/bin/sh", "-ec"]
          args: ["$cli_commands"]
          env:
            - name: TSDB_HOST
              valueFrom:
                secretKeyRef:
                  name: $release-timescaledb-connection-secret
                  key: host
            - name: TSDB_PORT
              valueFrom:
                secretKeyRef:
                  name: $release-timescaledb-connection-secret
                  key: port
            - name: TSDB_NAME
              valueFrom:
                secretKeyRef:
                  name: $release-timescaledb-connection-secret
                  key: dbname
            - name: TSDB_USER
              valueFrom:
                secretKeyRef:
                  name: $release-timescaledb-connection-secret
                  key: user
            - name: TSDB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: $release-timescaledb-connection-secret
                  key: password
            - name: GEORCHESTRA_ANALYTICS_CLI_CONFIG_FILE
              value: /etc/georchestra/analytics/cli.yaml
          volumeMounts:
            - name: cli-config
              subPath: cli.yaml
              mountPath: /etc/georchestra/analytics/cli.yaml
      volumes:
        - name: cli-config
          configMap:
            name: $release-cli-config
EOF
    kubectl --context "$context" -n "$namespace" wait \
        --for=condition=complete job/"$name" --timeout=5m
    kubectl --context "$context" -n "$namespace" logs job/"$name"
}

# Two successful comparisons model repeated checks during the observation window.
run_lifecycle_job legacy-observation-1 validate
run_lifecycle_job legacy-observation-2 validate
run_lifecycle_job legacy-disable disable

db_pod="$(kubectl --context "$context" -n "$namespace" get pod \
    -l app.kubernetes.io/component="$release-timescaledb" \
    -o jsonpath='{.items[0].metadata.name}')"
scheduled="$(kubectl --context "$context" -n "$namespace" exec "$db_pod" -- \
    psql -U tsdb -d analytics -Atc "
        SELECT count(*)
        FROM timescaledb_information.jobs
        WHERE hypertable_schema = 'analytics'
          AND hypertable_name LIKE 'ogc_summary_%_legacy'
          AND scheduled;")"
test "$scheduled" = "0" || {
    echo "Expected all legacy jobs to be disabled, found $scheduled scheduled" >&2
    exit 1
}

# Restore the jobs so the lifecycle test proves that disabling is reversible.
run_lifecycle_job legacy-enable enable
scheduled="$(kubectl --context "$context" -n "$namespace" exec "$db_pod" -- \
    psql -U tsdb -d analytics -Atc "
        SELECT count(*)
        FROM timescaledb_information.jobs
        WHERE hypertable_schema = 'analytics'
          AND hypertable_name LIKE 'ogc_summary_%_legacy'
          AND scheduled;")"
test "$scheduled" -gt 0 || {
    echo "Expected legacy jobs to be restored" >&2
    exit 1
}

echo "Helm migration, observation, disable and reversible enable lifecycle OK."
