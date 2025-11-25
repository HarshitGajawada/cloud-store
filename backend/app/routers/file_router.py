import logging
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, File, FileAccessLog
from app.schemas import FileUploadResponse, FileListResponse, FileResponse, DuplicateFileResponse
from app.auth import get_current_user, verify_token
from app.storage import storage_service
import os

logger = logging.getLogger(__name__)


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content for duplicate detection"""
    return hashlib.sha256(content).hexdigest()


def log_file_access(db: Session, file_id: int, user_id: int, action: str):
    """Log file access event for analytics"""
    access_log = FileAccessLog(
        file_id=file_id,
        user_id=user_id,
        action=action
    )
    db.add(access_log)
    db.commit()

router = APIRouter(prefix="/api/files", tags=["files"])

# Configuration
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload file to MinIO storage with duplicate detection
    
    - Accepts multipart/form-data file upload
    - Validates file size (max 100MB)
    - Computes SHA-256 hash for duplicate detection
    - If duplicate found, returns existing file info
    - Generates unique filename using UUID
    - Uploads to MinIO with user-scoped path
    - Creates File record in database
    - Returns file metadata with MinIO presigned URL
    """
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Compute content hash for duplicate detection
        content_hash = compute_file_hash(file_content)
        
        # Check for duplicate file (same content hash for this user)
        existing_file = db.query(File).filter(
            File.user_id == current_user.id,
            File.content_hash == content_hash
        ).first()
        
        if existing_file:
            logger.info(f"Duplicate file detected: {existing_file.id} for user {current_user.id}")
            return DuplicateFileResponse(
                is_duplicate=True,
                message=f"File already exists as '{existing_file.original_filename}'",
                existing_file=FileResponse.model_validate(existing_file)
            )
        
        # Get content type
        content_type = file.content_type or "application/octet-stream"
        
        # Create file-like object for MinIO
        from io import BytesIO
        file_data = BytesIO(file_content)
        
        # Upload to MinIO
        try:
            object_key, presigned_url = storage_service.upload_to_minio(
                file_data,
                current_user.id,
                file.filename,
                content_type
            )
        except Exception as e:
            logger.error(f"MinIO upload failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Storage service unavailable. Please try again later."
            )
        
        # Extract unique filename from object_key
        unique_filename = object_key.split('/')[-1]
        
        # Create file record in database with content hash
        db_file = File(
            user_id=current_user.id,
            filename=unique_filename,
            original_filename=file.filename,
            file_size=file_size,
            content_type=content_type,
            content_hash=content_hash,
            storage_location="minio",
            object_key=object_key,
            access_url=presigned_url
        )
        
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        logger.info(f"File uploaded successfully: {db_file.id} by user {current_user.id}")
        
        return FileUploadResponse(
            id=db_file.id,
            filename=db_file.filename,
            file_size=db_file.file_size,
            storage_location=db_file.storage_location,
            access_url=db_file.access_url,
            uploaded_at=db_file.uploaded_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while uploading the file"
        )


@router.get("", response_model=FileListResponse)
def list_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all files owned by the authenticated user
    
    - Returns files filtered by user ID
    - Includes current storage location and access URL
    """
    files = db.query(File).filter(File.user_id == current_user.id).order_by(File.uploaded_at.desc()).all()
    
    return FileListResponse(
        files=[FileResponse.from_orm(file) for file in files]
    )


@router.get("/{file_id}", response_model=FileResponse)
def get_file_details(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific file
    
    - Verifies file ownership
    - Returns complete file metadata
    """
    file = db.query(File).filter(File.id == file_id).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify ownership
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this file"
        )
    
    return FileResponse.from_orm(file)


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    token: str = None
):
    """
    Get download URL for a file
    
    - Verifies file ownership
    - Returns redirect to current access URL (MinIO presigned or S3 public)
    - Accepts token as query parameter for browser navigation
    """
    from fastapi.responses import RedirectResponse
    from app.auth import verify_token
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - token required"
        )
    
    # Verify token and get user
    try:
        payload = verify_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user_id = int(user_id_str)
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}"
        )
    
    file = db.query(File).filter(File.id == file_id).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify ownership
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this file"
        )
    
    # Log file access for analytics
    log_file_access(db, file.id, current_user.id, "download")
    
    from fastapi.responses import RedirectResponse, StreamingResponse
    import io
    
    # If file is in MinIO, stream through backend
    if file.storage_location == "minio":
        try:
            # Get file data from MinIO
            file_data = storage_service.minio.get_file_from_minio(file.object_key)
            
            # Stream the file with inline disposition to open in browser
            return StreamingResponse(
                io.BytesIO(file_data),
                media_type=file.content_type,
                headers={
                    "Content-Disposition": f'inline; filename="{file.original_filename}"'
                }
            )
        except Exception as e:
            logger.error(f"Error downloading file from MinIO: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error downloading file"
            )
    
    # For S3, redirect to public URL (bucket must be public)
    if file.storage_location == "s3":
        return RedirectResponse(url=file.access_url)
    
    # Fallback
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unknown storage location"
    )


@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    token: str = None
):
    """
    Delete a file from storage and database
    
    - Verifies file ownership
    - Deletes from MinIO or S3
    - Removes database record
    """
    # Verify token and get user
    try:
        payload = verify_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user_id = int(user_id_str)
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}"
        )
    
    file = db.query(File).filter(File.id == file_id).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Verify ownership
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this file"
        )
    
    # Delete from storage
    try:
        if file.storage_location == "minio":
            storage_service.delete_from_minio(file.object_key)
            logger.info(f"Deleted file {file_id} from MinIO")
        elif file.storage_location == "s3":
            # Delete from S3
            import boto3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=storage_service.s3.access_key,
                aws_secret_access_key=storage_service.s3.secret_key,
                region_name=storage_service.s3.region
            )
            s3_client.delete_object(
                Bucket=storage_service.s3.bucket,
                Key=file.object_key
            )
            logger.info(f"Deleted file {file_id} from S3")
    except Exception as e:
        logger.error(f"Error deleting file from storage: {e}")
        # Continue to delete from database even if storage deletion fails
    
    # Delete from database
    db.delete(file)
    db.commit()
    
    logger.info(f"Deleted file {file_id} from database")
    
    return {"message": "File deleted successfully"}
