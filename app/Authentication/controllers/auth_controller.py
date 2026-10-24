from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.Authentication.dependencies import get_supabase_auth_service
from app.Authentication.schemas.auth_schemas import TokenVerificationResponse
from app.Authentication.services.supabase_auth_service import (
    InvalidAccessTokenError,
    SupabaseAuthService,
    SupabaseAuthUnavailableError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.get("/verify", response_model=TokenVerificationResponse)
def verify_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TokenVerificationResponse:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer access token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        auth_service: SupabaseAuthService = get_supabase_auth_service()
        user = auth_service.get_user_from_access_token(credentials.credentials)
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

    return TokenVerificationResponse(user_id=user.id, email=user.email)
