# Authentication

This package verifies Supabase access tokens without decoding or trusting JWT
claims locally. The request's bearer token is passed to Supabase Auth, which
returns the authenticated user only when the token is valid.

## Layers

- `controllers/auth_controller.py`: FastAPI `GET /auth/verify` route and HTTP
  status mapping.
- `services/supabase_auth_service.py`: token verification through Supabase Auth.
- `dependencies.py`: cached Supabase client and service construction.
- `config.py`: reads and validates the Supabase URL and anon/publishable key.
- `schemas/auth_schemas.py`: response shape.

Copy `.env.example` to `.env` in this directory and replace both placeholders.
Alternatively, provide `SUPABASE_URL` and `SUPABASE_ANON_KEY` in the process
environment. Do not use a Supabase `service_role` key for token verification.

Include the router in the application's FastAPI instance:

```python
from app.Authentication import router as authentication_router

app.include_router(authentication_router)
```

Send `Authorization: Bearer <supabase-access-token>` to `GET /auth/verify`.
A valid token returns `valid`, the Supabase user ID, and email. Missing or
invalid tokens return `401`; Supabase availability errors return `503`.
