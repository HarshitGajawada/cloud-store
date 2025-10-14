# Design Document: Hybrid Cloud File Storage System

## Overview

The Hybrid Cloud File Storage System is a full-stack application that provides secure file storage with automatic cloud synchronization. The system uses a three-tier architecture:

- **Frontend**: React-based SPA for user interaction
- **Backend**: FastAPI REST API for business logic and file operations
- **Storage**: MinIO for local storage, AWS S3 for cloud backup
- **Database**: PostgreSQL for metadata and user management
- **Background Jobs**: Cron job for automated file synchronization at midnight

The system implements JWT-based authentication to ensure users can only access their own files, with automatic migration of files from local MinIO storage to AWS S3.

## Architecture

### System Architecture Diagram

```mermaid
graph TB
    subgraph "Frontend Layer"
        React[React SPA]
    end
    
    subgraph "Backend Layer"
        API[FastAPI Server]
        Auth[Auth Service]
        FileService[File Service]
        SyncJob[Sync Scheduler]
    end
    
    subgraph "Storage Layer"
        MinIO[MinIO Server]
        S3[AWS S3]
        DB[(PostgreSQL)]
    end
    
    React -->|HTTP/REST| API
    API --> Auth
    API --> FileService
    API --> DB
    FileService --> MinIO
    FileService --> S3
    SyncJob --> FileService
    SyncJob --> DB
```

### Technology Stack

**Backend:**
- FastAPI (Python web framework)
- SQLAlchemy (ORM)
- Alembic (database migrations)
- boto3 (AWS S3 client)
- minio (MinIO Python client)
- python-jose (JWT handling)
- passlib (password hashing)
- python-multipart (file upload handling)
- Cron (system-level job scheduling)

**Frontend:**
- React 18
- React Router (navigation)
- Axios (HTTP client)
- TanStack Query (data fetching and caching)
- Tailwind CSS (styling)
- React Dropzone (file upload UI)

**Infrastructure:**
- PostgreSQL (user and file metadata)
- MinIO (local object storage)
- AWS S3 (cloud object storage)

## Components and Interfaces

### Backend Components

#### 1. Authentication Module

**Purpose**: Handle user registration, login, and JWT token management

**Components:**
- `auth.py`: Authentication utilities (password hashing, token generation/validation)
- `auth_router.py`: API endpoints for signup and login

**Key Functions:**
```python
def hash_password(password: str) -> str
def verify_password(plain_password: str, hashed_password: str) -> bool
def create_access_token(data: dict, expires_delta: timedelta) -> str
def verify_token(token: str) -> dict
def get_current_user(token: str) -> User
```

**API Endpoints:**
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Authenticate and get JWT token

#### 2. File Management Module

**Purpose**: Handle file uploads, downloads, and metadata management

**Components:**
- `file_service.py`: Business logic for file operations
- `file_router.py`: API endpoints for file operations
- `storage_client.py`: Abstraction layer for MinIO and S3 operations

**Key Functions:**
```python
class StorageClient:
    def upload_to_minio(file: UploadFile, user_id: int) -> str
    def upload_to_s3(file_path: str, user_id: int, filename: str) -> str
    def get_minio_url(object_key: str) -> str
    def get_s3_url(object_key: str) -> str
    def delete_from_minio(object_key: str) -> bool
    def transfer_to_s3(object_key: str) -> bool
```

**API Endpoints:**
- `POST /api/files/upload` - Upload file to MinIO
- `GET /api/files` - List user's files
- `GET /api/files/{file_id}` - Get file details
- `GET /api/files/{file_id}/download` - Download file

#### 3. Sync Job Module

**Purpose**: Automatically transfer files from MinIO to S3 at midnight

**Components:**
- `sync_job.py`: Standalone script for file synchronization
- `cron_setup.sh`: Script to configure cron job

**Key Functions:**
```python
def sync_files_to_s3():
    """Main sync job that runs at midnight via cron"""
    
def process_file_batch(files: List[File]) -> dict:
    """Process a batch of files for sync"""
    
def update_file_location(file_id: int, new_location: str, new_url: str):
    """Update file metadata after successful sync"""
    
def main():
    """Entry point for cron job execution"""
```

