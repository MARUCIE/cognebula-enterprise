FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# Install system dependencies for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install fastapi uvicorn kuzu lancedb pydantic numpy

# Copy backend server
COPY kg-api-server.py .

# Copy frontend interfaces
COPY src/web/ ./src/web/
COPY design/ ./design/

# Default environment variables
ENV HOST=0.0.0.0
ENV PORT=8400
ENV DB_PATH=/app/data/finance-tax-graph
ENV LANCE_PATH=/app/data/lancedb-build

EXPOSE 8400

# Start Uvicorn
CMD ["uvicorn", "kg-api-server:app", "--host", "0.0.0.0", "--port", "8400"]
