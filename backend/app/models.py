from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship to files
    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    content_type = Column(String(100))
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash for deduplication
    storage_location = Column(String(20), nullable=False, index=True)
    object_key = Column(String(500), nullable=False)
    access_url = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship to user
    owner = relationship("User", back_populates="files")
    access_logs = relationship("FileAccessLog", back_populates="file", cascade="all, delete-orphan")

    # Additional indexes
    __table_args__ = (
        Index('idx_files_user_storage', 'user_id', 'storage_location'),
        Index('idx_files_user_hash', 'user_id', 'content_hash'),
    )


class FileAccessLog(Base):
    """Track file access events for analytics"""
    __tablename__ = "file_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # 'view', 'download', 'delete'
    accessed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    file = relationship("File", back_populates="access_logs")
    user = relationship("User")
