FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Support build context being either repo root or scraper/ directory
COPY requirements.txt scraper/requirements.tx[t] ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; \
    elif [ -f scraper/requirements.txt ]; then pip install --no-cache-dir -r scraper/requirements.txt; fi

COPY . .

# If built with repo root as context, move scraper/* contents to /app
RUN if [ -d "scraper/app" ]; then cp -r scraper/* . && rm -rf scraper; fi

# Run Alembic migrations and start Web server binding to dynamic $PORT
CMD ["sh", "-c", "alembic upgrade head || true && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
