FROM python:3.13-slim-trixie

# set fixed UID and GID - see github.com/hexops/dockerfile
ARG UID=10000
ARG GID=10001

RUN addgroup --gid ${GID} appgroup
RUN adduser --uid ${UID} --disabled-password --home /app --shell /bin/sh --ingroup appgroup appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sync_dashboards.py .

# Default dashboards directory — mount your .zip exports here
VOLUME ["/dashboards"]

USER appuser

ENTRYPOINT ["python", "sync_dashboards.py"]
