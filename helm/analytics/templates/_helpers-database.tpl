{{/*
Insert database timescaledb environment variables
*/}}
{{- define "analytics.timescaledb-envs" -}}
{{- $database := .Values.timescaledb -}}
{{- $analytics_timescaled_secret_name := printf "%s-analytics-timescaledb-secret" (include "analytics.fullname" .) -}}
{{- if $database.builtin }}
- name: PGHOST
  value: "{{ .Release.Name }}-database"
{{- else }}
{{- if $database.auth.existingSecret }}
{{- $analytics_timescaled_secret_name = $database.auth.existingSecret -}}
{{- end }}
- name: PGHOST
  valueFrom:
    secretKeyRef:
        name: {{ $analytics_timescaled_secret_name }}
        key: host
        optional: false
{{- end }}
- name: PGPORT
  valueFrom:
    secretKeyRef:
        name: {{ $analytics_timescaled_secret_name }}
        key: port
        optional: false
- name: PGDATABASE
  valueFrom:
    secretKeyRef:
        name: {{ $analytics_timescaled_secret_name }}
        key: dbname
        optional: false
- name: PGUSER
  valueFrom:
    secretKeyRef:
        name: {{ $analytics_timescaled_secret_name }}
        key: user
        optional: false
- name: PGPASSWORD
  valueFrom:
    secretKeyRef:
        name: {{ $analytics_timescaled_secret_name }}
        key: password
        optional: false
{{- end }}