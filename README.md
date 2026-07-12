# Gym Progress Tracker API

A production-oriented REST API for tracking gym workouts, exercises, body
measurements, and fitness progress.

The project is being developed as a portfolio backend application using
professional architecture, testing, database migrations, containerisation,
and deployment practices.

## Current features

- FastAPI application with modular routing
- Liveness and database readiness endpoints
- Asynchronous SQLAlchemy database layer
- PostgreSQL integration through Psycopg
- Alembic migration infrastructure
- Dockerised API and PostgreSQL services
- Automated tests with pytest
- Linting and formatting with Ruff
- Automatic Swagger and OpenAPI documentation
- Environment-based configuration
- User registration with email normalization
- UUID-based user identities
- Secure Argon2id password hashing
- Duplicate email handling
- Safe response schemas that exclude password hashes

## Technology stack

- Python 3.13
- FastAPI
- PostgreSQL 18
- SQLAlchemy 2
- Alembic
- Psycopg 3
- Pydantic Settings
- Docker and Docker Compose
- pytest
- Ruff
- pwdlib with Argon2

## Project structure

```text
.
├── alembic/
│   ├── versions/
│   │   └── <revision>_create_users_table.py
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   └── health.py
│   │   └── router.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── mixins.py
│   │   └── user.py
│   ├── schemas/
│   │   └── user.py
│   ├── services/
│   │   └── user.py
│   └── main.py
├── tests/
│   ├── test_auth.py
│   ├── test_health.py
│   ├── test_security.py
│   └── test_user_schemas.py
├── .env.example
├── alembic.ini
├── compose.yaml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Running with Docker

### 1. Create the environment file

```bash
cp .env.example .env
```

The values in `.env.example` are intended only for local development.

### 2. Build and start the services

```bash
docker compose up --build -d
```

### 3. Check service status

```bash
docker compose ps
```

### 4. Open the API

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI schema: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>
- Readiness: <http://localhost:8000/health/ready>

### 5. Stop the services

```bash
docker compose down
```

The PostgreSQL data remains stored in the named Docker volume.

## Local development

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the application and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Start only PostgreSQL in Docker:

```bash
docker compose up -d db
```

Run FastAPI locally:

```bash
fastapi dev app/main.py
```

## Code quality

Format the code:

```bash
ruff format .
```

Run the linter:

```bash
ruff check .
```

Run the tests:

```bash
pytest
```

## Database migrations

Check the current migration revision:

```bash
alembic current
```

Check whether the models contain uncommitted schema changes:

```bash
alembic check
```

Create a migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe schema change"
```

Apply migrations:

```bash
alembic upgrade head
```

## API endpoints

| Method | Endpoint         | Description                         |
| ------ | ---------------- | ----------------------------------- |
| GET    | `/health`        | Checks whether the API is running   |
| GET    | `/health/ready`  | Checks API and database readiness   |
| POST   | `/auth/register` | Registers a new user                |

## Register a user

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "StrongPassword-2026!"
  }'
```

Successful response:

```json
{
  "id": "0d01fbce-6fc7-49e9-929c-87c732b924a6",
  "email": "user@example.com",
  "created_at": "2026-07-12T13:00:00Z",
  "updated_at": "2026-07-12T13:00:00Z"
}
```

The API never returns plaintext passwords or stored password hashes.

Possible responses:

| Status | Meaning                                      |
| ------ | -------------------------------------------- |
| `201`  | User created                                 |
| `409`  | A user with this email already exists     |
| `422`  | Email or password validation failed          |

## Roadmap

- JWT login, access tokens, and refresh tokens
- Exercise catalogue
- Workout and set tracking
- Body measurements and progress analytics
- Unit and integration test suites
- GitHub Actions CI pipeline
- Production deployment

## Project status

Sprint 2: user persistence and registration.
