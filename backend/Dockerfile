FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# Minimal system dependencies
# Skip apt-get to avoid network timeouts during build
# RUN apt-get update --fix-missing && \
#     apt-get install -y --no-install-recommends curl && \
#     rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Health check using Python instead of curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import http.client; conn = http.client.HTTPConnection('localhost', 8000); conn.request('GET', '/health'); response = conn.getresponse(); exit(0) if response.status == 200 else exit(1)"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
