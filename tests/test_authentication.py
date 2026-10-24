import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from gotrue.errors import AuthApiError

from app.Authentication.controllers import auth_controller
from app.Authentication.services.supabase_auth_service import (
    InvalidAccessTokenError,
    SupabaseAuthService,
    SupabaseAuthUnavailableError,
)


class SupabaseAuthServiceTests(unittest.TestCase):
    def test_valid_token_returns_supabase_user(self) -> None:
        user = object()
        client = Mock()
        client.auth.get_user.return_value = SimpleNamespace(user=user)

        result = SupabaseAuthService(client).get_user_from_access_token("access-token")

        self.assertIs(result, user)
        client.auth.get_user.assert_called_once_with("access-token")

    def test_invalid_token_is_reported(self) -> None:
        client = Mock()
        client.auth.get_user.side_effect = AuthApiError("invalid token", 401, None)

        with self.assertRaises(InvalidAccessTokenError):
            SupabaseAuthService(client).get_user_from_access_token("bad-token")

    def test_provider_failure_is_reported(self) -> None:
        client = Mock()
        client.auth.get_user.side_effect = AuthApiError("provider error", 500, None)

        with self.assertRaises(SupabaseAuthUnavailableError):
            SupabaseAuthService(client).get_user_from_access_token("access-token")


class AuthenticationControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(auth_controller.router)
        self.client = TestClient(app)

    def test_missing_token_returns_401_without_initializing_supabase(self) -> None:
        with patch.object(auth_controller, "get_supabase_auth_service") as service_factory:
            response = self.client.get("/auth/verify")

        self.assertEqual(response.status_code, 401)
        service_factory.assert_not_called()

    def test_valid_token_returns_user_identity(self) -> None:
        service = Mock()
        service.get_user_from_access_token.return_value = SimpleNamespace(
            id="user-123",
            email="user@example.com",
        )
        with patch.object(
            auth_controller, "get_supabase_auth_service", return_value=service
        ):
            response = self.client.get(
                "/auth/verify",
                headers={"Authorization": "Bearer access-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"valid": True, "user_id": "user-123", "email": "user@example.com"},
        )
        service.get_user_from_access_token.assert_called_once_with("access-token")

    def test_invalid_token_returns_401(self) -> None:
        service = Mock()
        service.get_user_from_access_token.side_effect = InvalidAccessTokenError
        with patch.object(
            auth_controller, "get_supabase_auth_service", return_value=service
        ):
            response = self.client.get(
                "/auth/verify",
                headers={"Authorization": "Bearer bad-token"},
            )

        self.assertEqual(response.status_code, 401)

    def test_supabase_failure_returns_503(self) -> None:
        service = Mock()
        service.get_user_from_access_token.side_effect = SupabaseAuthUnavailableError
        with patch.object(
            auth_controller, "get_supabase_auth_service", return_value=service
        ):
            response = self.client.get(
                "/auth/verify",
                headers={"Authorization": "Bearer access-token"},
            )

        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
