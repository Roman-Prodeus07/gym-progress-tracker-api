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
- Protected, paginated, read-only exercise catalogue
- Idempotent seeding of 20 baseline catalogue exercises
- Owner-scoped workout exercise CRUD with automatic position assignment
- Nested workout set CRUD with automatic set-number assignment
- Conflict handling for duplicate exercise positions and set numbers
- Offset pagination for workout, exercise, and set collections
- Protection against cross-user workout, workout exercise, and workout set access
- Async-safe eager loading of nested exercise response data
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
│   │   │   ├── exercises.py
│   │   │   ├── health.py
│   │   │   ├── users.py
│   │   │   ├── workout_exercises.py
│   │   │   ├── workout_sets.py
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
│   │   ├── exercise.py
│   │   ├── token.py
│   │   ├── user.py
│   │   ├── workout.py
│   │   ├── workout_exercise.py
│   │   └── workout_set.py
│   ├── scripts/
│   │   ├── __init__.py
│   │   └── seed_exercises.py
│   ├── services/
│   │   ├── auth.py
│   │   ├── exercise.py
│   │   ├── exercise_seed.py
│   │   ├── user.py
│   │   ├── workout.py
│   │   ├── workout_exercise.py
│   │   └── workout_set.py
│   └── main.py
├── tests/
│   ├── test_auth.py
│   ├── test_auth_dependencies.py
│   ├── test_auth_service.py
│   ├── test_exercise_schemas.py
│   ├── test_exercise_seed_service.py
│   ├── test_exercise_service.py
│   ├── test_exercises.py
│   ├── test_health.py
│   ├── test_jwt.py
│   ├── test_login.py
│   ├── test_security.py
│   ├── test_token_schemas.py
│   ├── test_user_schemas.py
│   ├── test_users.py
│   ├── test_workout_exercise_schemas.py
│   ├── test_workout_exercise_service.py
│   ├── test_workout_exercises.py
│   ├── test_workout_schemas.py
│   ├── test_workout_service.py
│   ├── test_workout_set_schemas.py
│   ├── test_workout_set_service.py
│   ├── test_workout_sets.py
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

### 4. Seed the exercise catalogue

```bash
docker compose exec api python -m app.scripts.seed_exercises
```

The seed command is idempotent. It inserts any missing baseline exercises and
can be run repeatedly without creating duplicate catalogue entries.

### 5. Check service status

```bash
docker compose ps
```

### 6. Open the API

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI schema: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>
- Readiness: <http://localhost:8000/health/ready>

### 7. Stop the services

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

Seed the exercise catalogue:

```bash
python -m app.scripts.seed_exercises
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

The current validation baseline is 186 passing automated tests. The complete
authenticated workout-recording flow has also been verified end to end against
the Dockerised API and a real PostgreSQL database.

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

| Method | Endpoint                                                                                     | Authentication | Description                         |
| ------ | -------------------------------------------------------------------------------------------- | -------------- | ----------------------------------- |
| GET    | `/health`                                                                                    | Public         | Checks whether the API is running   |
| GET    | `/health/ready`                                                                              | Public         | Checks API and database readiness   |
| POST   | `/auth/register`                                                                             | Public         | Registers a new user                |
| POST   | `/auth/login`                                                                                | Public         | Issues a JWT access token           |
| GET    | `/users/me`                                                                                  | Bearer token   | Returns the authenticated user      |
| GET    | `/exercises`                                                                                 | Bearer token   | Lists active catalogue exercises    |
| GET    | `/exercises/{exercise_id}`                                                                   | Bearer token   | Returns an active exercise          |
| POST   | `/workouts`                                                                                  | Bearer token   | Creates a workout session           |
| GET    | `/workouts`                                                                                  | Bearer token   | Lists the current user's workouts   |
| GET    | `/workouts/{workout_id}`                                                                     | Bearer token   | Returns an owned workout session    |
| PATCH  | `/workouts/{workout_id}`                                                                     | Bearer token   | Partially updates an owned workout  |
| DELETE | `/workouts/{workout_id}`                                                                     | Bearer token   | Deletes an owned workout session    |
| POST   | `/workouts/{workout_id}/exercises`                                                           | Bearer token   | Adds an exercise to a workout       |
| GET    | `/workouts/{workout_id}/exercises`                                                           | Bearer token   | Lists exercises in a workout        |
| GET    | `/workouts/{workout_id}/exercises/{workout_exercise_id}`                                     | Bearer token   | Returns a workout exercise          |
| PATCH  | `/workouts/{workout_id}/exercises/{workout_exercise_id}`                                     | Bearer token   | Updates a workout exercise          |
| DELETE | `/workouts/{workout_id}/exercises/{workout_exercise_id}`                                     | Bearer token   | Removes an exercise from a workout  |
| POST   | `/workouts/{workout_id}/exercises/{workout_exercise_id}/sets`                                | Bearer token   | Adds a set to a workout exercise    |
| GET    | `/workouts/{workout_id}/exercises/{workout_exercise_id}/sets`                                | Bearer token   | Lists workout sets                  |
| GET    | `/workouts/{workout_id}/exercises/{workout_exercise_id}/sets/{workout_set_id}`               | Bearer token   | Returns a workout set               |
| PATCH  | `/workouts/{workout_id}/exercises/{workout_exercise_id}/sets/{workout_set_id}`               | Bearer token   | Updates a workout set               |
| DELETE | `/workouts/{workout_id}/exercises/{workout_exercise_id}/sets/{workout_set_id}`               | Bearer token   | Deletes a workout set               |

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

| Status | Meaning                            |
| ------ | ---------------------------------- |
| `200`  | Login successful and token issued |
| `401`  | Email or password is incorrect     |
| `422`  | OAuth2 form validation failed      |

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

Deleting a workout session cascades to its workout exercises and sets. Deleting
a workout exercise cascades to its sets. The referenced catalogue exercises
remain available for other workouts.

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

## Exercise catalogue

All exercise catalogue endpoints require a Bearer access token. The catalogue
is read-only through the API and returns only active exercises.

Seed the 20 baseline exercises before using the catalogue:

```bash
docker compose exec api python -m app.scripts.seed_exercises
```

### List catalogue exercises

```bash
curl "http://localhost:8000/exercises?limit=20&offset=0" \
  -H "Authorization: Bearer <access-token>"
