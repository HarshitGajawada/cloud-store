import os
import uuid
import logging
from typing import BinaryIO, Optional
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class MinIOClient:
    """Wrapper for MinIO client operations"""
    
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        self.public_endpoint = os.getenv("MINIO_PUBLIC_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket = os.getenv("MINIO_BUCKET", "local-files")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        
        # Use internal endpoint for connections (works inside Docker)
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created MinIO bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Error ensuring MinIO bucket exists: {e}")
            raise
    
    def upload_to_minio(self, file_data: BinaryIO, user_id: int, filename: str, content_type: str) -> str:
        """
        Upload file to MinIO with user-scoped path
        
        Args:
            file_data: File binary data
            user_id: User ID for scoping
            filename: Original filename
            content_type: MIME type of file
        
        Returns:
            Object key (path) in MinIO
        
        Raises:
            Exception: If upload fails
        """
        try:
            # Generate unique filename with user scope
            unique_filename = f"{uuid.uuid4()}-{filename}"
            object_key = f"user-{user_id}/{unique_filename}"
            
            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Reset to beginning
            
            # Upload to MinIO
            self.client.put_object(
                self.bucket,
                object_key,
                file_data,
                length=file_size,
                content_type=content_type
            )
            
            logger.info(f"Uploaded file to MinIO: {object_key}")
            return object_key
            
        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            raise Exception(f"Failed to upload to MinIO: {str(e)}")
    
    def get_minio_presigned_url(self, object_key: str, expires: timedelta = timedelta(hours=24)) -> str:
        """
        Generate presigned URL for MinIO object
        
        Args:
            object_key: Object path in MinIO
            expires: URL expiration time (default 24 hours)
        
        Returns:
            Presigned URL string accessible from browser
        """
        try:
            # Generate presigned URL
            # Since endpoint and public_endpoint are both localhost:9000, no replacement needed
            url = self.client.presigned_get_object(
                self.bucket,
                object_key,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating MinIO presigned URL: {e}")
            raise Exception(f"Failed to generate presigned URL: {str(e)}")
    
    def delete_from_minio(self, object_key: str) -> bool:
        """
        Delete file from MinIO
        
        Args:
            object_key: Object path in MinIO
        
        Returns:
            True if successful
        """
        try:
            self.client.remove_object(self.bucket, object_key)
            logger.info(f"Deleted file from MinIO: {object_key}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting from MinIO: {e}")
            return False
    
    def get_file_from_minio(self, object_key: str) -> bytes:
        """
        Retrieve file data from MinIO
        
        Args:
            object_key: Object path in MinIO
        
        Returns:
            File data as bytes
        """
        try:
            response = self.client.get_object(self.bucket, object_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error retrieving file from MinIO: {e}")
            raise Exception(f"Failed to retrieve file from MinIO: {str(e)}")


class S3Client:
    """Wrapper for AWS S3 client operations"""
    
    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.bucket = os.getenv("S3_BUCKET")
        
        if not self.access_key or not self.secret_key or not self.bucket:
            logger.warning("AWS S3 credentials not fully configured")
        
        self.client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )
    
    def upload_to_s3(self, file_data: bytes, user_id: int, filename: str, content_type: str) -> str:
        """
        Upload file to S3 with user-scoped path
        
        Args:
            file_data: File binary data
            user_id: User ID for scoping
            filename: Filename (should include UUID prefix)
            content_type: MIME type of file
        
        Returns:
            Object key (path) in S3
        
        Raises:
            Exception: If upload fails
        """
        try:
            # Use same path structure as MinIO
            object_key = f"user-{user_id}/{filename}"
            
            # Upload to S3 with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.client.put_object(
                        Bucket=self.bucket,
                        Key=object_key,
                        Body=file_data,
                        ContentType=content_type
                    )
                    logger.info(f"Uploaded file to S3: {object_key}")
                    return object_key
                except ClientError as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"S3 upload attempt {attempt + 1} failed, retrying...")
            
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise Exception(f"Failed to upload to S3: {str(e)}")
    
    def get_s3_public_url(self, object_key: str) -> str:
        """
        Generate public URL for S3 object
        
        Args:
            object_key: Object path in S3
        
        Returns:
            Public URL string
        """
        url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{object_key}"
        return url


class StorageService:
    """Unified storage service combining MinIO and S3 clients"""
    
    def __init__(self):
        self.minio = MinIOClient()
        self.s3 = S3Client()
    
    def upload_to_minio(self, file_data: BinaryIO, user_id: int, filename: str, content_type: str) -> tuple[str, str]:
        """
        Upload file to MinIO and return object key and presigned URL
        
        Returns:
            Tuple of (object_key, presigned_url)
        """
        object_key = self.minio.upload_to_minio(file_data, user_id, filename, content_type)
        presigned_url = self.minio.get_minio_presigned_url(object_key)
        return object_key, presigned_url
    
    def transfer_file_to_s3(self, object_key: str, user_id: int, content_type: str) -> str:
        """
        Transfer file from MinIO to S3
        
        Args:
            object_key: Object path in MinIO
            user_id: User ID
            content_type: MIME type
        
        Returns:
            S3 public URL
        
        Raises:
            Exception: If transfer fails
        """
        try:
            # Download from MinIO
            logger.info(f"Downloading file from MinIO: {object_key}")
            file_data = self.minio.get_file_from_minio(object_key)
            
            # Extract filename from object_key
            filename = object_key.split('/')[-1]
            
            # Upload to S3
            logger.info(f"Uploading file to S3: {object_key}")
            s3_object_key = self.s3.upload_to_s3(file_data, user_id, filename, content_type)
            
            # Generate S3 public URL
            s3_url = self.s3.get_s3_public_url(s3_object_key)
            
            logger.info(f"Successfully transferred file from MinIO to S3: {object_key}")
            return s3_url
            
        except Exception as e:
            logger.error(f"Error transferring file to S3: {e}")
            raise
    
    def delete_from_minio(self, object_key: str) -> bool:
        """Delete file from MinIO"""
        return self.minio.delete_from_minio(object_key)


# Singleton instance
storage_service = StorageService()
