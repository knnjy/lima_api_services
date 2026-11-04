import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.LivestockRegistry.dao.species_repository import SpeciesRepository
from app.LivestockRegistry.dto.species_schema import SpeciesResponse
from app.LivestockRegistry.router.species_router import router
from app.LivestockRegistry.services.species_service import (
    SpeciesNotFoundError,
    SpeciesService,
)
from app.LivestockRegistry.utils.species_dependencies import get_species_service


def species_row(species_id: int) -> dict[str, object]:
    return {
        "species_id": species_id,
        "species_name": f"Species {species_id}",
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
    }


class SpeciesRepositoryTests(unittest.TestCase):
    def test_list_all_reads_species_ordered_by_id(self) -> None:
        rows = [species_row(1), species_row(2)]
        query = Mock()
        query.select.return_value = query
        query.order.return_value = query
        query.execute.return_value = SimpleNamespace(data=rows)
        client = Mock()
        client.table.return_value = query

        result = SpeciesRepository(client).list_all()

        self.assertEqual(result, rows)
        client.table.assert_called_once_with("species")
        query.select.assert_called_once_with("*")
        query.order.assert_called_once_with("species_id")

    def test_get_by_id_filters_species_id(self) -> None:
        row = species_row(3)
        query = Mock()
        query.select.return_value = query
        query.eq.return_value = query
        query.limit.return_value = query
        query.execute.return_value = SimpleNamespace(data=[row])
        client = Mock()
        client.table.return_value = query

        result = SpeciesRepository(client).get_by_id(3)

        self.assertEqual(result, row)
        query.eq.assert_called_once_with("species_id", 3)


class SpeciesServiceTests(unittest.TestCase):
    def test_list_and_get_species(self) -> None:
        repository = Mock(spec=SpeciesRepository)
        repository.list_all.return_value = [species_row(1)]
        repository.get_by_id.return_value = species_row(1)
        service = SpeciesService(repository)

        self.assertEqual(
            service.list_species(),
            [SpeciesResponse.model_validate(species_row(1))],
        )
        self.assertEqual(
            service.get_species(1),
            SpeciesResponse.model_validate(species_row(1)),
        )

    def test_get_species_reports_missing_id(self) -> None:
        repository = Mock(spec=SpeciesRepository)
        repository.get_by_id.return_value = None

        with self.assertRaises(SpeciesNotFoundError):
            SpeciesService(repository).get_species(999)


class SpeciesControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = Mock(spec=SpeciesService)
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_species_service] = lambda: self.service
        self.client = TestClient(app)
        self.app = app

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_species(self) -> None:
        self.service.list_species.return_value = [
            SpeciesResponse.model_validate(species_row(1))
        ]

        response = self.client.get("/species")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["species_id"], 1)

    def test_get_species_by_id(self) -> None:
        self.service.get_species.return_value = SpeciesResponse.model_validate(
            species_row(1)
        )

        response = self.client.get("/species/1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["species_id"], 1)
        self.service.get_species.assert_called_once_with(1)
