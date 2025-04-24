# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    mkdir -p /var/log/app && \
    chown -R appuser:appuser /var/log/app

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY app.py .
COPY healthcheck.py .

# Make healthcheck script executable
RUN chmod +x /app/healthcheck.py && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER appuser

EXPOSE 5000

# Run the application with Gunicorn
CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:5000", "app:app"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python /app/healthcheck.py