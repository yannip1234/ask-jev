FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home askjev

WORKDIR /app
COPY requirements-mcp.txt ./
RUN pip install --no-cache-dir -r requirements-mcp.txt
COPY askjev_mcp.py ./
COPY skills/askjev/scripts/askjev ./skills/askjev/scripts/askjev

USER askjev
ENTRYPOINT ["python", "/app/askjev_mcp.py"]
