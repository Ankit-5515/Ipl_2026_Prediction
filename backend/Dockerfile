FROM python:3.11-slim

WORKDIR /app

# Install system build dependencies for psycopg2 / xgboost
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy dataset, ML package, and backend source
COPY IPL.csv ./IPL.csv
COPY ml ./ml
COPY backend ./backend

# Train artifact if not already present
RUN python -m ml.train

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
