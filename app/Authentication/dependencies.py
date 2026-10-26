from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from gotrue.types import User

from app.common.db.supabase_client import get_supabase_client
from app.Authentication.services.supabase_auth_service import (
    InvalidAccessTokenError,
    SupabaseAuthService,
    SupabaseAuthUnavailableError,
)


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user: User
    access_token: str


@lru_cache(maxsize=1)
def get_supabase_auth_service() -> SupabaseAuthService:
    return SupabaseAuthService(get_supabase_client())


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = get_supabase_auth_service().get_user_from_access_token(
            credentials.credentials
        )
    except InvalidAccessTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except SupabaseAuthUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider is unavailable",
        ) from exc

    return AuthenticatedUser(user, credentials.credentials)
