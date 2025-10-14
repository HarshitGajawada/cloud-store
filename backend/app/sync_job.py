"""
Midnight sync job to transfer files from MinIO to S3

This script runs as a cron job at midnight (0 0 * * *) to automatically
sync files from local MinIO storage to AWS S3 cloud storage.
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import File
from app.storage import storage_service

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
SYNC_BATCH_SIZE = int(os.getenv("SYNC_BATCH_SIZE", "10"))
DELETE_FROM_MINIO_AFTER_SYNC = os.getenv("DELETE_FROM_MINIO_AFTER_SYNC", "false").lower() == "true"
SYNC_LOG_FILE = os.getenv("SYNC_LOG_FILE", "/var/log/hybrid-storage/sync.log")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(SYNC_LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def process_file_batch(files: list, session) -> dict:
    """
    Process a batch of files for sync
    
    Args:
        files: List of File objects to sync
        session: Database session
    
    Returns:
        Dictionary with processing statistics
    """
    stats = {
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "errors": []
    }
    
    for file in files:
        stats["processed"] += 1
        
        try:
            logger.info(f"Syncing file {file.id}: {file.filename} (user {file.user_id})")
            
            # Transfer file from MinIO to S3
            s3_url = storage_service.transfer_file_to_s3(
                file.object_key,
                file.user_id,
                file.content_type or "application/octet-stream"
            )
            
            # Update file record
            file.storage_location = "s3"
            file.access_url = s3_url
            file.synced_at = datetime.utcnow()
            
            session.commit()
            
            logger.info(f"Successfully synced file {file.id} to S3")
            stats["succeeded"] += 1
            
            # Optionally delete from MinIO
            if DELETE_FROM_MINIO_AFTER_SYNC:
                try:
                    storage_service.delete_from_minio(file.object_key)
                    logger.info(f"Deleted file {file.id} from MinIO")
                except Exception as e:
                    logger.warning(f"Failed to delete file {file.id} from MinIO: {e}")
            
        except Exception as e:
            stats["failed"] += 1
            error_msg = f"Failed to sync file {file.id}: {str(e)}"
            stats["errors"].append(error_msg)
            logger.error(error_msg)
            session.rollback()
            # Continue processing remaining files
            continue
    
    return stats


def main():
    """
    Main sync job function
    
    - Connects to database
    - Queries files where storage_location="minio"
    - Processes files in batches
    - Logs results
    """
    logger.info("=" * 80)
    logger.info("Starting midnight sync job")
    logger.info(f"Batch size: {SYNC_BATCH_SIZE}")
    logger.info(f"Delete from MinIO after sync: {DELETE_FROM_MINIO_AFTER_SYNC}")
    
    try:
        # Create database connection
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Query all files in MinIO
        files_to_sync = session.query(File).filter(
            File.storage_location == "minio"
        ).all()
        
        total_files = len(files_to_sync)
        logger.info(f"Found {total_files} files to sync")
        
        if total_files == 0:
            logger.info("No files to sync. Exiting.")
            session.close()
            return
        
        # Process files in batches
        total_stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "errors": []
        }
        
        for i in range(0, total_files, SYNC_BATCH_SIZE):
            batch = files_to_sync[i:i + SYNC_BATCH_SIZE]
            batch_num = (i // SYNC_BATCH_SIZE) + 1
            total_batches = (total_files + SYNC_BATCH_SIZE - 1) // SYNC_BATCH_SIZE
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} files)")
            
            batch_stats = process_file_batch(batch, session)
            
            # Aggregate statistics
            total_stats["processed"] += batch_stats["processed"]
            total_stats["succeeded"] += batch_stats["succeeded"]
            total_stats["failed"] += batch_stats["failed"]
            total_stats["errors"].extend(batch_stats["errors"])
            
            logger.info(
                f"Batch {batch_num} complete: "
                f"{batch_stats['succeeded']} succeeded, "
                f"{batch_stats['failed']} failed"
            )
        
        # Log final results
        logger.info("=" * 80)
        logger.info("Sync job completed")
        logger.info(f"Total files processed: {total_stats['processed']}")
        logger.info(f"Successfully synced: {total_stats['succeeded']}")
        logger.info(f"Failed: {total_stats['failed']}")
        
        if total_stats["errors"]:
            logger.error("Errors encountered:")
            for error in total_stats["errors"]:
                logger.error(f"  - {error}")
        
        logger.info("=" * 80)
        
        session.close()
        
    except Exception as e:
        logger.error(f"Critical error in sync job: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
