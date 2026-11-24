{{/*
Expand the name of the chart.
*/}}
{{- define "analytics.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "analytics.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "analytics.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "analytics.labels" -}}
helm.sh/chart: {{ include "analytics.chart" . }}
{{ include "analytics.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "analytics.selectorLabels" -}}
app.kubernetes.io/name: {{ include "analytics.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "analytics.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "analytics.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/* Block data producers until the Alembic migration hook reaches its target. */}}
{{- define "analytics.revisionGate" -}}
{{- if and .Values.cli.enabled .Values.cli.migrations.enabled }}
initContainers:
  - name: wait-for-database-revision
    image: {{ .Values.cli.image }}
    imagePullPolicy: {{ .Values.cli.imagePullPolicy }}
    command: ["/bin/sh", "-ec"]
    args:
      - |
        until analytics-cli db require-revision --revision {{ .Values.cli.migrations.targetRevision | quote }}; do
          echo "Database migration is not ready; retrying in 2 seconds"
          sleep 2
        done
    env:
      {{- range $name, $key := dict "TSDB_HOST" "host" "TSDB_PORT" "port" "TSDB_NAME" "dbname" "TSDB_USER" "user" "TSDB_PASSWORD" "password" }}
      - name: {{ $name }}
        valueFrom:
          secretKeyRef:
            name: {{ $.Values.timescaledb.existingSecret | default (printf "%s-timescaledb-connection-secret" (include "analytics.fullname" $)) | quote }}
            key: {{ $key }}
      {{- end }}
      - name: GEORCHESTRA_ANALYTICS_CLI_CONFIG_FILE
        value: /etc/georchestra/analytics/cli.yaml
    volumeMounts:
      - name: cli-config
        subPath: cli.yaml
        mountPath: /etc/georchestra/analytics/cli.yaml
{{- end }}
{{- end }}