**Cron Configuration:**
- Runs daily at midnight (00:00)
- Cron expression: `0 0 * * *`
- Processes files in batches of 10
- Implements retry logic for failed transfers
- Logs execution to dedicated log file

#### 4. Database Models

**User Model:**
```python
class User:
    id: int (PK)
    email: str (unique, indexed)
    hashed_password: str
    created_at: datetime
    updated_at: datetime
```

**File Model:**
```python
class File:
    id: int (PK)
    user_id: int (FK -> User.id, indexed)
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    storage_location: str  # "minio" or "s3"
    object_key: str  # Storage path
    access_url: str
    uploaded_at: datetime
    synced_at: datetime (nullable)
    created_at: datetime
    updated_at: datetime
```

### Frontend Components

#### 1. Authentication Components

**LoginPage.jsx:**
- Login form with email/password
- Form validation
- Error handling
- Redirect to dashboard on success

**SignupPage.jsx:**
- Registration form with email/password
- Password strength indicator
- Form validation
- Redirect to login on success

**AuthContext.jsx:**
- Global authentication state
- Token storage in localStorage
- Automatic token refresh
- Protected route wrapper

#### 2. File Management Components

**Dashboard.jsx:**
- Main application view
- File upload area
- File list display
- User profile/logout

**FileUpload.jsx:**
- Drag-and-drop file upload
- Upload progress indicator
- File size validation
- Success/error notifications

**FileList.jsx:**
- Table/grid view of files
- Storage location badge (MinIO/S3)
- File metadata display
- Download buttons
- Auto-refresh on storage location changes

**FileItem.jsx:**
- Individual file display
- Storage status indicator
- Download link
- File metadata (size, upload date)

#### 3. Shared Components

**ProtectedRoute.jsx:**
- Route wrapper requiring authentication
- Redirect to login if not authenticated

**Navbar.jsx:**
- Application header
- User info display
- Logout button

### API Request/Response Schemas

**Authentication:**
```typescript
// POST /api/auth/signup
Request: { email: string, password: string }
Response: { message: string, user_id: number }

// POST /api/auth/login
Request: { email: string, password: string }
Response: { access_token: string, token_type: string, user: { id: number, email: string } }
```

**File Operations:**
```typescript
// POST /api/files/upload
Request: FormData { file: File }
Headers: { Authorization: "Bearer <token>" }
Response: {
  id: number,
  filename: string,
  file_size: number,
  storage_location: "minio",
  access_url: string,
  uploaded_at: string
}

// GET /api/files
Headers: { Authorization: "Bearer <token>" }
Response: {
  files: [{
    id: number,
    filename: string,
    file_size: number,
    storage_location: "minio" | "s3",
    access_url: string,
    uploaded_at: string,
    synced_at: string | null
  }]
}
```

## Data Models

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- Files table
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    content_type VARCHAR(100),
    storage_location VARCHAR(20) NOT NULL,
    object_key VARCHAR(500) NOT NULL,
    access_url TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_files_user_id ON files(user_id);
CREATE INDEX idx_files_storage_location ON files(storage_location);
```

### Object Storage Structure

**MinIO Bucket Structure:**
```
bucket-name/
  user-{user_id}/
    {uuid}-{filename}
```

**S3 Bucket Structure:**
```
bucket-name/
  user-{user_id}/
    {uuid}-{filename}
