# ── Backend image ──────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Standard Python Docker best practices.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Default config — overridden at runtime by backend/.env or compose environment.
ENV LLM_PROVIDER=ollama \
    LLM_MODEL=llama3.2 \
    OLLAMA_BASE_URL=http://ollama:11434 \
    OPENAI_API_KEY=""

# WeasyPrint requires several Pango/Cairo/GDK system libraries for PDF rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libcairo2 \
        libglib2.0-0 \
        libharfbuzz0b \
        shared-mime-info \
        fonts-liberation \
        fonts-noto-core \
        fontconfig \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry and configure it to install into the system Python
# (no virtualenv inside Docker — the container IS the isolation boundary).
RUN pip install --no-cache-dir "poetry>=1.8,<2" && \
    poetry config virtualenvs.create false

# Copy only the dependency manifest first so this layer is cached until
# pyproject.toml or poetry.lock changes.
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-interaction --no-ansi

# Copy application source (invalidates cache on code changes only).
COPY . .

# Bake static data (i18n bundles, normative tables) into a separate image
# path so the entrypoint can sync them into the volume-mounted /app/data on
# every start.  This keeps translations and norms up-to-date after rebuilds
# without wiping runtime data (fitness.db, clients.json, coaches.json).
RUN mkdir -p /app/seed_data && \
    cp -r /app/data/i18n /app/seed_data/i18n && \
    cp -r /app/data/norms /app/seed_data/norms

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
