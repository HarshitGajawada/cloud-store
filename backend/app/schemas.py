from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional


# Authentication Schemas
class UserSignup(BaseModel):
    email: str
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    
    @validator('email')
    def validate_email(cls, v):
        import re
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', v):
            raise ValueError('Invalid email format')
        return v


class UserLogin(BaseModel):
    email: str
    password: str
    
    @validator('email')
    def validate_email(cls, v):
        import re
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', v):
            raise ValueError('Invalid email format')
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class SignupResponse(BaseModel):
    message: str
    user_id: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# File Schemas
class FileUploadResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    storage_location: str
    access_url: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class FileResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    content_type: Optional[str]
    content_hash: Optional[str] = None
    storage_location: str
    access_url: str
    uploaded_at: datetime
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    files: list[FileResponse]


class DuplicateFileResponse(BaseModel):
    """Response when a duplicate file is detected"""
    is_duplicate: bool = True
    message: str
    existing_file: FileResponse


# Analytics Schemas
class FileAccessLogResponse(BaseModel):
    id: int
    file_id: int
    action: str
    accessed_at: datetime

    class Config:
        from_attributes = True


class AnalyticsSummary(BaseModel):
    """Summary analytics for user's files"""
    total_files: int
    total_storage_bytes: int
    files_in_minio: int
    files_in_s3: int
    total_downloads: int
    most_accessed_files: list[dict]


class AccessTimelineEntry(BaseModel):
    date: str
    count: int


class AccessTimeline(BaseModel):
    """File access timeline data"""
    timeline: list[AccessTimelineEntry]
