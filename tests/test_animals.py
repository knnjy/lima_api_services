import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.Authentication.dependencies import AuthenticatedUser
from app.LivestockRegistry.router.animal_router import router
from app.LivestockRegistry.services.animal_service import (
    AnimalService,
    FarmAccessDeniedError,
)
from app.LivestockRegistry.utils.animal_dependencies import get_animal_service
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    FarmRoleMembership,
    get_authenticated_farm_user,
)


class AnimalServiceTests(unittest.TestCase):
    def test_list_animals_queries_only_the_requested_farm(self) -> None:
        farm_id = uuid4()
        other_farm_id = uuid4()
        repository = Mock()
        repository.list_by_farms.return_value = []

        result = AnimalService(repository).list_animals(
            farm_id,
            [str(farm_id), str(other_farm_id)],
        )

        self.assertEqual(result, [])
        repository.list_by_farms.assert_called_once_with([str(farm_id)])

    def test_list_animals_rejects_farms_without_membership(self) -> None:
        repository = Mock()

        with self.assertRaises(FarmAccessDeniedError):
            AnimalService(repository).list_animals(uuid4(), [])

        repository.list_by_farms.assert_not_called()


class AnimalControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.farm_id = uuid4()
        self.context = AuthenticatedFarmUser(
            AuthenticatedUser(SimpleNamespace(id=uuid4()), "access-token"),
            [FarmRoleMembership(str(self.farm_id), "1")],
        )
        self.service = Mock(spec=AnimalService)
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_authenticated_farm_user] = (
            lambda: self.context
        )
        self.app.dependency_overrides[get_animal_service] = lambda: self.service
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_animals_for_farm(self) -> None:
        self.service.list_animals.return_value = []

        response = self.client.get(f"/me/animals/{self.farm_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.service.list_animals.assert_called_once_with(
            self.farm_id,
            [str(self.farm_id)],
        )

    def test_list_animals_rejects_farm_without_membership(self) -> None:
        self.service.list_animals.side_effect = FarmAccessDeniedError

        response = self.client.get(f"/me/animals/{uuid4()}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "You do not have access to this farm")
        self.service.list_animals.assert_called_once()

