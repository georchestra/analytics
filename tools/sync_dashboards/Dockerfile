FROM python:3.13-slim-trixie

# set fixed UID and GID - see github.com/hexops/dockerfile
ARG UID=10000
ARG GID=10001

RUN addgroup --gid ${GID} appgroup
RUN adduser --uid ${UID} --disabled-password --home /app --shell /bin/sh --ingroup appgroup appuser

WORKDIR /app

COPY tools/sync_dashboards/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tools/sync_dashboards/sync_dashboards.py .
COPY dashboards/superset /dashboards

USER appuser

ENTRYPOINT ["python", "sync_dashboards.py"]
