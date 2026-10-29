import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.Authentication.dependencies import AuthenticatedUser, get_authenticated_user
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    FarmRoleMembership,
    get_authenticated_farm_user,
)
from app.LivestockRegistry.controllers.farm_controllers import router

from app.LivestockRegistry.dao.farm_membership_repository import FarmMembershipDataAccessError, FarmMembershipRepository
from app.LivestockRegistry.utils.membership_dependencies import get_farm_membership_service
from app.LivestockRegistry.services.farm_membership_service import (
    FarmMembershipService,
    FarmMembershipUnavailableError,
)


class FarmMembershipRepositoryTests(unittest.TestCase):
    def test_get_active_memberships_filters_user_and_orders_by_joined_at(self) -> None:
        memberships = [{"farm_id": "farm-1", "status": "active"}]
        query = Mock()
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.execute.return_value = SimpleNamespace(data=memberships)
        client = Mock()
        client.table.return_value = query

        result = FarmMembershipRepository(client).get_active_memberships("user-123")

        self.assertEqual(result, memberships)
        client.table.assert_called_once_with("farm_membership")
        query.select.assert_called_once_with("*")
        self.assertEqual(
            query.eq.call_args_list,
            [
                unittest.mock.call("user_id", "user-123"),
                unittest.mock.call("status", "active"),
            ],
        )
        query.order.assert_called_once_with("joined_at")
        query.execute.assert_called_once_with()

    def test_database_failure_is_reported(self) -> None:
        query = Mock()
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.execute.side_effect = httpx.ConnectError("database unavailable")
        client = Mock()
        client.table.return_value = query

        with self.assertRaises(FarmMembershipDataAccessError):
            FarmMembershipRepository(client).get_active_memberships("user-123")


class FarmMembershipServiceTests(unittest.TestCase):
    def test_get_active_memberships_delegates_to_repository(self) -> None:
        memberships = [{"farm_id": "farm-1", "status": "active"}]
        repository = Mock(spec=FarmMembershipRepository)
        repository.get_active_memberships.return_value = memberships

        result = FarmMembershipService(repository).get_active_memberships("user-123")

        self.assertEqual(result, memberships)
        repository.get_active_memberships.assert_called_once_with("user-123")

    def test_repository_failure_is_reported_as_unavailable(self) -> None:
        repository = Mock(spec=FarmMembershipRepository)
        repository.get_active_memberships.side_effect = FarmMembershipDataAccessError

        with self.assertRaises(FarmMembershipUnavailableError):
            FarmMembershipService(repository).get_active_memberships("user-123")


class FarmMembershipControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.authenticated_user = AuthenticatedUser(
            SimpleNamespace(id="user-123"),
            "access-token",
        )
        app.dependency_overrides[get_authenticated_user] = (
            lambda: self.authenticated_user
        )

    def tearDown(self) -> None:
        self.client.app.dependency_overrides.clear()

    def test_get_my_farms_returns_active_memberships_for_authenticated_user(self) -> None:
        memberships = [{"farm_id": "farm-1", "status": "active"}]
        service = Mock(spec=FarmMembershipService)
        service.get_active_memberships.return_value = memberships
        self.client.app.dependency_overrides[get_farm_membership_service] = (
            lambda: service
        )

        response = self.client.get("/me/farms")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), memberships)
        service.get_active_memberships.assert_called_once_with("user-123")

    def test_database_failure_returns_503(self) -> None:
        service = Mock(spec=FarmMembershipService)
        service.get_active_memberships.side_effect = FarmMembershipUnavailableError
        self.client.app.dependency_overrides[get_farm_membership_service] = (
            lambda: service
        )

        response = self.client.get("/me/farms")

        self.assertEqual(response.status_code, 503)


class AuthenticatedFarmUserDependencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.authenticated_user = AuthenticatedUser(
            SimpleNamespace(id="user-123"),
            "access-token",
        )

    def test_builds_typed_farm_role_memberships(self) -> None:
        service = Mock(spec=FarmMembershipService)
        service.get_active_memberships.return_value = [
            {"farm_id": "farm-1", "role_id": "role-1"},
            {"farm_id": "farm-2", "role_id": "role-2"},
        ]

        result = get_authenticated_farm_user(self.authenticated_user, service)

        self.assertEqual(
            result,
            AuthenticatedFarmUser(
                self.authenticated_user,
                [
                    FarmRoleMembership("farm-1", "role-1"),
                    FarmRoleMembership("farm-2", "role-2"),
                ],
            ),
        )
        service.get_active_memberships.assert_called_once_with("user-123")

    def test_unavailable_membership_service_returns_503(self) -> None:
        service = Mock(spec=FarmMembershipService)
        service.get_active_memberships.side_effect = FarmMembershipUnavailableError

        with self.assertRaises(HTTPException) as raised:
            get_authenticated_farm_user(self.authenticated_user, service)

        self.assertEqual(raised.exception.status_code, 503)
