# Implementation Plan

- [x] 1. Set up project structure and configuration

  - Create backend directory with FastAPI project structure (app/, alembic/, requirements.txt)
  - Create frontend directory with React + Vite project structure
  - Create Docker configuration files (Dockerfile for backend, Dockerfile for frontend, docker-compose.yml)
  - Create environment variable templates (.env.example for backend and frontend)
  - Set up .gitignore files for both backend and frontend
  - _Requirements: 9.1, 9.2, 9.4_

- [x] 2. Implement database models and migrations

  - [x] 2.1 Create SQLAlchemy User model with email and hashed_password fields
    - Define User model with id, email, hashed_password, created_at, updated_at
    - Add email index for query optimization
    - _Requirements: 1.3, 1.4_
  - [x] 2.2 Create SQLAlchemy File model with user relationship
    - Define File model with id, user_id, filename, original_filename, file_size, content_type, storage_location, object_key, access_url, uploaded_at, synced_at
    - Add foreign key relationship to User model
    - Add indexes on user_id and storage_location
    - _Requirements: 3.5, 4.5, 8.1_
  - [x] 2.3 Set up Alembic and create initial migration
    - Initialize Alembic configuration
    - Generate migration for User and File models
    - _Requirements: 9.1_

- [x] 3. Implement authentication system

  - [x] 3.1 Create password hashing and JWT token utilities
    - Implement hash_password() using passlib with bcrypt
    - Implement verify_password() for credential validation
    - Implement create_access_token() with 24-hour expiration
    - Implement verify_token() for JWT validation
    - _Requirements: 1.4, 2.2, 2.5_
  - [x] 3.2 Create authentication dependency for protected routes
    - Implement get_current_user() dependency that extracts and validates JWT from Authorization header
    - Handle token expiration and invalid token errors
    - _Requirements: 2.6, 8.2_
  - [x] 3.3 Implement user registration endpoint
    - Create POST /api/auth/signup endpoint
    - Validate email format and password length (minimum 8 characters)
    - Check for duplicate email and return 409 Conflict if exists
    - Hash password before storing
    - Return success message with user_id
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
  - [x] 3.4 Implement user login endpoint
    - Create POST /api/auth/login endpoint
    - Validate credentials against database
    - Generate and return JWT token on success
    - Return 401 Unauthorized for invalid credentials
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 4. Implement storage client abstraction

  - [x] 4.1 Create MinIO client wrapper
    - Initialize MinIO client with environment variables
    - Implement upload_to_minio() to store files with user-scoped paths (user-{user_id}/{uuid}-{filename})
    - Implement get_minio_presigned_url() to generate temporary access URLs
    - Implement delete_from_minio() for cleanup after sync
    - Implement get_file_from_minio() to retrieve file for transfer
    - Handle MinIO connection errors and return appropriate exceptions
    - _Requirements: 4.1, 4.2, 4.4, 5.6, 9.1_
  - [x] 4.2 Create S3 client wrapper
    - Initialize boto3 S3 client with AWS credentials from environment
    - Implement upload_to_s3() to store files with user-scoped paths
    - Implement get_s3_public_url() to generate public access URLs
    - Handle S3 upload errors and implement retry logic
    - _Requirements: 5.2, 5.4, 9.2_
  - [x] 4.3 Create unified StorageService class
    - Combine MinIO and S3 clients into single service
    - Implement transfer_file_to_s3() that downloads from MinIO and uploads to S3
    - Add error handling and logging for all storage operations
    - _Requirements: 5.2, 10.1, 10.2_

- [x] 5. Implement file upload API

  - [x] 5.1 Create file upload endpoint
    - Create POST /api/files/upload endpoint with authentication dependency
    - Accept multipart/form-data file upload
    - Validate file size (max 100MB)
    - Generate unique filename using UUID
    - Upload file to MinIO using StorageService
    - Create File record in database with user_id, storage_location="minio", and MinIO presigned URL
    - Return file metadata (id, filename, file_size, storage_location, access_url, uploaded_at)
    - _Requirements: 3.1, 3.5, 3.6, 4.1, 4.2, 4.3, 7.1, 7.2, 8.1_
  - [x] 5.2 Add error handling for upload failures
    - Handle MinIO unavailable errors and return 503 Service Unavailable
    - Handle file size validation errors and return 400 Bad Request
    - Log all upload operations with file metadata
    - _Requirements: 3.4, 4.4, 10.1, 10.2_

- [x] 6. Implement file listing and retrieval API

  - [x] 6.1 Create file list endpoint
    - Create GET /api/files endpoint with authentication dependency
    - Query files filtered by authenticated user's ID
    - Return array of file metadata with current storage_location and access_url
    - _Requirements: 6.1, 6.2, 6.3, 7.3, 8.4_
  - [x] 6.2 Create file details endpoint
    - Create GET /api/files/{file_id} endpoint with authentication dependency
    - Verify file ownership before returning details
    - Return 403 Forbidden if user doesn't own the file
    - Return complete file metadata
    - _Requirements: 6.6, 7.4, 8.2, 8.3_
  - [x] 6.3 Create file download endpoint
    - Create GET /api/files/{file_id}/download endpoint with authentication dependency
    - Verify file ownership
    - Return redirect to current access_url (MinIO presigned or S3 public URL)
    - _Requirements: 6.5, 8.2_

