FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Copy entrypoint script
COPY scripts/entrypoint.sh .
RUN chmod +x entrypoint.sh

# Set PYTHONPATH so `app` is importable
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["./entrypoint.sh"]
