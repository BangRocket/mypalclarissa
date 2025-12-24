# Backend Dockerfile for MyPalClarissa API
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies (production only)
RUN poetry install --only main --no-interaction --no-ansi

# Copy application code
COPY *.py ./
COPY clarissa_core/ ./clarissa_core/
COPY config/ ./config/
COPY db/ ./db/
COPY sandbox/ ./sandbox/
COPY storage/ ./storage/
COPY tools/ ./tools/
COPY personalities/ ./personalities/
COPY VERSION ./

# Copy user_profile.txt if it exists (optional)
RUN mkdir -p /app/inputs && touch /app/inputs/user_profile.txt
COPY inputs/user_profile.tx[t] ./inputs/

# Create directory for persistent data (mounted as volume)
RUN mkdir -p /data
ENV DATA_DIR=/data

# Expose port (Railway sets PORT env var automatically)
EXPOSE 8000

# Health check - use PORT env var if set, otherwise 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the API - Railway sets PORT automatically
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}