```

Successful response:

```json
{
  "items": [
    {
      "id": "ae0ce5b7-4bea-4618-951a-15401a632b25",
      "name": "Barbell Back Squat",
      "slug": "barbell-back-squat",
      "description": "Compound squat for the quadriceps and glutes.",
      "primary_muscle_group": "quadriceps",
      "equipment": "barbell",
      "created_at": "2026-07-28T10:00:00Z",
      "updated_at": "2026-07-28T10:00:00Z"
    }
  ],
  "total": 20,
  "limit": 20,
  "offset": 0
}
```

### Get a catalogue exercise

```bash
curl http://localhost:8000/exercises/<exercise-id> \
  -H "Authorization: Bearer <access-token>"
```

`limit` must be between `1` and `100`. `offset` must be zero or greater.

Possible responses:

| Status | Meaning                                       |
| ------ | --------------------------------------------- |
| `200`  | Active exercise returned or catalogue listed |
| `401`  | Authentication is missing or invalid         |
| `404`  | Active exercise was not found                 |
| `422`  | UUID or pagination validation failed          |

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

| Status | Meaning                                         |
| ------ | ----------------------------------------------- |
| `200`  | Workout returned, listed, or updated            |
| `201`  | Workout created                                 |
| `204`  | Workout deleted                                 |
| `401`  | Authentication is missing or invalid            |
| `404`  | Workout is missing or belongs to another user   |
| `422`  | Request validation or workout time range failed |

## Workout exercises

Workout exercises are nested under an owned workout session. Every response
includes both `exercise_id` and the nested catalogue exercise so clients do not
need an additional lookup to display exercise details.

### Add an exercise to a workout

```bash
curl -X POST http://localhost:8000/workouts/<workout-id>/exercises \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "exercise_id": "<exercise-id>",
    "rest_seconds": 90,
    "notes": "Controlled tempo"
  }'
```

Successful response:

```json
{
  "id": "a6fd8904-54dd-4799-a3ae-a23407e07579",
  "exercise_id": "ae0ce5b7-4bea-4618-951a-15401a632b25",
  "exercise": {
    "id": "ae0ce5b7-4bea-4618-951a-15401a632b25",
    "name": "Barbell Back Squat",
    "slug": "barbell-back-squat",
    "description": "Compound squat for the quadriceps and glutes.",
    "primary_muscle_group": "quadriceps",
    "equipment": "barbell",
    "created_at": "2026-07-28T10:00:00Z",
    "updated_at": "2026-07-28T10:00:00Z"
  },
  "position": 1,
  "rest_seconds": 90,
  "notes": "Controlled tempo",
  "created_at": "2026-07-28T10:05:00Z",
  "updated_at": "2026-07-28T10:05:00Z"
}
```

`position` is optional. When omitted, the service assigns
`max(existing position) + 1`. An explicitly requested position that is already
used within the workout returns `409 Conflict`.

### List exercises in a workout

```bash
curl \
  "http://localhost:8000/workouts/<workout-id>/exercises?limit=20&offset=0" \
  -H "Authorization: Bearer <access-token>"
```

### Get, update, or remove a workout exercise

```bash
curl \
  http://localhost:8000/workouts/<workout-id>/exercises/<workout-exercise-id> \
  -H "Authorization: Bearer <access-token>"

curl -X PATCH \
  http://localhost:8000/workouts/<workout-id>/exercises/<workout-exercise-id> \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rest_seconds": 120,
    "notes": "Updated rest interval"
  }'

curl -X DELETE \
  http://localhost:8000/workouts/<workout-id>/exercises/<workout-exercise-id> \
  -H "Authorization: Bearer <access-token>"
