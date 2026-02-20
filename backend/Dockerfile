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
        fontconfig \
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

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
