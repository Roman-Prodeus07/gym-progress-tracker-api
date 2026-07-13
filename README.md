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
- JWT access-token authentication
- Configurable token expiration, issuer, and audience validation
- OAuth2 password flow integrated with Swagger UI
- Protected current-user endpoint
- Consistent `401 Unauthorized` responses with Bearer authentication headers
- Timing-attack mitigation for unknown login emails

## Technology stack

- Python 3.13
- FastAPI
- PostgreSQL 18
- SQLAlchemy 2
- Alembic
- Psycopg 3
- Pydantic Settings
- PyJWT
- pwdlib with Argon2
- Docker and Docker Compose
- pytest
- Ruff

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
│   │   ├── dependencies/
│   │   │   └── auth.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── health.py
│   │   │   └── users.py
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
│   │   ├── common.py
│   │   ├── token.py
│   │   └── user.py
│   ├── services/
│   │   ├── auth.py
│   │   └── user.py
│   └── main.py
├── tests/
│   ├── test_auth.py
│   ├── test_auth_dependencies.py
│   ├── test_auth_service.py
│   ├── test_health.py
│   ├── test_jwt.py
│   ├── test_login.py
│   ├── test_security.py
│   ├── test_token_schemas.py
│   ├── test_user_schemas.py
│   └── test_users.py
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

Generate a development JWT secret:

```bash
openssl rand -hex 32
```

Copy the generated value into `JWT_SECRET_KEY` in `.env`.

The values in `.env.example` are intended only for local development. Never
commit the real `.env` file or reuse a development secret in production.

### 2. Build and start the services

```bash
docker compose up --build -d
```

### 3. Apply database migrations

```bash
docker compose exec api alembic upgrade head
```

### 4. Check service status

```bash
docker compose ps
```

### 5. Open the API

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI schema: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>
- Readiness: <http://localhost:8000/health/ready>

### 6. Stop the services

```bash
docker compose down
```

The PostgreSQL data remains stored in the named Docker volume.

## Authentication configuration

| Variable                          | Description                           | Default                    |
| --------------------------------- | ------------------------------------- | -------------------------- |
| `JWT_SECRET_KEY`                  | Secret used to sign access tokens     | Required, minimum 32 chars |
| `JWT_ALGORITHM`                   | Allowed JWT signing algorithm         | `HS256`                    |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime in minutes      | `30`                       |
| `JWT_ISSUER`                      | Expected token issuer                 | `gym-progress-tracker-api` |
| `JWT_AUDIENCE`                    | Expected token audience               | `gym-progress-tracker-api` |

Changing `JWT_SECRET_KEY` invalidates every access token signed with the
previous secret.

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

Start PostgreSQL in Docker:

```bash
docker compose up -d db
```

Apply database migrations:

```bash
alembic upgrade head
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

| Method | Endpoint         | Authentication | Description                       |
| ------ | ---------------- | -------------- | --------------------------------- |
| GET    | `/health`        | Public         | Checks whether the API is running |
| GET    | `/health/ready`  | Public         | Checks API and database readiness |
| POST   | `/auth/register` | Public         | Registers a new user              |
| POST   | `/auth/login`    | Public         | Issues a JWT access token         |
| GET    | `/users/me`      | Bearer token   | Returns the authenticated user    |

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
  "created_at": "2026-07-13T20:00:00Z",
  "updated_at": "2026-07-13T20:00:00Z"
}
```

Possible responses:

| Status | Meaning                               |
| ------ | ------------------------------------- |
| `201`  | User created                          |
| `409`  | A user with this email already exists |
| `422`  | Email or password validation failed   |

## Log in

The login endpoint follows the OAuth2 password form contract. The standard
`username` field is interpreted as the user's email address.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=user@example.com" \
  --data-urlencode "password=StrongPassword-2026!"
```

Successful response:

```json
{
  "access_token": "<signed-jwt-access-token>",
  "token_type": "bearer"
}
```

Access tokens expire after 30 minutes by default. Each token contains the
following claims:

- `sub`: UUID of the authenticated user
- `type`: token type, currently `access`
- `iat`: token creation time
- `exp`: token expiration time
- `iss`: token issuer
- `aud`: intended token audience

The API validates the token signature, algorithm, type, expiration, issuer,
audience, and subject before granting access.

Possible responses:

| Status | Meaning                           |
| ------ | --------------------------------- |
| `200`  | Login successful and token issued |
| `401`  | Email or password is incorrect    |
| `422`  | OAuth2 form validation failed     |

## Get the authenticated user

Replace `<access-token>` with the token returned by `/auth/login`:

```bash
curl http://localhost:8000/users/me \
  -H "Authorization: Bearer <access-token>"
```

Successful response:

```json
{
  "id": "0d01fbce-6fc7-49e9-929c-87c732b924a6",
  "email": "user@example.com",
  "created_at": "2026-07-13T20:00:00Z",
  "updated_at": "2026-07-13T20:00:00Z"
}
```

The API never returns plaintext passwords, password hashes, JWT secrets, or
other authentication credentials.

Possible responses:

| Status | Meaning                                      |
| ------ | -------------------------------------------- |
| `200`  | Authenticated user returned                  |
| `401`  | Token is missing, invalid, expired, or stale |

The complete authentication flow can also be tested using the **Authorize**
button in Swagger UI at <http://localhost:8000/docs>.

## Security decisions

- Passwords are hashed with Argon2id and never stored in plaintext.
- Password hashing and verification run outside the asynchronous event loop.
- Unknown emails use dummy password verification to reduce timing differences.
- JWT algorithms are explicitly allow-listed during token validation.
- Token expiration, issuer, audience, type, and subject are validated.
- Authentication failures return consistent `401 Unauthorized` responses.
- Protected responses use explicit schemas that exclude password hashes.
- Real secrets are loaded from environment variables and excluded from Git.

## Roadmap

- Refresh-token rotation and logout/revocation
- Exercise catalogue
- Workout and set tracking
- Body measurements and progress analytics
- Dedicated PostgreSQL integration test suite
- GitHub Actions CI pipeline
- Production deployment

## Project status

Sprint 3: JWT login and protected user routes.
