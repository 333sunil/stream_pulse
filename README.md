# StreamPulse

FastAPI service for uploading, storing, and streaming media files.

## Features
- Upload and store media files (local or S3-compatible storage)
- Search media by title
- Download media by ID
- Delete media by ID
- Async PostgreSQL with Alembic migrations

## Tech Stack
- FastAPI, SQLAlchemy (async), Alembic
- PostgreSQL, MinIO (S3-compatible)
- Docker, docker-compose

## Project Structure
- API entrypoint: [app/main.py](app/main.py)
- Media routes: [app/api/v1/media.py](app/api/v1/media.py)
- Media model: [app/models/media.py](app/models/media.py)
- Media schema: [app/schemas/media.py](app/schemas/media.py)
- Media repository: [app/crud/media.py](app/crud/media.py)
- Storage services: [app/utils/storage.py](app/utils/storage.py)
- DB config: [app/core/config.py](app/core/config.py)
- DB session: [app/db.py](app/db.py)
- Migrations: [migrations/env.py](migrations/env.py), [alembic.ini](alembic.ini)
- Settings: [config/settings.toml](config/settings.toml), [config/.secrets.toml](config/.secrets.toml)
- Docker: [Dockerfile](Dockerfile), [docker-compose.yaml](docker-compose.yaml)

## Setup

### 1) Install dependencies
```bash
pip install -r requirements-tests.txt
```

### 2) Configure settings
Edit [config/settings.toml](config/settings.toml) and [config/.secrets.toml](config/.secrets.toml) as needed.

### 3) Run PostgreSQL and MinIO (optional)
```bash
docker-compose up -d
```

### 4) Run migrations
```bash
alembic revision --autogenerate -m "<message>"
alembic upgrade head
```

### 5) Start the app
```bash
uvicorn app.main:app --reload
```


## API Endpoints
Base URL: `http://localhost:8000`

- `GET /health` — health check ([app/main.py](app/main.py))
- `GET /api/v1/media/search?title=...` — search media ([app/api/v1/media.py](app/api/v1/media.py))
- `POST /api/v1/media/upload` — upload file ([app/api/v1/media.py](app/api/v1/media.py))
- `GET /api/v1/media/info/{media_id}` — media info ([app/api/v1/media.py](app/api/v1/media.py))
- `GET /api/v1/media/download/{media_id}` — download file ([app/api/v1/media.py](app/api/v1/media.py))
- `DELETE /api/v1/media/delete/{media_id}` — delete media ([app/api/v1/media.py](app/api/v1/media.py))


## Storage
Storage is selected in [app/utils/storage.py](app/utils/storage.py):

- S3/MinIO if `ENDPOINT` is set in [config/settings.toml](config/settings.toml)
- Local filesystem otherwise (uses `MEDIA_PATH`)


## Notes
- Default Postgres settings are defined in [config/settings.toml](config/settings.toml).
- Credentials are stored in [config/.secrets.toml](config/.secrets.toml).