# ── Frontend image ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Standard Python Docker best practices.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Default API URL — overridden by compose environment block.
ENV API_URL=http://backend:8000

WORKDIR /app

# Install Poetry and configure it to install into the system Python.
RUN pip install --no-cache-dir "poetry>=1.8,<2" && \
    poetry config virtualenvs.create false

# Copy only the dependency manifest first for layer caching.
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-interaction --no-ansi

# Copy application source.
COPY . .

EXPOSE 8501

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" \
    || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
