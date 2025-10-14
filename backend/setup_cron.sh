#!/bin/bash

# Create cron job for sync every 2 minutes
# Load environment variables from docker-compose
echo "*/2 * * * * cd /app && MINIO_ENDPOINT=minio:9000 MINIO_PUBLIC_ENDPOINT=localhost:9000 MINIO_ACCESS_KEY=minioadmin MINIO_SECRET_KEY=minioadmin MINIO_BUCKET=minio-cloud-store MINIO_SECURE=false DATABASE_URL=postgresql://postgres:postgres@postgres:5432/hybrid_storage AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} AWS_REGION=${AWS_REGION} S3_BUCKET=${S3_BUCKET} /usr/local/bin/python -m app.sync_job >> /var/log/hybrid-storage/sync.log 2>&1" | crontab -

echo "Cron job configured to run every 2 minutes (*/2 * * * *)"