- [x] 7. Implement midnight sync job

  - [x] 7.1 Create sync job script
    - Create app/sync_job.py as standalone Python script
    - Implement main() function that connects to database
    - Query all files where storage_location="minio"
    - Process files in batches of 10
    - For each file: download from MinIO, upload to S3, update database record
    - Update storage_location to "s3" and access_url to S3 public URL
    - Update synced_at timestamp
    - Optionally delete from MinIO based on DELETE_FROM_MINIO_AFTER_SYNC env var
    - Log batch processing results (files processed, succeeded, failed)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6, 5.7, 10.3_
  - [x] 7.2 Add error handling and retry logic for sync job
    - Wrap each file transfer in try-except block
    - Log errors but continue processing remaining files
    - Failed files remain in MinIO for next run
    - _Requirements: 5.5, 10.1, 10.3_
  - [x] 7.3 Create cron setup script
    - Create setup_cron.sh script that adds cron job entry
    - Configure cron to run sync_job.py at midnight (0 0 \* \* \*)
    - Redirect output to log file
    - _Requirements: 5.1, 9.3_

- [x] 8. Set up FastAPI application and CORS

  - [x] 8.1 Create main FastAPI application
    - Initialize FastAPI app with title and version
    - Configure CORS middleware for frontend origin
    - Include authentication and file routers
    - Add global exception handler for consistent error responses
    - _Requirements: 7.5, 7.6_
  - [x] 8.2 Create configuration module
    - Load all environment variables using pydantic BaseSettings
    - Validate required configuration on startup
    - Raise clear errors if required config is missing
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [x] 8.3 Set up logging configuration
    - Configure Python logging with INFO level for normal operations
    - Configure ERROR level for exceptions
    - Add structured logging with timestamps
    - _Requirements: 10.1, 10.4, 10.5_

- [x] 9. Create Docker configuration

  - [x] 9.1 Create backend Dockerfile
    - Use python:3.11-slim base image
    - Install cron package
    - Copy requirements.txt and install dependencies
    - Copy application code
    - Copy and configure setup_cron.sh
    - Set CMD to start cron, run migrations, and start uvicorn
    - _Requirements: 9.1, 9.2_
  - [x] 9.2 Create docker-compose.yml
    - Define postgres service with persistent volume
    - Define minio service with persistent volume and console port
    - Define backend service with environment variables and dependencies
    - Define frontend service (placeholder for now)
    - Configure health checks for postgres and minio
    - _Requirements: 9.1, 9.2, 9.5_

- [x] 10. Implement React frontend authentication

  - [x] 10.1 Create authentication context and hooks
    - Create AuthContext with user state and token management
    - Implement useAuth hook for accessing auth state
    - Store JWT token in localStorage
    - Implement login(), signup(), and logout() functions
    - _Requirements: 1.6, 2.2, 2.3_
  - [x] 10.2 Create signup page component
    - Create form with email and password fields
    - Implement client-side validation (email format, password min 8 chars)
    - Call POST /api/auth/signup on form submit
    - Display success message and redirect to login
    - Display error messages for duplicate email or validation errors
    - _Requirements: 1.1, 1.2, 1.5, 1.6_
  - [x] 10.3 Create login page component
    - Create form with email and password fields
    - Call POST /api/auth/login on form submit
    - Store JWT token in AuthContext and localStorage
    - Redirect to dashboard on success
    - Display error message for invalid credentials
    - _Requirements: 2.1, 2.3, 2.4_
  - [x] 10.4 Create ProtectedRoute component
    - Check if user is authenticated before rendering route
    - Redirect to login page if not authenticated
    - _Requirements: 2.6_

- [x] 11. Implement React frontend file management

  - [x] 11.1 Create file upload component
    - Create drag-and-drop upload area using react-dropzone
    - Display selected file name and size before upload
    - Show upload progress bar during upload
    - Call POST /api/files/upload with Authorization header
    - Display success message with storage location on completion
    - Display error message and retry button on failure
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 11.2 Create file list component
    - Fetch files from GET /api/files with Authorization header
    - Display files in table/grid with filename, size, storage location, upload date
    - Show storage location badge (MinIO in blue, S3 in green)
    - Display access URL or download button for each file
    - Implement auto-refresh every 30 seconds to catch sync updates
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  - [x] 11.3 Create dashboard page component
    - Combine FileUpload and FileList components
    - Add navbar with user email and logout button
    - Implement responsive layout
    - _Requirements: 6.1_
  - [x] 11.4 Set up React Router and navigation
    - Configure routes for /login, /signup, /dashboard
    - Implement navigation between pages
    - Apply ProtectedRoute to dashboard
    - _Requirements: 2.3_

- [x] 12. Create frontend Dockerfile and integrate with docker-compose

  - [x] 12.1 Create frontend Dockerfile with multi-stage build
    - Build stage: install dependencies and build React app
    - Production stage: serve built files with nginx
    - Copy nginx configuration for SPA routing
    - _Requirements: 9.1_
  - [x] 12.2 Update docker-compose.yml with frontend service
    - Add frontend service definition
    - Configure build context and environment variables
    - Expose port 3000
    - Add dependency on backend service
    - _Requirements: 9.1, 9.5_

- [x] 13. Create setup documentation and environment templates
  - Create README.md with setup instructions
  - Create .env.example files for backend and frontend
  - Document Docker Compose commands
  - Document cron job setup
  - Add API endpoint documentation
  - _Requirements: 9.1, 9.2, 9.3_
