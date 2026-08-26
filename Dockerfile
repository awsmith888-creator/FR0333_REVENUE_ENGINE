FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV GITHUB_WEBHOOK_DB=/var/lib/fr0333/github-webhook.sqlite3
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY camera_package.py .
COPY facebook_bridge.py .
COPY github_bridge.py .

RUN addgroup --system fr0333 \
    && adduser --system --ingroup fr0333 fr0333 \
    && mkdir -p /var/lib/fr0333 \
    && chown fr0333:fr0333 /var/lib/fr0333

USER fr0333
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3).read()"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
