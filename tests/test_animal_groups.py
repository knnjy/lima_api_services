import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.Authentication.dependencies import AuthenticatedUser
from app.LivestockRegistry.dao.animal_group_repository import AnimalGroupRepository
from app.LivestockRegistry.dto.animal_group_schema import (
    AnimalGroupCreate,
    AnimalGroupResponse,
    AnimalGroupUpdate,
)
from app.LivestockRegistry.router.animal_group_router import router
from app.LivestockRegistry.services.animal_group_service import (
    AnimalGroupFarmAccessDeniedError,
    AnimalGroupNotFoundError,
    AnimalGroupSpeciesNotFoundError,
    AnimalGroupService,
    InvalidAnimalGroupUpdateError,
)
from app.LivestockRegistry.services.species_service import SpeciesService
from app.LivestockRegistry.services.species_service import SpeciesNotFoundError
from app.LivestockRegistry.utils.animal_group_dependencies import (
    get_animal_group_service,
)
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    FarmRoleMembership,
    get_authenticated_farm_user,
)


def animal_group_row(animal_group_id, farm_id):
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    return {
        "animal_group_id": str(animal_group_id),
        "farm_id": str(farm_id),
        "species_id": 1,
        "breed_id": None,
        "group_name": "Herd A",
        "sex": "mixed",
        "date_established": date(2026, 1, 1).isoformat(),
        "initial_head_count": 10,
        "current_head_count": 10,
        "status": "active",
        "remarks": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


class AnimalGroupRepositoryTests(unittest.TestCase):
    def test_crud_queries_use_animal_group_table_and_farm_scope(self) -> None:
        farm_id = str(uuid4())
        group_id = str(uuid4())
        row = animal_group_row(group_id, farm_id)
        query = Mock()
        for method in ("select", "in_", "order", "eq", "insert", "update", "delete"):
            getattr(query, method).return_value = query
        query.execute.return_value = SimpleNamespace(data=[row])
        client = Mock()
        client.table.return_value = query
        repository = AnimalGroupRepository(client)

        self.assertEqual(repository.list_by_farms([farm_id]), [row])
        self.assertEqual(repository.get_by_id(group_id, [farm_id]), row)
        self.assertEqual(repository.create(row), row)
        self.assertEqual(repository.update(group_id, [farm_id], row), row)
        self.assertTrue(repository.delete(group_id, [farm_id]))

        self.assertEqual(client.table.call_count, 5)
        self.assertTrue(all(call.args == ("animal_group",) for call in client.table.call_args_list))
        self.assertIn(unittest.mock.call("farm_id", [farm_id]), query.in_.call_args_list)
        self.assertIn(
            unittest.mock.call("animal_group_id", group_id),
            query.eq.call_args_list,
        )


class AnimalGroupServiceTests(unittest.TestCase):
    def test_create_rejects_farms_without_membership(self) -> None:
        animal_group = AnimalGroupCreate(
            farm_id=uuid4(),
            species_id=1,
            group_name="Herd A",
            initial_head_count=10,
            current_head_count=10,
        )
        repository = Mock(spec=AnimalGroupRepository)
        species_service = Mock(spec=SpeciesService)

        with self.assertRaises(AnimalGroupFarmAccessDeniedError):
            AnimalGroupService(repository, species_service).create_animal_group(
                animal_group,
                [],
            )

        repository.create.assert_not_called()
        species_service.get_species.assert_not_called()

    def test_create_rejects_missing_species(self) -> None:
        farm_id = uuid4()
        animal_group = AnimalGroupCreate(
            farm_id=farm_id,
            species_id=999,
            group_name="Herd A",
            initial_head_count=10,
            current_head_count=10,
        )
        repository = Mock(spec=AnimalGroupRepository)
        species_service = Mock(spec=SpeciesService)
        species_service.get_species.side_effect = SpeciesNotFoundError

        with self.assertRaises(AnimalGroupSpeciesNotFoundError):
            AnimalGroupService(repository, species_service).create_animal_group(
                animal_group,
                [str(farm_id)],
            )

        species_service.get_species.assert_called_once_with(999)
        repository.create.assert_not_called()

    def test_update_requires_a_field(self) -> None:
        farm_id = uuid4()
        group_id = uuid4()
        repository = Mock(spec=AnimalGroupRepository)
        repository.get_by_id.return_value = animal_group_row(group_id, farm_id)

        with self.assertRaisesRegex(
            InvalidAnimalGroupUpdateError,
            "Provide at least one field",
        ):
            AnimalGroupService(
                repository,
                Mock(spec=SpeciesService),
            ).update_animal_group(
                group_id,
                AnimalGroupUpdate(),
                [str(farm_id)],
            )

        repository.update.assert_not_called()

    def test_get_rejects_group_outside_membership(self) -> None:
        repository = Mock(spec=AnimalGroupRepository)
        repository.get_by_id.return_value = None

        with self.assertRaises(AnimalGroupNotFoundError):
            AnimalGroupService(
                repository,
                Mock(spec=SpeciesService),
            ).get_animal_group(uuid4(), [])

        repository.get_by_id.assert_not_called()


class AnimalGroupControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.farm_id = uuid4()
        self.group_id = uuid4()
        self.context = AuthenticatedFarmUser(
            AuthenticatedUser(SimpleNamespace(id=uuid4()), "access-token"),
            [FarmRoleMembership(str(self.farm_id), "1")],
        )
        self.service = Mock(spec=AnimalGroupService)
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_authenticated_farm_user] = (
            lambda: self.context
        )
        self.app.dependency_overrides[get_animal_group_service] = (
            lambda: self.service
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_animal_groups(self) -> None:
        self.service.list_animal_groups.return_value = []

        response = self.client.get("/me/animal-groups")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.service.list_animal_groups.assert_called_once_with([str(self.farm_id)])

    def test_create_animal_group(self) -> None:
        row = animal_group_row(self.group_id, self.farm_id)
        self.service.create_animal_group.return_value = AnimalGroupResponse.model_validate(row)

        response = self.client.post(
            "/me/animal-groups",
            json={
                "farm_id": str(self.farm_id),
                "species_id": 1,
                "group_name": "Herd A",
                "initial_head_count": 10,
                "current_head_count": 10,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["animal_group_id"], str(self.group_id))
        self.assertEqual(
            self.service.create_animal_group.call_args.args[1],
            [str(self.farm_id)],
        )

    def test_get_animal_group(self) -> None:
        row = animal_group_row(self.group_id, self.farm_id)
        self.service.get_animal_group.return_value = AnimalGroupResponse.model_validate(row)

        response = self.client.get(f"/me/animal-groups/{self.group_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["animal_group_id"], str(self.group_id))

    def test_update_animal_group(self) -> None:
        row = animal_group_row(self.group_id, self.farm_id)
        self.service.update_animal_group.return_value = AnimalGroupResponse.model_validate(row)

        response = self.client.patch(
            f"/me/animal-groups/{self.group_id}",
            json={"group_name": "Updated herd"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.service.update_animal_group.call_args.args[2],
            [str(self.farm_id)],
        )

    def test_delete_animal_group(self) -> None:
        response = self.client.delete(f"/me/animal-groups/{self.group_id}")

        self.assertEqual(response.status_code, 204)
        self.service.delete_animal_group.assert_called_once_with(
            self.group_id,
            [str(self.farm_id)],
        )
