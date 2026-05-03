FROM python:3.12-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && find /opt/venv -depth -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && find /opt/venv -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true \
    && pip uninstall -y pip setuptools wheel \
    && apt-get update \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*
FROM python:3.12-slim-bookworm AS runtime
# Quran content routes (/chapters, /verses, …) require OAuth client credentials at runtime:
#   QURAN_CLIENT_ID (or QF_CLIENT_ID) and QURAN_CLIENT_SECRET (or QF_CLIENT_SECRET)
# Optional: QF_ENV (production | prelive), QURAN_BASE_URL, QURAN_OAUTH_URL
# Phone auth: MSG91_* and USER_STORE_FILE (defaults to data/user_store.json).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .
RUN find /opt/venv -depth -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && find /opt/venv -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true \
    && adduser --disabled-password --gecos "" app \
    && mkdir -p /app/logs \
    && chown -R app:app /app
USER app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]