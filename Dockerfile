FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-web.txt

# Copy application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/
COPY config.py ./
COPY models/ ./models/

# Build frontend
WORKDIR /app/frontend
RUN npm ci && npm run build

WORKDIR /app

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]