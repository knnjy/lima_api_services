import httpx
from gotrue.errors import AuthApiError, AuthError
from gotrue.types import User
from supabase import Client


class InvalidAccessTokenError(Exception):
    pass


class SupabaseAuthUnavailableError(Exception):
    pass


class SupabaseAuthService:
    def __init__(self, client: Client) -> None:
        self._client = client

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
