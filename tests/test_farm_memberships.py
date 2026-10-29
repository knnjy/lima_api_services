import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.Authentication.dependencies import AuthenticatedUser, get_authenticated_user
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    FarmRoleMembership,
    get_authenticated_farm_user,
)
from app.LivestockRegistry.router.farm_membership_router import router

from app.LivestockRegistry.dao.farm_membership_repository import (
    FarmMembershipDataAccessError,
    FarmMembershipRepository,
)
from app.LivestockRegistry.utils.membership_dependencies import get_farm_membership_service
from app.LivestockRegistry.services.farm_membership_service import (
    FarmNotFoundError,
    FarmMembershipService,
    FarmMembershipUnavailableError,
)
from app.LivestockRegistry.dto.farm_membership_schema import FarmMembershipCreate


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

    def test_create_membership_requests_inserted_row(self) -> None:
        membership = {"user_id": "user-123", "farm_id": "farm-123", "role_id": 1}
        query = Mock()
        query.insert.return_value = query
        query.select.return_value = query
        query.execute.return_value = SimpleNamespace(data=[membership])
        client = Mock()
        client.table.return_value = query

        result = FarmMembershipRepository(client).create_membership(
            FarmMembershipCreate(
                user_id=UUID("00000000-0000-0000-0000-000000000123"),
                farm_id=UUID("00000000-0000-0000-0000-000000000456"),
                role_id=1,
            )
        )

        self.assertEqual(result, membership)
        client.table.assert_called_once_with("farm_membership")
        query.select.assert_called_once_with("*")

    def test_farm_exists_checks_farm_foreign_key(self) -> None:
        query = Mock()
        query.select.return_value = query
        query.eq.return_value = query
        query.limit.return_value = query
        query.execute.return_value = SimpleNamespace(data=[{"farm_id": "farm-123"}])
        client = Mock()
        client.table.return_value = query

        exists = FarmMembershipRepository(client).farm_exists("farm-123")

        self.assertTrue(exists)
        client.table.assert_called_once_with("farm")
        query.select.assert_called_once_with("farm_id")
        query.eq.assert_called_once_with("farm_id", "farm-123")
        query.limit.assert_called_once_with(1)


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

    def test_create_membership_checks_farm_before_insert(self) -> None:
        member_data = FarmMembershipCreate(
            user_id=uuid4(),
            farm_id=uuid4(),
            role_id=1,
        )
        created = {"id": str(uuid4())}
        repository = Mock(spec=FarmMembershipRepository)
        repository.farm_exists.return_value = True
        repository.create_membership.return_value = created

        result = FarmMembershipService(repository).create_membership(member_data)

        self.assertEqual(result, created)
        repository.farm_exists.assert_called_once_with(str(member_data.farm_id))
        repository.create_membership.assert_called_once_with(member_data)

    def test_create_membership_does_not_insert_when_farm_is_missing(self) -> None:
        member_data = FarmMembershipCreate(
            user_id=uuid4(),
            farm_id=uuid4(),
            role_id=1,
        )
        repository = Mock(spec=FarmMembershipRepository)
        repository.farm_exists.return_value = False

        with self.assertRaises(FarmNotFoundError):
            FarmMembershipService(repository).create_membership(member_data)

        repository.create_membership.assert_not_called()


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

    def test_create_membership_uses_authenticated_user_and_returns_created_row(self) -> None:
        user_id = uuid4()
        farm_id = uuid4()
        self.authenticated_user.user = SimpleNamespace(id=user_id)
        membership = {
            "id": str(uuid4()),
            "user_id": str(user_id),
            "farm_id": str(farm_id),
            "role_id": 1,
            "invitation_id": None,
            "status": "active",
            "joined_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        service = Mock(spec=FarmMembershipService)
        service.create_membership.return_value = membership
        self.client.app.dependency_overrides[get_farm_membership_service] = (
            lambda: service
        )

        response = self.client.post(
            "/me/farms",
            json={"farm_id": str(farm_id), "role_id": 1},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), membership)
        service.create_membership.assert_called_once_with(
            FarmMembershipCreate(
                user_id=user_id,
                farm_id=farm_id,
                role_id=1,
            )
        )

    def test_create_membership_returns_404_for_missing_farm(self) -> None:
        self.authenticated_user.user = SimpleNamespace(id=uuid4())
        service = Mock(spec=FarmMembershipService)
        service.create_membership.side_effect = FarmNotFoundError
        self.client.app.dependency_overrides[get_farm_membership_service] = (
            lambda: service
        )

        response = self.client.post(
            "/me/farms",
            json={"farm_id": str(uuid4()), "role_id": 1},
        )

        self.assertEqual(response.status_code, 404)


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
