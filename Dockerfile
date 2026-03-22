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
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]