```

Successful deletion returns `204 No Content`. Deleting a workout exercise also
deletes its workout sets through the database cascade.

Possible responses:

| Status | Meaning                                                   |
| ------ | --------------------------------------------------------- |
| `200`  | Workout exercise returned, listed, or updated             |
| `201`  | Workout exercise created                                  |
| `204`  | Workout exercise deleted                                  |
| `401`  | Authentication is missing or invalid                      |
| `404`  | Parent, exercise, or owned workout exercise was not found |
| `409`  | Position is already used within the workout               |
| `422`  | UUID, pagination, or request validation failed            |

## Workout sets

Workout sets are nested under an owned workout exercise and can record
strength, timed, or distance-based performance.

### Add a set to a workout exercise

```bash
curl -X POST \
  http://localhost:8000/workouts/<workout-id>/exercises/<workout-exercise-id>/sets \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "set_type": "working",
    "reps": 8,
    "weight_kg": 60.5,
    "rpe": 8.5,
    "notes": "Strong working set"
  }'
```

Successful response:

```json
{
  "id": "0b594aad-a8b4-4191-9a76-09e83f6841c7",
  "set_number": 1,
  "set_type": "working",
  "reps": 8,
  "weight_kg": "60.500",
  "duration_seconds": null,
  "distance_meters": null,
  "rpe": "8.5",
  "notes": "Strong working set",
  "created_at": "2026-07-28T10:10:00Z",
  "updated_at": "2026-07-28T10:10:00Z"
}
```

`set_number` is optional. When omitted, the service assigns
`max(existing set number) + 1`. An explicitly requested set number that is
already used within the workout exercise returns `409 Conflict`.

Every set requires at least one primary performance metric: `reps`,
`duration_seconds`, or `distance_meters`. `weight_kg`, `rpe`, and `notes` can
supplement those metrics but cannot create a valid set on their own.

Supported `set_type` values are:

- `warmup`
- `working`
- `drop`
- `failure`

### List sets

```bash
curl \
  "http://localhost:8000/workouts/<workout-id>/exercises/<workout-exercise-id>/sets?limit=20&offset=0" \
  -H "Authorization: Bearer <access-token>"
```

### Get, update, or delete a set

```bash
curl \
  http://localhost:8000/workouts/<workout-id>/exercises/<workout-exercise-id>/sets/<workout-set-id> \
  -H "Authorization: Bearer <access-token>"

curl -X PATCH \
  http://localhost:8000/workouts/<workout-id>/exercises/<workout-exercise-id>/sets/<workout-set-id> \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "reps": 9,
    "weight_kg": 62.5,
    "notes": "Progressive overload"
  }'

curl -X DELETE \
  http://localhost:8000/workouts/<workout-id>/exercises/<workout-exercise-id>/sets/<workout-set-id> \
  -H "Authorization: Bearer <access-token>"
```

Successful deletion returns `204 No Content`.

Possible responses:

| Status | Meaning                                                |
| ------ | ------------------------------------------------------ |
| `200`  | Workout set returned, listed, or updated               |
| `201`  | Workout set created                                    |
| `204`  | Workout set deleted                                    |
| `401`  | Authentication is missing or invalid                   |
| `404`  | Owned parent or workout set was not found              |
| `409`  | Set number is already used for the workout exercise    |
| `422`  | Request, metric, UUID, or pagination validation failed |

## Security decisions

- Passwords are hashed with Argon2id and never stored in plaintext.
- Password hashing and verification run outside the asynchronous event loop.
- Unknown emails use dummy password verification to reduce timing differences.
- JWT algorithms are explicitly allow-listed during token validation.
- Token expiration, issuer, audience, type, and subject are validated.
- Authentication failures return consistent `401 Unauthorized` responses.
- Workout ownership is enforced in database queries using both resource and
  authenticated-user UUIDs.
- Child resource queries join through the owned workout session instead of
  trusting client-supplied parent identifiers.
- Missing and foreign workout, workout exercise, and workout set UUIDs return
  the same `404 Not Found` responses.
- Protected responses use explicit schemas that exclude ownership and password
  data.
- Nested catalogue exercise data is eagerly loaded before async response
  serialization.
- Database constraints enforce training-domain invariants independently of the
  API validation layer.
- Child workout records are deleted through database cascades.
- Catalogue exercises are protected from accidental deletion while referenced.
- Real secrets are loaded from environment variables and excluded from Git.

## Roadmap

- Refresh-token rotation and logout/revocation
- Workout templates and reusable training plans
- Body measurements and progress analytics
- Automated PostgreSQL integration and E2E test suite
- GitHub Actions CI pipeline
- Production deployment

## Project status

Sprint 5: protected exercise catalogue, idempotent exercise seeding, and
owner-scoped workout exercise and workout set CRUD. The current baseline is
186 passing automated tests plus a successful full Docker/PostgreSQL E2E flow.
