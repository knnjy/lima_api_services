from uuid import UUID

from app.LivestockRegistry.dao.animal_repository import (
    AnimalDataAccessError,
    AnimalRepository,
)
from app.LivestockRegistry.dto.animal_create import AnimalCreate
from app.LivestockRegistry.dto.animal_response import AnimalResponse
from app.LivestockRegistry.dto.animal_update import AnimalUpdate


class AnimalUnavailableError(Exception):
    pass


class AnimalNotFoundError(Exception):
    pass


class FarmAccessDeniedError(Exception):
    pass


class InvalidAnimalUpdateError(Exception):
    pass


class AnimalService:
    def __init__(self, repository: AnimalRepository) -> None:
        self._repository = repository

    def list_animals(self, farm_ids: list[str]) -> list[AnimalResponse]:
        if not farm_ids:
            return []
        try:
            rows = self._repository.list_by_farms(farm_ids)
            return [AnimalResponse.model_validate(row) for row in rows]
        except AnimalDataAccessError as exc:
            raise AnimalUnavailableError from exc

    def create_animal(
        self,
        animal: AnimalCreate,
        farm_ids: list[str],
    ) -> AnimalResponse:
        if str(animal.farm_id) not in farm_ids:
            raise FarmAccessDeniedError
        try:
            row = self._repository.create(animal.model_dump(mode="json"))
            return AnimalResponse.model_validate(row)
        except AnimalDataAccessError as exc:
            raise AnimalUnavailableError from exc

    def get_animal(
        self,
        animal_id: UUID,
        farm_ids: list[str],
    ) -> AnimalResponse:
        row = self._get_row(animal_id, farm_ids)
        return AnimalResponse.model_validate(row)

    def update_animal(
        self,
        animal_id: UUID,
        animal: AnimalUpdate,
        farm_ids: list[str],
    ) -> AnimalResponse:
        self._get_row(animal_id, farm_ids)
        update_data = animal.model_dump(mode="json", exclude_unset=True)
        if not update_data:
            raise InvalidAnimalUpdateError("Provide at least one field to update")

        target_farm_id = update_data.get("farm_id")
        if target_farm_id is not None and str(target_farm_id) not in farm_ids:
            raise FarmAccessDeniedError

        try:
            row = self._repository.update(str(animal_id), farm_ids, update_data)
        except AnimalDataAccessError as exc:
            raise AnimalUnavailableError from exc
        if row is None:
            raise AnimalNotFoundError
        return AnimalResponse.model_validate(row)

    def delete_animal(self, animal_id: UUID, farm_ids: list[str]) -> None:
        self._get_row(animal_id, farm_ids)
        try:
            deleted = self._repository.delete(str(animal_id), farm_ids)
        except AnimalDataAccessError as exc:
            raise AnimalUnavailableError from exc
        if not deleted:
            raise AnimalNotFoundError

    def _get_row(
        self,
        animal_id: UUID,
        farm_ids: list[str],
    ) -> dict[str, object]:
        if not farm_ids:
            raise AnimalNotFoundError
        try:
            row = self._repository.get_by_id(str(animal_id), farm_ids)
        except AnimalDataAccessError as exc:
            raise AnimalUnavailableError from exc
        if row is None:
            raise AnimalNotFoundError
        return row