```

## Error Handling

### Backend Error Handling

**HTTP Status Codes:**
- 200: Success
- 201: Created
- 400: Bad Request (validation errors)
- 401: Unauthorized (missing/invalid token)
- 403: Forbidden (accessing other user's files)
- 404: Not Found
- 409: Conflict (duplicate email)
- 500: Internal Server Error

**Error Response Format:**
```json
{
  "detail": "Error message",
  "error_code": "SPECIFIC_ERROR_CODE"
}
```

**Exception Handling Strategy:**
- Custom exception classes for domain-specific errors
- Global exception handler in FastAPI
- Structured logging for all errors
- Graceful degradation for storage failures

### Frontend Error Handling

**Error Display:**
- Toast notifications for user-facing errors
- Form validation errors inline
- Network error retry mechanisms
- Fallback UI for failed data loads

**Error Recovery:**
- Automatic token refresh on 401
- Retry failed uploads
- Graceful handling of sync delays

## Testing Strategy

### Backend Testing

**Unit Tests:**
- Authentication functions (password hashing, token generation)
- File service methods (upload, download, metadata)
- Storage client operations (mocked MinIO/S3)
- Database models and queries

**Integration Tests:**
- API endpoint tests with test database
- File upload/download workflows
- Authentication flow end-to-end
- Sync job execution

**Test Tools:**
- pytest (test framework)
- pytest-asyncio (async test support)
- httpx (API testing)
- moto (AWS S3 mocking)
- testcontainers (MinIO/PostgreSQL containers)

### Frontend Testing

**Unit Tests:**
- Component rendering
- Form validation logic
- Authentication context
- Utility functions

**Integration Tests:**
- User authentication flow
- File upload workflow
- File list updates

**Test Tools:**
- Vitest (test runner)
- React Testing Library
- MSW (API mocking)

## Security Considerations

### Authentication & Authorization

- Passwords hashed using bcrypt (cost factor 12)
- JWT tokens with 24-hour expiration
- Token stored in localStorage (with XSS protection)
- All file operations require valid JWT
- User ID extracted from token, not request body
- Database queries filtered by authenticated user ID

### File Security

- File uploads validated for size limits
- Content-type validation
- Unique filenames using UUID to prevent collisions
- User-scoped storage paths
- Presigned URLs for MinIO (short expiration)
- S3 bucket policies restricting public access

### API Security

- CORS configuration for frontend origin only
- Rate limiting on authentication endpoints
- Input validation using Pydantic models
- SQL injection prevention via SQLAlchemy ORM
- File path traversal prevention

## Configuration Management

### Environment Variables

**Backend (.env):**
```
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/hybrid_storage

# JWT
SECRET_KEY=<random-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=local-files
MINIO_SECURE=false

# AWS S3
AWS_ACCESS_KEY_ID=<aws-key>
AWS_SECRET_ACCESS_KEY=<aws-secret>
AWS_REGION=us-east-1
S3_BUCKET=cloud-files

# Sync Job
SYNC_BATCH_SIZE=10
DELETE_FROM_MINIO_AFTER_SYNC=false
SYNC_LOG_FILE=/var/log/hybrid-storage/sync.log

# File Upload
MAX_FILE_SIZE_MB=100
```

**Frontend (.env):**
```
VITE_API_BASE_URL=http://localhost:8000
```

## Docker Containerization

### Docker Architecture

The application uses Docker Compose to orchestrate multiple services:

```mermaid
graph TB
    subgraph "Docker Compose Stack"
        Frontend[Frontend Container<br/>Nginx + React Build]
        Backend[Backend Container<br/>FastAPI + Uvicorn]
        DB[(PostgreSQL Container)]
        MinIO[MinIO Container]
        
        Frontend -->|API Requests| Backend
        Backend --> DB
        Backend --> MinIO
    end
    
    Backend -->|Sync Job| S3[AWS S3<br/>External]
```

### Container Definitions

**1. Backend Container (FastAPI)**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app ./app

# Copy cron job setup script
COPY setup_cron.sh /setup_cron.sh
RUN chmod +x /setup_cron.sh

# Setup cron job and start services
CMD /setup_cron.sh && cron && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**setup_cron.sh:**
```bash
#!/bin/bash
# Create cron job for midnight sync
echo "0 0 * * * cd /app && python -m app.sync_job >> /var/log/cron.log 2>&1" | crontab -
echo "Cron job configured to run at midnight"
```

**2. Frontend Container (React + Nginx)**
```dockerfile
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**3. PostgreSQL Container**
- Use official PostgreSQL image
- Persistent volume for data
- Initialization scripts for schema

