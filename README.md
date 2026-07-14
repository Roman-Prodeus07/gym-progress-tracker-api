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
- Normalized training domain for workouts, exercises, and sets
- UUID primary keys and timezone-aware timestamps across training entities
- Database constraints for ordering, metrics, time ranges, and set types
- Owner-scoped workout session CRUD
- Offset pagination for workout session lists
- Protection against cross-user workout access
- Cascading deletion of workout details while preserving catalogue exercises

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
│   │   ├── <revision>_create_users_table.py
│   │   └── <revision>_create_training_domain_tables.py
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── api/
│   │   ├── dependencies/
│   │   │   └── auth.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── health.py
│   │   │   ├── users.py
│   │   │   └── workouts.py
│   │   └── router.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── exercise.py
│   │   ├── mixins.py
│   │   ├── user.py
│   │   ├── workout_exercise.py
│   │   ├── workout_session.py
│   │   └── workout_set.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── token.py
│   │   ├── user.py
│   │   └── workout.py
│   ├── services/
│   │   ├── auth.py
│   │   ├── user.py
│   │   └── workout.py
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
│   ├── test_users.py
│   ├── test_workout_schemas.py
│   ├── test_workout_service.py
│   └── test_workouts.py
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

| Variable                          | Description                       | Default                    |
| --------------------------------- | --------------------------------- | -------------------------- |
| `JWT_SECRET_KEY`                  | Secret used to sign access tokens | Required, minimum 32 chars |
| `JWT_ALGORITHM`                   | Allowed JWT signing algorithm     | `HS256`                    |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime in minutes  | `30`                       |
| `JWT_ISSUER`                      | Expected token issuer             | `gym-progress-tracker-api` |
| `JWT_AUDIENCE`                    | Expected token audience           | `gym-progress-tracker-api` |

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

| Method | Endpoint                 | Authentication | Description                        |
| ------ | ------------------------ | -------------- | ---------------------------------- |
| GET    | `/health`                | Public         | Checks whether the API is running  |
| GET    | `/health/ready`          | Public         | Checks API and database readiness  |
| POST   | `/auth/register`         | Public         | Registers a new user               |
| POST   | `/auth/login`            | Public         | Issues a JWT access token          |
| GET    | `/users/me`              | Bearer token   | Returns the authenticated user     |
| POST   | `/workouts`              | Bearer token   | Creates a workout session          |
| GET    | `/workouts`              | Bearer token   | Lists the current user's workouts  |
| GET    | `/workouts/{workout_id}` | Bearer token   | Returns an owned workout session   |
| PATCH  | `/workouts/{workout_id}` | Bearer token   | Partially updates an owned workout |
| DELETE | `/workouts/{workout_id}` | Bearer token   | Deletes an owned workout session   |

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
  "created_at": "2026-07-14T10:00:00Z",
  "updated_at": "2026-07-14T10:00:00Z"
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
  "created_at": "2026-07-14T10:00:00Z",
  "updated_at": "2026-07-14T10:00:00Z"
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

## Training domain design

The training domain uses four normalized entities:

- `Exercise` is a global catalogue entry.
- `WorkoutSession` is owned by exactly one user.
- `WorkoutExercise` places an exercise at an ordered position within a session.
- `WorkoutSet` records performance metrics for a workout exercise.

Ownership is stored on `WorkoutSession` and inherited by its child entities.
This avoids duplicating `user_id` across the hierarchy and prevents
inconsistent ownership data.

Deleting a workout session cascades to its workout exercises and sets. The
referenced catalogue exercises remain available for other workouts.

Database constraints enforce:

- workout completion cannot precede its start;
- exercise positions are positive and unique within a session;
- rest duration must be positive when provided;
- set numbers are positive and unique within a workout exercise;
- repetitions and weights cannot be negative;
- duration and distance must be positive when provided;
- RPE must be between `0` and `10`;
- each set must contain at least one performance metric;
- set types are restricted to supported values.

## Workout sessions

All workout endpoints require a Bearer access token.

### Create a workout

```bash
curl -X POST http://localhost:8000/workouts \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Push Day",
    "notes": "Chest, shoulders, and triceps"
  }'
```

Successful response:

```json
{
  "id": "afd236ca-fc58-403c-a2be-e4297e941bbe",
  "name": "Push Day",
  "notes": "Chest, shoulders, and triceps",
  "started_at": "2026-07-14T10:36:57Z",
  "completed_at": null,
  "created_at": "2026-07-14T10:36:57Z",
  "updated_at": "2026-07-14T10:36:57Z"
}
```

The authenticated user's UUID is taken from the validated JWT. Clients cannot
provide or override the workout owner.

### List workouts

```bash
curl "http://localhost:8000/workouts?limit=20&offset=0" \
  -H "Authorization: Bearer <access-token>"
```

Successful response:

```json
{
  "items": [
    {
      "id": "afd236ca-fc58-403c-a2be-e4297e941bbe",
      "name": "Push Day",
      "notes": "Chest, shoulders, and triceps",
      "started_at": "2026-07-14T10:36:57Z",
      "completed_at": null,
      "created_at": "2026-07-14T10:36:57Z",
      "updated_at": "2026-07-14T10:36:57Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

`limit` must be between `1` and `100`. `offset` must be zero or greater.

### Get a workout

```bash
curl http://localhost:8000/workouts/<workout-id> \
  -H "Authorization: Bearer <access-token>"
```

### Update a workout

Updates use PATCH semantics, so only supplied fields are changed.

```bash
curl -X PATCH http://localhost:8000/workouts/<workout-id> \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Push Day Completed",
    "completed_at": "2026-07-14T12:00:00Z"
  }'
```

`completed_at` cannot be earlier than `started_at`.

### Delete a workout

```bash
curl -X DELETE http://localhost:8000/workouts/<workout-id> \
  -H "Authorization: Bearer <access-token>"
```

Successful deletion returns `204 No Content`.

All workout queries are scoped to the authenticated user's UUID. Missing and
foreign workout identifiers both return `404 Not Found`, preventing resource
enumeration and cross-user access.

Possible responses:

| Status | Meaning                                           |
| ------ | ------------------------------------------------- |
| `200`  | Workout returned, listed, or updated              |
| `201`  | Workout created                                   |
| `204`  | Workout deleted                                   |
| `401`  | Authentication is missing or invalid              |
| `404`  | Workout is missing or belongs to another user     |
| `422`  | Request validation or workout time range failed   |

## Security decisions

- Passwords are hashed with Argon2id and never stored in plaintext.
- Password hashing and verification run outside the asynchronous event loop.
- Unknown emails use dummy password verification to reduce timing differences.
- JWT algorithms are explicitly allow-listed during token validation.
- Token expiration, issuer, audience, type, and subject are validated.
- Authentication failures return consistent `401 Unauthorized` responses.
- Workout ownership is enforced in database queries using both resource and
  authenticated-user UUIDs.
- Missing and foreign workout UUIDs return the same `404 Not Found` response.
- Protected responses use explicit schemas that exclude ownership and password
  data.
- Database constraints enforce training-domain invariants independently of the
  API validation layer.
- Child workout records are deleted through database cascades.
- Catalogue exercises are protected from accidental deletion while referenced.
- Real secrets are loaded from environment variables and excluded from Git.

## Roadmap

- Exercise catalogue API
- Workout exercise and set CRUD
- Refresh-token rotation and logout/revocation
- Workout templates and reusable training plans
- Body measurements and progress analytics
- Dedicated PostgreSQL integration test suite
- GitHub Actions CI pipeline
- Production deployment

## Project status

Sprint 4: training domain foundation and owner-scoped workout session CRUD.
