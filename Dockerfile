FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# Install the minimal runtime dependencies required by kg-api-server.py.
# Do not install the repo-wide requirements set here: it drags in heavy
# embedding / ML packages that are not needed for the API container.
RUN pip install \
    "fastapi>=0.110.0" \
    "uvicorn>=0.29.0" \
    "pydantic>=2.6.0" \
    "kuzu>=0.11.3" \
    "lancedb>=0.6.0"

# Copy backend server
COPY kg-api-server.py .

# Copy frontend interfaces
COPY src/web/ ./src/web/
COPY src/audit/ ./src/audit/
COPY src/reasoning/ ./src/reasoning/
COPY schemas/ ./schemas/
COPY design/ ./design/

# Default environment variables
ENV HOST=0.0.0.0
ENV PORT=8400
ENV DB_PATH=/app/data/finance-tax-graph
ENV LANCE_PATH=/app/data/lancedb-build

EXPOSE 8400

# Start Uvicorn
CMD ["uvicorn", "kg-api-server:app", "--host", "0.0.0.0", "--port", "8400"]
