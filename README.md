# FastAPI Backend

A FastAPI backend application with JWT authentication, PostgreSQL database, and Docker setup.

## Features

- User authentication with JWT
- Full CRUD operations for users and documents
- PostgreSQL database with SQLAlchemy ORM
- Alembic migrations
- Docker and docker-compose for easy deployment
- Password hashing for security

## Database Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

## Getting Started

### Prerequisites

- Docker and docker-compose

### Installation

1. Clone the repository
2. Copy the `.env.example` file to `.env` and modify as needed
   ```bash
   cp .env.example .env
   ```
3. Start the containers with docker-compose
   ```bash
   docker-compose up -d
   ```
4. The API will be available at http://localhost:8000
5. API documentation is available at http://localhost:8000/docs

## API Endpoints

- **Authentication**

  - `POST /api/v1/auth/login` - Get JWT token

- **Users**

  - `POST /api/v1/users` - Create new user
  - `GET /api/v1/users/me` - Get current user
  - `PUT /api/v1/users/me` - Update current user
  - `GET /api/v1/users` - List all users (requires authentication)

- **Documents**
  - `GET /api/v1/documents` - List user's documents
  - `POST /api/v1/documents` - Create new document
  - `GET /api/v1/documents/{document_id}` - Get specific document
  - `PUT /api/v1/documents/{document_id}` - Update document
  - `DELETE /api/v1/documents/{document_id}` - Delete document

## Development

To work on the application locally:

1. Create a virtual environment

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (modify DATABASE_URL to point to your local PostgreSQL)

4. Run the application

   ```bash
   uvicorn app.main:app --reload
   ```

5. Run database migrations
   ```bash
   alembic upgrade head
   ```

## Creating Migrations

To create a new migration after changing models:

```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```
