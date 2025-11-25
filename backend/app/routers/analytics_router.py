"""
Analytics router for file access analytics and usage patterns
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.models import User, File, FileAccessLog
from app.schemas import AnalyticsSummary, AccessTimeline, AccessTimelineEntry
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get analytics summary for the authenticated user
    
    Returns:
    - Total files count
    - Total storage usage in bytes
    - Files count by storage location (minio/s3)
    - Total downloads
    - Most accessed files (top 5)
    """
    # Total files and storage
    files = db.query(File).filter(File.user_id == current_user.id).all()
    total_files = len(files)
    total_storage = sum(f.file_size for f in files)
    
    # Files by storage location
    files_in_minio = len([f for f in files if f.storage_location == "minio"])
    files_in_s3 = len([f for f in files if f.storage_location == "s3"])
    
    # Total downloads
    total_downloads = db.query(FileAccessLog).join(File).filter(
        File.user_id == current_user.id,
        FileAccessLog.action == "download"
    ).count()
    
    # Most accessed files (top 5)
    most_accessed = db.query(
        File.id,
        File.original_filename,
        func.count(FileAccessLog.id).label("access_count")
    ).join(FileAccessLog).filter(
        File.user_id == current_user.id
    ).group_by(File.id, File.original_filename).order_by(
        desc("access_count")
    ).limit(5).all()
    
    most_accessed_files = [
        {
            "file_id": row[0],
            "filename": row[1],
            "access_count": row[2]
        }
        for row in most_accessed
    ]
    
    return AnalyticsSummary(
        total_files=total_files,
        total_storage_bytes=total_storage,
        files_in_minio=files_in_minio,
        files_in_s3=files_in_s3,
        total_downloads=total_downloads,
        most_accessed_files=most_accessed_files
    )


@router.get("/timeline", response_model=AccessTimeline)
def get_access_timeline(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get file access timeline for the authenticated user
    
    Args:
        days: Number of days to look back (default 30)
    
    Returns:
        Daily access counts for the specified period
    """
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 365"
        )
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Query access logs grouped by date
    access_logs = db.query(
        func.date(FileAccessLog.accessed_at).label("date"),
        func.count(FileAccessLog.id).label("count")
    ).join(File).filter(
        File.user_id == current_user.id,
        FileAccessLog.accessed_at >= start_date
    ).group_by(
        func.date(FileAccessLog.accessed_at)
    ).order_by("date").all()
    
    # Build timeline with all dates (fill in zeros for missing dates)
    timeline = []
    current_date = start_date.date()
    end_date = datetime.utcnow().date()
    
    # Create a dict of date -> count from query results
    date_counts = {str(row[0]): row[1] for row in access_logs}
    
    while current_date <= end_date:
        date_str = str(current_date)
        count = date_counts.get(date_str, 0)
        timeline.append(AccessTimelineEntry(date=date_str, count=count))
        current_date += timedelta(days=1)
    
    return AccessTimeline(timeline=timeline)


@router.get("/storage-breakdown")
def get_storage_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get storage breakdown by file type
    
    Returns storage usage grouped by content type
    """
    files = db.query(File).filter(File.user_id == current_user.id).all()
    
    # Group by content type
    breakdown = {}
    for f in files:
        content_type = f.content_type or "unknown"
        # Simplify content type (e.g., "image/png" -> "image")
        category = content_type.split("/")[0] if "/" in content_type else content_type
        
        if category not in breakdown:
            breakdown[category] = {"count": 0, "size_bytes": 0}
        
        breakdown[category]["count"] += 1
        breakdown[category]["size_bytes"] += f.file_size
    
    return {
        "breakdown": [
            {
                "category": category,
                "count": data["count"],
                "size_bytes": data["size_bytes"]
            }
            for category, data in sorted(breakdown.items(), key=lambda x: x[1]["size_bytes"], reverse=True)
        ]
    }


@router.get("/upload-history")
def get_upload_history(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get upload history for the authenticated user
    
    Returns daily upload counts and sizes for the specified period
    """
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days must be between 1 and 365"
        )
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Query uploads grouped by date
    uploads = db.query(
        func.date(File.uploaded_at).label("date"),
        func.count(File.id).label("count"),
        func.sum(File.file_size).label("total_size")
    ).filter(
        File.user_id == current_user.id,
        File.uploaded_at >= start_date
    ).group_by(
        func.date(File.uploaded_at)
    ).order_by("date").all()
    
    return {
        "history": [
            {
                "date": str(row[0]),
                "count": row[1],
                "total_size_bytes": row[2] or 0
            }
            for row in uploads
        ]
    }
