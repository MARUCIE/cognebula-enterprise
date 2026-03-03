FROM python:3.11-slim

# CogNebula SOTA Enterprise Deployment
# Includes KuzuDB, LanceDB (Vector), Redis bindings, and Tree-sitter (WASM/Bindings)

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Install system dependencies (git, build tools for tree-sitter/lancedb)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install SOTA python dependencies
# Note: tree-sitter packages and lancedb are included for the Hybrid RAG architecture
RUN pip install \
    kuzu \
    fastapi \
    uvicorn \
    pydantic \
    redis \
    lancedb \
    sentence-transformers \
    tree-sitter \
    tree-sitter-python \
    tree-sitter-javascript \
    tree-sitter-typescript

COPY src/cognebula.py /app/cognebula.py
RUN chmod +x /app/cognebula.py

ENV PORT=8766 \
    HOST=0.0.0.0

EXPOSE 8766

# Entrypoint script handles both API server and background Worker modes
RUN echo '#!/bin/bash\n\
if [ "$MODE" = "worker" ]; then\n\
    echo "Starting CogNebula Event-Driven Ingestion Worker..."\n\
    # In a full implementation, this would start the celery/redis consumer\n\
    # For now, we simulate the worker loop\n\
    while true; do sleep 60; done\n\
else\n\
    if [ ! -f /data/cognebula-registry.json ]; then\n\
        echo "Initializing registry in /data..."\n\
        python /app/cognebula.py setup\n\
    fi\n\
    for d in /data/*/; do\n\
        if [ -d "$d" ] && [ "$(basename "$d")" != "cognebula-registry" ]; then\n\
            echo "Auto-analyzing $d..."\n\
            python /app/cognebula.py analyze "$d"\n\
        fi\n\
    done\n\
    echo "Starting CogNebula SOTA API Gateway on $HOST:$PORT..."\n\
    exec python /app/cognebula.py serve --host $HOST --port $PORT\n\
fi\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

VOLUME ["/data"]

ENTRYPOINT ["/app/entrypoint.sh"]
