import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.Authentication.dependencies import AuthenticatedUser, get_authenticated_user
from app.IdentityAndAccess.dto.profile_schema import ProfileResponse
from app.IdentityAndAccess.dto.user_preferences_schema import (
    UserPreferencesResponse,
    UserViewResponse,
)
from app.IdentityAndAccess.router.profile_router import router
from app.IdentityAndAccess.services.user_preferences_service import (
    UserPreferencesAlreadyExistsError,
    UserPreferencesNotFoundError,
    UserPreferencesService,
)
from app.IdentityAndAccess.services.user_view_service import UserViewService
from app.IdentityAndAccess.utils.user_preferences_dependencies import (
    get_user_preferences_service,
    get_user_view_service,
)


def preferences_row(user_id):
    return {
        "user_id": str(user_id),
        "language_code": "fil",
        "timezone": "Asia/Manila",
        "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
    }


def profile_row(user_id):
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    return {
        "user_id": str(user_id),
        "first_name": "Alex",
        "middle_name": None,
        "last_name": "Rivera",
        "suffix": None,
        "birth_date": None,
        "gender": None,
        "profile_photo_path": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


class UserPreferencesControllerTests(unittest.TestCase):
    def setUp(self):
        self.user_id = uuid4()
        self.preferences_service = Mock(spec=UserPreferencesService)
        self.user_view_service = Mock(spec=UserViewService)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_authenticated_user] = lambda: AuthenticatedUser(
            SimpleNamespace(id=self.user_id),
            "access-token",
        )
        app.dependency_overrides[get_user_preferences_service] = (
            lambda: self.preferences_service
        )
        app.dependency_overrides[get_user_view_service] = (
            lambda: self.user_view_service
        )
        self.client = TestClient(app)

    def tearDown(self):
        self.client.app.dependency_overrides.clear()

    def test_create_preferences_uses_authenticated_user(self):
        self.preferences_service.create_user_preferences.return_value = (
            UserPreferencesResponse.model_validate(
                preferences_row(self.user_id)
            )
        )

        response = self.client.post(
            "/me/preferences",
            json={"language_code": "en", "timezone": "UTC"},
        )

        self.assertEqual(response.status_code, 201)
        self.preferences_service.create_user_preferences.assert_called_once()
        self.assertEqual(
            self.preferences_service.create_user_preferences.call_args.args[1],
            self.user_id,
        )

    def test_create_preferences_returns_conflict_if_already_created(self):
        self.preferences_service.create_user_preferences.side_effect = (
            UserPreferencesAlreadyExistsError
        )

        response = self.client.post("/me/preferences", json={})

        self.assertEqual(response.status_code, 409)

    def test_get_preferences_returns_404_when_missing(self):
        self.preferences_service.get_user_preferences.side_effect = (
            UserPreferencesNotFoundError
        )

        response = self.client.get("/me/preferences")

        self.assertEqual(response.status_code, 404)

    def test_update_preferences_returns_updated_data(self):
        self.preferences_service.update_user_preferences.return_value = (
            UserPreferencesResponse.model_validate(
                {**preferences_row(self.user_id), "language_code": "en"}
            )
        )

        response = self.client.patch(
            "/me/preferences",
            json={"language_code": "en"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["language_code"], "en")
        self.assertEqual(
            self.preferences_service.update_user_preferences.call_args.args[1],
            self.user_id,
        )

    def test_get_user_view_returns_profile_and_preferences(self):
        self.user_view_service.get_user_view.return_value = (
            UserViewResponse(
                profile=ProfileResponse.model_validate(profile_row(self.user_id)),
                user_preferences=UserPreferencesResponse.model_validate(
                    preferences_row(self.user_id)
                ),
            )
        )

        response = self.client.get("/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profile"]["user_id"], str(self.user_id))
        self.assertEqual(
            response.json()["user_preferences"]["user_id"],
            str(self.user_id),
        )
        self.user_view_service.get_user_view.assert_called_once_with(self.user_id)


if __name__ == "__main__":
    unittest.main()
