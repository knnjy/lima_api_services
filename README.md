# LiMa: AI-based Livestock Management

LiMa is a FastAPI service organized by business feature, with each feature
separated into application layers.

## Tech Stack

- **Python** — programming language
- **FastAPI** — API framework
- **Supabase Auth** — authentication and access-token verification
- **Supabase** — application data storage
- **Uvicorn** — ASGI server
- **Pydantic** — request and response data validation
- **python-dotenv** — environment variable loading
- **HTTPX** — HTTP client

## Project Architecture

The application uses a feature-based layered architecture. Business features
own their controllers, services, data-access code, schemas, and feature-specific
dependencies. Shared infrastructure and cross-feature dependencies live under
`app/common`.

```text
app/
├── Authentication/
│   ├── controllers/       # Authentication HTTP routes
│   ├── schemas/           # Authentication request/response models
│   ├── services/          # Supabase Auth operations
│   └── dependencies.py    # Verified-user authentication dependency
├── LivestockRegistry/
│   ├── controllers/       # Farm and livestock HTTP handlers
│   ├── dao/               # Supabase data-access repositories
│   ├── dto/               # Request and response schemas
│   ├── router/            # Feature HTTP route registration
│   ├── services/          # Feature business logic
│   └── utils/             # Feature dependency providers
├── common/
│   ├── config.py          # Application settings
│   ├── db/                # Shared Supabase client setup
│   └── dependencies/      # Reusable cross-feature dependencies
└── main.py                # FastAPI app and router registration
```

### Layer responsibilities

- **Controllers** define HTTP routes, receive dependencies, and translate
  service errors into HTTP responses. They should not contain database queries.
- **Services** implement feature-level operations and coordinate with the
  data-access layer.
- **DAO/repositories** own database queries and translate database failures
  into data-access errors.
- **Dependencies** construct and provide services or reusable request context.
  Authentication verifies the bearer token first; the shared farm-access
  dependency then loads the verified user's active memberships.
- **Common** contains infrastructure and dependencies shared across feature
  modules. It should not become a home for feature-specific business logic.

For example, `GET /me/farms` is served by the LivestockRegistry controller,
which calls the membership service; that service delegates the
`farm_membership` query to its repository. The shared dependency in
`app/common/dependencies/farm_access.py` exposes an authenticated user together
with typed `{farm_id, role_id}` membership pairs for other protected endpoints.

## Configuration

Set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` in `app/.env` or in the
process environment. Do not use a Supabase `service_role` key for user sign-in
or token verification.

## Authentication API

The authentication router is registered by `app/main.py`.

Send `POST /auth/sign-in` with an email and password to sign in:

```json
{"email": "user@example.com", "password": "your-password"}
```

A successful response includes access and refresh tokens plus the user's ID
and email. Invalid credentials return `401`; Supabase availability errors
return `503`.

Send the access token in an `Authorization: Bearer` header to
`GET /auth/verify`. A valid token returns `valid`, the Supabase user ID, and
email. Missing or invalid tokens return `401`; Supabase availability errors
return `503`.

When an access token expires, send the saved refresh token to
`POST /auth/refresh`:

```json
{"refresh_token": "your-refresh-token"}
```

The response contains a new access token and refresh token. Replace both saved
tokens with the returned values. If the refresh token is expired or invalid,
the endpoint returns `401` and the user must sign in again.

## Farm Membership API

Use `GET /me/farms` with the same bearer token to retrieve the authenticated
user's active `farm_membership` rows, ordered by `joined_at`. The repository
filters by the verified user's ID and `status = "active"` so it returns only
that user's active memberships.

The shared authenticated farm context preserves each farm and role as a pair;
it does not combine them into separate ID lists, which would lose the
farm-to-role association.

## Farm API

Farm CRUD uses `GET /farms` and `POST /farms`, plus
`GET /farms/{farm_id}`, `PATCH /farms/{farm_id}`, and
`DELETE /farms/{farm_id}`. These routes require authentication and operate only
on farms where the user has an active membership. Creating a farm assigns the
authenticated user as its creator and creates an owner membership. Only an
owner (`role_id = 1`) may update or delete a farm; workers receive `403` for
those operations.
