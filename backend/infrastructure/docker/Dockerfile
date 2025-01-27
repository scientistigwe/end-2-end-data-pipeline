# Backend Dockerfile
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user
<<<<<<< HEAD
RUN useradd -m appuser && chown -R appuser:appuser /flask_app
=======
RUN useradd -m appuser && chown -R appuser:appuser /app
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
USER appuser

# Run the application
CMD ["gunicorn", "backend.wsgi:application", "--bind", "0.0.0.0:8000"]

---
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - static_files:/app/static
      - media_files:/app/uploads
    env_file: .env
    depends_on:
      - postgres
      - redis
      - celery
    environment:
      - DATABASE_URL=postgresql://analyst_user:secure_password@postgres:5432/analyst_pa
      - REDIS_URL=redis://redis:6379/0
      - PROMETHEUS_MULTIPROC_DIR=/tmp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A backend worker -l INFO
    volumes:
      - ./backend:/app
    depends_on:
      - redis
      - postgres
    env_file: .env
    environment:
      - DATABASE_URL=postgresql://analyst_user:secure_password@postgres:5432/analyst_pa
      - REDIS_URL=redis://redis:6379/0

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A backend beat -l INFO
    volumes:
      - ./backend:/app
    depends_on:
      - redis
      - celery
    env_file: .env

  postgres:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=analyst_pa
      - POSTGRES_USER=analyst_user
      - POSTGRES_PASSWORD=secure_password
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U analyst_user -d analyst_pa"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./infrastructure/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    depends_on:
      - prometheus
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_grafana_password
      - GF_USERS_ALLOW_SIGN_UP=false

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
  static_files:
  media_files: