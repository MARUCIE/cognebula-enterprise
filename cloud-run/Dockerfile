FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir kuzu google-cloud-storage

# Copy scripts
COPY run_job.py .

# Default: run the job
CMD ["python", "-u", "run_job.py"]
