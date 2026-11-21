import httpx
from gotrue.errors import AuthApiError, AuthError
from gotrue.types import AuthResponse, User
from supabase import Client


class InvalidCredentialsError(Exception):
    pass


class InvalidAccessTokenError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class SupabaseAuthUnavailableError(Exception):
    pass


class SupabaseAuthService:
    def __init__(self, client: Client) -> None:
        self._client = client

    def sign_in_with_password(self, email: str, password: str) -> AuthResponse:
        try:
            return self._client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except AuthApiError as exc:
            if exc.status in (400, 401, 403, 422):
                raise InvalidCredentialsError from exc
            raise SupabaseAuthUnavailableError from exc
        except (AuthError, httpx.HTTPError) as exc:
            raise SupabaseAuthUnavailableError from exc

    def refresh_session(self, refresh_token: str) -> AuthResponse:
        try:
            return self._client.auth.refresh_session(refresh_token)
        except AuthApiError as exc:
            if exc.status in (400, 401, 403):
                raise InvalidRefreshTokenError from exc
            raise SupabaseAuthUnavailableError from exc
        except (AuthError, httpx.HTTPError) as exc:
            raise SupabaseAuthUnavailableError from exc

    def get_user_from_access_token(self, access_token: str) -> User:
        try:
            response = self._client.auth.get_user(access_token)
        except AuthApiError as exc:
            if exc.status in (400, 401, 403):
                raise InvalidAccessTokenError from exc
            raise SupabaseAuthUnavailableError from exc
        except (AuthError, httpx.HTTPError) as exc:
            raise SupabaseAuthUnavailableError from exc

        if response is None:
            raise InvalidAccessTokenError
        return response.user
