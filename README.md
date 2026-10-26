# Authentication

This package signs users in with Supabase Auth and verifies Supabase access
tokens without decoding or trusting JWT claims locally.

## Layers

- `controllers/auth_controller.py`: FastAPI sign-in and token verification
  routes and HTTP status mapping.
- `services/supabase_auth_service.py`: password sign-in and token verification
  through Supabase Auth.
- `dependencies.py`: cached Supabase client and service construction.
- `config.py`: reads and validates the Supabase URL and publishable key.
- `schemas/auth_schemas.py`: request and response shapes.

Set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` in `app/.env` or in the
process environment. Do not use a Supabase `service_role` key for user sign-in
or token verification.

Include the router in the application's FastAPI instance:

```python
from app.Authentication import router as authentication_router

app.include_router(authentication_router)
```

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

Use `GET /me/farms` with the same bearer token to retrieve the authenticated
user's active `farm_membership` rows, ordered by `joined_at`. The farm
membership flow uses separate controller, service, and data-access classes.
The repository query filters by the verified user's ID so it does not return
other members of their farms.
