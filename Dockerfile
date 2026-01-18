# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Create directories for SQLite databases if they don't exist
RUN mkdir -p omniflow/db/shipstream omniflow/db/shopcore omniflow/db/caredesk omniflow/db/payguard

# Run database migrations and seed data
RUN python omniflow/manage.py migrate --database=default && \
    python omniflow/manage.py migrate --database=shopcore && \
    python omniflow/manage.py migrate --database=shipstream && \
    python omniflow/manage.py migrate --database=payguard && \
    python omniflow/manage.py migrate --database=caredesk && \
    python omniflow/manage.py seed_from_input_data && \
    python omniflow/manage.py seed_demo_complex_query

# Expose the port the app runs on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["python", "omniflow/manage.py", "runserver", "0.0.0.0:8000"]
