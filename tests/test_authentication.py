import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from gotrue.errors import AuthApiError

from app.Authentication.controllers import auth_controller
from app.Authentication.services.supabase_auth_service import (
    InvalidCredentialsError,
    InvalidAccessTokenError,
    InvalidRefreshTokenError,
    SupabaseAuthService,
    SupabaseAuthUnavailableError,
)


class SupabaseAuthServiceTests(unittest.TestCase):
    def test_sign_in_returns_supabase_auth_response(self) -> None:
        auth_response = object()
        client = Mock()
        client.auth.sign_in_with_password.return_value = auth_response

        result = SupabaseAuthService(client).sign_in_with_password(
            "user@example.com",
            "correct-password",
        )

        self.assertIs(result, auth_response)
        client.auth.sign_in_with_password.assert_called_once_with(
            {"email": "user@example.com", "password": "correct-password"}
        )

    def test_invalid_sign_in_credentials_are_reported(self) -> None:
        client = Mock()
        client.auth.sign_in_with_password.side_effect = AuthApiError(
            "invalid credentials", 400, None
        )

        with self.assertRaises(InvalidCredentialsError):
            SupabaseAuthService(client).sign_in_with_password(
                "user@example.com",
                "wrong-password",
            )

    def test_sign_in_provider_failure_is_reported(self) -> None:
        client = Mock()
        client.auth.sign_in_with_password.side_effect = AuthApiError(
            "provider error", 500, None
        )

        with self.assertRaises(SupabaseAuthUnavailableError):
            SupabaseAuthService(client).sign_in_with_password(
                "user@example.com",
                "correct-password",
            )

    def test_refresh_session_uses_refresh_token(self) -> None:
        auth_response = object()
        client = Mock()
        client.auth.refresh_session.return_value = auth_response

        result = SupabaseAuthService(client).refresh_session("refresh-token")

        self.assertIs(result, auth_response)
        client.auth.refresh_session.assert_called_once_with("refresh-token")

    def test_invalid_refresh_token_is_reported(self) -> None:
        client = Mock()
        client.auth.refresh_session.side_effect = AuthApiError(
            "invalid refresh token", 400, None
        )

        with self.assertRaises(InvalidRefreshTokenError):
            SupabaseAuthService(client).refresh_session("expired-refresh-token")

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

    def test_sign_in_returns_tokens_and_user(self) -> None:
        service = Mock()
        service.sign_in_with_password.return_value = SimpleNamespace(
            user=SimpleNamespace(id="user-123", email="user@example.com"),
            session=SimpleNamespace(
                access_token="access-token",
                refresh_token="refresh-token",
                token_type="bearer",
                expires_in=3600,
            ),
        )
        with patch.object(
            auth_controller, "get_supabase_auth_service", return_value=service
        ):
            response = self.client.post(
                "/auth/sign-in",
                json={"email": "user@example.com", "password": "correct-password"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "token_type": "bearer",
                "expires_in": 3600,
                "user_id": "user-123",
                "email": "user@example.com",
            },
        )
        service.sign_in_with_password.assert_called_once_with(
            "user@example.com",
            "correct-password",
        )

    def test_sign_in_invalid_credentials_returns_401(self) -> None:
        service = Mock()
        service.sign_in_with_password.side_effect = InvalidCredentialsError
        with patch.object(
            auth_controller, "get_supabase_auth_service", return_value=service
        ):
            response = self.client.post(
                "/auth/sign-in",
                json={"email": "user@example.com", "password": "wrong-password"},
            )

        self.assertEqual(response.status_code, 401)

    def test_sign_in_provider_failure_returns_503(self) -> None:
        service = Mock()
        service.sign_in_with_password.side_effect = SupabaseAuthUnavailableError
        with patch.object(
            auth_controller, "get_supabase_auth_service", return_value=service
        ):
            response = self.client.post(
                "/auth/sign-in",
                json={"email": "user@example.com", "password": "password"},
            )

        self.assertEqual(response.status_code, 503)

    def test_refresh_returns_replacement_tokens(self) -> None:
        service = Mock()
        service.refresh_session.return_value = SimpleNamespace(
            user=SimpleNamespace(id="user-123", email="user@example.com"),
            session=SimpleNamespace(
                access_token="new-access-token",
                refresh_token="new-refresh-token",
                token_type="bearer",
                expires_in=3600,
            ),
        )
        with patch.object(
            auth_controller, "get_supabase_auth_service", return_value=service
        ):
            response = self.client.post(
                "/auth/refresh",
                json={"refresh_token": "old-refresh-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["access_token"], "new-access-token")
        self.assertEqual(response.json()["refresh_token"], "new-refresh-token")
        service.refresh_session.assert_called_once_with("old-refresh-token")

    def test_refresh_rejects_invalid_refresh_token(self) -> None:
        service = Mock()
        service.refresh_session.side_effect = InvalidRefreshTokenError
        with patch.object(
            auth_controller, "get_supabase_auth_service", return_value=service
        ):
            response = self.client.post(
                "/auth/refresh",
                json={"refresh_token": "expired-refresh-token"},
            )

        self.assertEqual(response.status_code, 401)

    def test_sign_in_rejects_empty_credentials(self) -> None:
        with patch.object(
            auth_controller, "get_supabase_auth_service"
        ) as service_factory:
            response = self.client.post(
                "/auth/sign-in",
                json={"email": "", "password": ""},
            )

        self.assertEqual(response.status_code, 422)
        service_factory.assert_not_called()

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
