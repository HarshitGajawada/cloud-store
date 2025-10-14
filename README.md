# Hybrid Cloud Storage System

A full-stack application that provides secure file storage with automatic cloud synchronization. Files are initially stored on a local MinIO server for fast access, then automatically synchronized to AWS S3 via a scheduled background process.

## Features

- User authentication with JWT tokens
- File upload with drag-and-drop interface
- Initial storage on local MinIO for fast access
- Automatic nightly sync to AWS S3
- Real-time storage location tracking
- Secure file access with user-scoped permissions

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- PostgreSQL (database)
- SQLAlchemy (ORM)
- MinIO (local object storage)
- AWS S3 (cloud storage)

**Frontend:**
- React 18
- Vite
- Tailwind CSS
- React Router
- TanStack Query

**Infrastructure:**
- Docker & Docker Compose
- Nginx (frontend server)
- Cron (scheduled sync job)

## Prerequisites

- Docker and Docker Compose
- AWS account with S3 access
- AWS credentials (Access Key ID and Secret Access Key)

## Quick Start

### 1. Clone the repository

```bash
git clone <repository-url>
cd hybrid-cloud-storage
```

### 2. Configure environment variables

Copy the example environment file and update with your AWS credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your AWS credentials:

```env
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET=your-s3-bucket-name
SECRET_KEY=your-secret-key-here
```

### 3. Start the application

```bash
docker-compose up -d
```

This will start all services:
- PostgreSQL database (port 5432)
- MinIO server (port 9000, console on 9001)
- Backend API (port 8000)
- Frontend application (port 3000)

### 4. Access the application

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **MinIO Console:** http://localhost:9001 (credentials: minioadmin/minioadmin)

### 5. Create MinIO bucket

Before uploading files, create the MinIO bucket:

1. Open MinIO Console at http://localhost:9001
2. Login with credentials: minioadmin/minioadmin
3. Create a bucket named `local-files`
4. Set the bucket policy to allow read access

## Development Setup

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev
```

## Project Structure

```
hybrid-cloud-storage/
├── backend/
│   ├── app/
│   │   └── __init__.py
│   ├── alembic/
│   │   ├── versions/
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── setup_cron.sh
│   ├── .env.example
│   └── .gitignore
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── nginx.conf
│   ├── Dockerfile
│   ├── .env.example
│   └── .gitignore
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Sync Job

The system includes a cron job that runs at midnight (00:00) to sync files from MinIO to S3:

- Processes files in batches of 10
- Updates file metadata after successful sync
- Logs all operations to `/var/log/hybrid-storage/sync.log`
- Optionally deletes files from MinIO after sync (configurable)

To view sync logs:

```bash
docker exec hybrid-storage-backend cat /var/log/hybrid-storage/sync.log
```

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login and get JWT token

### File Operations
- `POST /api/files/upload` - Upload file (requires authentication)
- `GET /api/files` - List user's files (requires authentication)
- `GET /api/files/{file_id}` - Get file details (requires authentication)
- `GET /api/files/{file_id}/download` - Download file (requires authentication)

## Configuration

### Backend Environment Variables

See `backend/.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key
- `MINIO_ENDPOINT` - MinIO server endpoint
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `S3_BUCKET` - S3 bucket name
- `MAX_FILE_SIZE_MB` - Maximum file upload size (default: 100MB)

### Frontend Environment Variables

See `frontend/.env.example` for configuration options.

- `VITE_API_BASE_URL` - Backend API URL

## Troubleshooting

### MinIO Connection Issues

If you see MinIO connection errors, ensure:
1. MinIO container is running: `docker ps | grep minio`
2. MinIO bucket exists (create via console at http://localhost:9001)
3. MinIO credentials match in docker-compose.yml and backend .env

### Database Migration Issues

If migrations fail:
```bash
docker exec -it hybrid-storage-backend alembic upgrade head
```

### View Container Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

## License

MIT
