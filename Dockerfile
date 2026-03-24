FROM python:3.12-slim

WORKDIR /app

# Narzędzia sieciowe potrzebne do diagnostyki
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    traceroute \
    dnsutils \
    curl \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Zależności Python
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    anthropic \
    sqlmodel \
    dnspython \
    python-whois \
    httpx \
    psutil \
    pydantic-settings \
    pyyaml \
    python-dotenv \
    apscheduler \
    rich \
    typer \
    websockets

# Kod aplikacji
COPY cli_troubleshooter/ cli_troubleshooter/
COPY run_dashboard.py .

# Katalog na bazę danych (montowany jako volume)
RUN mkdir -p data

EXPOSE 8080

# Uruchom jako non-root (z wyjątkiem ping który wymaga NET_RAW)
# NET_RAW jest nadawany przez docker-compose

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

CMD ["python", "run_dashboard.py", "--host", "0.0.0.0", "--port", "8080"]
