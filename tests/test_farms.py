import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from postgrest.exceptions import APIError

from app.LivestockRegistry.dao.farm_membership_repository import (
    FarmMembershipRepository,
)
from app.LivestockRegistry.dao.farm_repository import FarmAuthError, FarmRepository
from app.LivestockRegistry.dto.farm_membership_schema import FarmMembershipCreate
from app.LivestockRegistry.dto.farm_schema import FarmCreate, FarmResponse, FarmUpdate
from app.LivestockRegistry.errors import FarmNotFoundError
from app.LivestockRegistry.router.farm_router import router
from app.LivestockRegistry.services.farm_service import (
    FarmAccessDeniedError,
    FarmService,
)
from app.LivestockRegistry.utils.farm_dependencies import get_farm_service
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    FarmRoleMembership,
    get_authenticated_farm_user,
)
from app.Authentication.dependencies import AuthenticatedUser


def farm_row(
    farm_id: UUID,
    created_by: UUID,
) -> dict[str, object]:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    return {
        "farm_id": str(farm_id),
        "farm_name": "Green Farm",
        "created_by": str(created_by),
        "province": "Province",
        "city_municipality": "Municipality",
        "address_line": None,
        "is_active": True,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


class FarmServiceTests(unittest.TestCase):
    def test_update_schema_rejects_null_required_fields(self) -> None:
        with self.assertRaises(ValidationError):
            FarmUpdate(farm_name=None)

    def test_create_farm_assigns_creator_as_owner(self) -> None:
        user_id = uuid4()
        farm_id = uuid4()
        farm_repository = Mock(spec=FarmRepository)
        farm_repository.create.return_value = farm_row(farm_id, user_id)
        membership_repository = Mock(spec=FarmMembershipRepository)
        service = FarmService(farm_repository, membership_repository)
        farm = FarmCreate(
            farm_name=" Green Farm ",
            created_by=uuid4(),
            province=" Province ",
            city_municipality=" Municipality ",
        )

        result = service.create_farm(farm, user_id)

        self.assertEqual(result.farm_id, farm_id)
        self.assertEqual(result.created_by, user_id)
        farm_data = farm_repository.create.call_args.args[0]
        self.assertEqual(farm_data["created_by"], str(user_id))
        membership_repository.create_membership.assert_called_once_with(
            FarmMembershipCreate(
                user_id=user_id,
                farm_id=farm_id,
                role_id=1,
            )
        )

    def test_get_farm_rejects_non_member(self) -> None:
        service = FarmService(
            Mock(spec=FarmRepository),
            Mock(spec=FarmMembershipRepository),
        )

        with self.assertRaises(FarmNotFoundError):
            service.get_farm(uuid4(), [])

    def test_update_farm_rejects_non_owner(self) -> None:
        farm_id = uuid4()
        service = FarmService(
            Mock(spec=FarmRepository),
            Mock(spec=FarmMembershipRepository),
        )

        with self.assertRaises(FarmAccessDeniedError):
            service.update_farm(
                farm_id,
                FarmUpdate(farm_name="Updated"),
                [str(farm_id)],
                [],
            )

    def test_delete_farm_maps_rpc_authorization_error(self) -> None:
        farm_id = uuid4()
        farm_repository = Mock(spec=FarmRepository)
        farm_repository.delete.side_effect = FarmAuthError
        service = FarmService(
            farm_repository,
            Mock(spec=FarmMembershipRepository),
        )

        with self.assertRaises(FarmAccessDeniedError):
            service.delete_farm(
                farm_id,
                [str(farm_id)],
                [str(farm_id)],
            )


class FarmRepositoryTests(unittest.TestCase):
    def test_delete_maps_rpc_auth_error(self) -> None:
        client = Mock()
        client.rpc.return_value.execute.side_effect = APIError(
            {
                "message": "not authorized",
                "code": "28000",
                "details": None,
                "hint": None,
            }
        )

        with self.assertRaises(FarmAuthError):
            FarmRepository(client).delete(str(uuid4()))


class FarmControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.farm_id = uuid4()
        self.context = AuthenticatedFarmUser(
            AuthenticatedUser(
                SimpleNamespace(id=self.user_id),
                "access-token",
            ),
            [FarmRoleMembership(str(self.farm_id), "1")],
        )
        self.service = Mock(spec=FarmService)
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_authenticated_farm_user] = (
            lambda: self.context
        )
        self.app.dependency_overrides[get_farm_service] = lambda: self.service
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_farms(self) -> None:
        self.service.list_farms.return_value = []

        response = self.client.get("/farms")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.service.list_farms.assert_called_once_with([str(self.farm_id)])

    def test_create_farm(self) -> None:
        row = farm_row(self.farm_id, self.user_id)
        self.service.create_farm.return_value = FarmResponse.model_validate(row)

        response = self.client.post(
            "/farms",
            json={
                "farm_name": "Green Farm",
                "province": "Province",
                "city_municipality": "Municipality",
                "created_by": str(uuid4()),
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["farm_id"], str(self.farm_id))
        self.assertEqual(
            self.service.create_farm.call_args.args[1],
            self.user_id,
        )

    def test_get_farm(self) -> None:
        self.service.get_farm.return_value = FarmResponse.model_validate(
            farm_row(self.farm_id, self.user_id)
        )

        response = self.client.get(f"/farms/{self.farm_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["farm_id"], str(self.farm_id))

    def test_update_farm(self) -> None:
        self.service.update_farm.return_value = FarmResponse.model_validate(
            farm_row(self.farm_id, self.user_id)
        )

        response = self.client.patch(
            f"/farms/{self.farm_id}",
            json={"farm_name": "Updated Farm"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.service.update_farm.call_args.args[3],
            [str(self.farm_id)],
        )

    def test_delete_farm(self) -> None:
        response = self.client.delete(f"/farms/{self.farm_id}")

        self.assertEqual(response.status_code, 204)
        self.service.delete_farm.assert_called_once_with(
            self.farm_id,
            [str(self.farm_id)],
            [str(self.farm_id)],
        )

    def test_worker_cannot_update_farm(self) -> None:
        self.context = AuthenticatedFarmUser(
            self.context.authenticated_user,
            [FarmRoleMembership(str(self.farm_id), "2")],
        )

        response = self.client.patch(
            f"/farms/{self.farm_id}",
            json={"farm_name": "Updated Farm"},
        )

        self.assertEqual(response.status_code, 403)
        self.service.update_farm.assert_not_called()

    def test_delete_rpc_authorization_error_returns_403(self) -> None:
        self.service.delete_farm.side_effect = FarmAccessDeniedError

        response = self.client.delete(f"/farms/{self.farm_id}")

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