**4. MinIO Container**
- Use official MinIO image
- Persistent volume for object storage
- Console UI for management

### Docker Compose Configuration

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: hybrid-storage-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: hybrid_storage
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: hybrid-storage-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: hybrid-storage-backend
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/hybrid_storage
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
      MINIO_BUCKET: local-files
      MINIO_SECURE: "false"
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_REGION: ${AWS_REGION}
      S3_BUCKET: ${S3_BUCKET}
      SECRET_KEY: ${SECRET_KEY}
      DELETE_FROM_MINIO_AFTER_SYNC: "false"
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_BASE_URL: http://localhost:8000
    container_name: hybrid-storage-frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  postgres_data:
  minio_data:
```

### Development vs Production Docker Setup

**Development (docker-compose.dev.yml):**
- Hot reload enabled for backend and frontend
- Volume mounts for live code changes
- Debug logging enabled
- Exposed database and MinIO ports for direct access

```yaml
services:
  backend:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
    environment:
      LOG_LEVEL: DEBUG

  frontend:
    command: npm run dev -- --host
    volumes:
      - ./frontend:/app
      - /app/node_modules
```

**Production (docker-compose.prod.yml):**
- Optimized builds
- No volume mounts
- Production-grade web server (Gunicorn for backend)
- Health checks enabled
- Resource limits defined

```yaml
services:
  backend:
    command: gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

## Deployment Considerations

### Development Setup

**Using Docker Compose:**
```bash
# Clone repository
git clone <repo-url>
cd hybrid-cloud-storage

# Create .env file with AWS credentials
cp .env.example .env
# Edit .env with your AWS credentials

# Start all services
docker-compose up -d

# Set up cron job for midnight sync
# The backend container will have a cron job configured to run at midnight
# Or set up on host machine:
crontab -e
# Add: 0 0 * * * docker exec hybrid-storage-backend python -m app.sync_job

# View logs
docker-compose logs -f

# Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# MinIO Console: http://localhost:9001
```

**Without Docker (Manual Setup):**
1. Install PostgreSQL and create database
2. Run MinIO in Docker: `docker run -p 9000:9000 -p 9001:9001 minio/minio server /data --console-address ":9001"`
3. Set up Python virtual environment and install dependencies
4. Run backend: `uvicorn app.main:app --reload`
5. Install Node.js dependencies and run frontend: `npm run dev`

### Production Deployment

**Option 1: Docker Compose on VPS/EC2**
- Deploy docker-compose.prod.yml on a single server
- Use Nginx reverse proxy for SSL termination
- Automated backups for PostgreSQL and MinIO volumes
- CloudWatch/monitoring for container health

**Option 2: Kubernetes**
- Separate deployments for each service
- Horizontal pod autoscaling for backend
- Persistent volume claims for database and MinIO
- Ingress controller for routing
- Secrets management for credentials

**Option 3: Cloud-Native Services**
- Backend: AWS ECS/Fargate, GCP Cloud Run, Azure Container Instances
- Frontend: S3 + CloudFront, Netlify, Vercel
- Database: AWS RDS, GCP Cloud SQL, Azure Database
- MinIO: Dedicated EC2/VM or managed MinIO service

**Infrastructure Requirements:**
- SSL/TLS certificates (Let's Encrypt or cloud provider)
- Domain name and DNS configuration
- AWS S3 bucket with appropriate IAM policies
- Secrets management (AWS Secrets Manager, HashiCorp Vault)
- Monitoring and logging (CloudWatch, Datadog, ELK stack)
- Backup strategy for database and MinIO data

## Performance Optimization

### Backend Optimizations

- Database connection pooling
- Indexed queries on user_id and storage_location
- Batch processing in sync job
- Async file operations
- Streaming file uploads/downloads

### Frontend Optimizations

- Code splitting by route
- Lazy loading components
- TanStack Query for caching
- Debounced file list refresh
- Optimistic UI updates

### Storage Optimizations

- Multipart uploads for large files
- Presigned URLs to offload bandwidth
- S3 lifecycle policies for archival
- MinIO erasure coding for redundancy
