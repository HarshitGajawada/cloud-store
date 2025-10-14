FROM python:3.11-slim

WORKDIR /app

# Install cron and other system dependencies
RUN apt-get update && \
    apt-get install -y cron && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy cron job setup script
COPY setup_cron.sh /setup_cron.sh
RUN chmod +x /setup_cron.sh

# Create log directory
RUN mkdir -p /var/log/hybrid-storage

# Expose port
EXPOSE 8000

# Setup cron, run migrations, and start the application
CMD /setup_cron.sh && cron && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
