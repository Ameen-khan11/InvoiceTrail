FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code and certs
COPY backend/ .
COPY certs/ ./certs/

# Expose port (Render sets PORT env var)
ENV PORT=10000
EXPOSE 10000

CMD ["sh", "-c", "gunicorn --workers=2 --bind=0.0.0.0:$PORT --timeout=120 run:app"]
