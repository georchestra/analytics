FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sync_dashboards.py .

# Default dashboards directory — mount your .zip exports here
VOLUME ["/dashboards"]

ENTRYPOINT ["python", "sync_dashboards.py"]
