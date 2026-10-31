import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.Authentication.dependencies import AuthenticatedUser, get_authenticated_user
from app.IdentityAndAccess.dao.profile_repository import (
    ProfileDataAccessError,
    ProfileRepository,
)
from app.IdentityAndAccess.dto.profile_schema import ProfileResponse
from app.IdentityAndAccess.router.profile_router import router
from app.IdentityAndAccess.services.profile_service import (
    ProfileNotFoundError,
    ProfileService,
    ProfileUnavailableError,
)
from app.IdentityAndAccess.utils.profile_dependencies import get_profile_service


def profile_row(user_id: UUID) -> dict[str, object]:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    return {
        "user_id": str(user_id),
        "first_name": "Ken",
        "middle_name": None,
        "last_name": "Example",
        "suffix": None,
        "birth_date": date(1990, 1, 1).isoformat(),
        "gender": None,
        "profile_photo_path": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


class ProfileRepositoryTests(unittest.TestCase):
    def test_get_by_user_id_filters_and_returns_profile(self) -> None:
        user_id = str(uuid4())
        profile = profile_row(UUID(user_id))
        query = Mock()
        query.select.return_value = query
        query.eq.return_value = query
        query.limit.return_value = query
        query.execute.return_value = SimpleNamespace(data=[profile])
        client = Mock()
        client.table.return_value = query

        result = ProfileRepository(client).get_by_user_id(user_id)

        self.assertEqual(result, profile)
        client.table.assert_called_once_with("profile")
        query.eq.assert_called_once_with("user_id", user_id)

    def test_database_failure_is_reported(self) -> None:
        query = Mock()
        query.select.return_value = query
        query.eq.return_value = query
        query.limit.return_value = query
        query.execute.side_effect = httpx.ConnectError("database unavailable")
        client = Mock()
        client.table.return_value = query

        with self.assertRaises(ProfileDataAccessError):
            ProfileRepository(client).get_by_user_id("user-123")


class ProfileServiceTests(unittest.TestCase):
    def test_get_profile_returns_profile_for_user(self) -> None:
        user_id = uuid4()
        repository = Mock(spec=ProfileRepository)
        repository.get_by_user_id.return_value = profile_row(user_id)

        result = ProfileService(repository).get_profile(user_id)

        self.assertEqual(result.user_id, user_id)
        repository.get_by_user_id.assert_called_once_with(str(user_id))

    def test_missing_profile_raises_not_found(self) -> None:
        repository = Mock(spec=ProfileRepository)
        repository.get_by_user_id.return_value = None

        with self.assertRaises(ProfileNotFoundError):
            ProfileService(repository).get_profile(uuid4())

    def test_repository_failure_raises_unavailable(self) -> None:
        repository = Mock(spec=ProfileRepository)
        repository.get_by_user_id.side_effect = ProfileDataAccessError

        with self.assertRaises(ProfileUnavailableError):
            ProfileService(repository).get_profile(uuid4())


class ProfileControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.service = Mock(spec=ProfileService)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_authenticated_user] = lambda: AuthenticatedUser(
            SimpleNamespace(id=self.user_id),
            "access-token",
        )
        app.dependency_overrides[get_profile_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.app.dependency_overrides.clear()

    def test_get_my_profile_returns_authenticated_users_profile(self) -> None:
        self.service.get_profile.return_value = ProfileResponse.model_validate(
            profile_row(self.user_id)
        )

        response = self.client.get("/me/profile")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], str(self.user_id))
        self.service.get_profile.assert_called_once_with(self.user_id)

    def test_missing_profile_returns_404(self) -> None:
        self.service.get_profile.side_effect = ProfileNotFoundError

        response = self.client.get("/me/profile")

        self.assertEqual(response.status_code, 404)

    def test_profile_service_failure_returns_503(self) -> None:
        self.service.get_profile.side_effect = ProfileUnavailableError

        response = self.client.get("/me/profile")

        self.assertEqual(response.status_code, 503)
