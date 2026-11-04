from uuid import UUID

from app.LivestockRegistry.dao.animal_group_repository import (
    AnimalGroupDataAccessError,
    AnimalGroupRepository,
)
from app.LivestockRegistry.dto.animal_group_schema import (
    AnimalGroupCreate,
    AnimalGroupResponse,
    AnimalGroupUpdate,
)
from app.LivestockRegistry.services.species_service import (
    SpeciesNotFoundError,
    SpeciesService,
    SpeciesUnavailableError,
)


class AnimalGroupUnavailableError(Exception):
    pass


class AnimalGroupNotFoundError(Exception):
    pass


class AnimalGroupFarmAccessDeniedError(Exception):
    pass


class AnimalGroupSpeciesNotFoundError(Exception):
    pass


class InvalidAnimalGroupUpdateError(Exception):
    pass


class AnimalGroupService:
    def __init__(
        self,
        repository: AnimalGroupRepository,
        species_service: SpeciesService,
    ) -> None:
        self._repository = repository
        self._species_service = species_service

    def list_animal_groups(self, farm_ids: list[str]) -> list[AnimalGroupResponse]:
        if not farm_ids:
            return []
        try:
            rows = self._repository.list_by_farms(farm_ids)
            return [AnimalGroupResponse.model_validate(row) for row in rows]
        except AnimalGroupDataAccessError as exc:
            raise AnimalGroupUnavailableError from exc

    def create_animal_group(
        self,
        animal_group: AnimalGroupCreate,
        farm_ids: list[str],
    ) -> AnimalGroupResponse:
        if str(animal_group.farm_id) not in farm_ids:
            raise AnimalGroupFarmAccessDeniedError
        try:
            self._species_service.get_species(animal_group.species_id)
        except SpeciesNotFoundError as exc:
            raise AnimalGroupSpeciesNotFoundError from exc
        except SpeciesUnavailableError as exc:
            raise AnimalGroupUnavailableError from exc

        try:
            row = self._repository.create(animal_group.model_dump(mode="json"))
            return AnimalGroupResponse.model_validate(row)
        except AnimalGroupDataAccessError as exc:
            raise AnimalGroupUnavailableError from exc

    def get_animal_group(
        self,
        animal_group_id: UUID,
        farm_ids: list[str],
    ) -> AnimalGroupResponse:
        row = self._get_row(animal_group_id, farm_ids)
        return AnimalGroupResponse.model_validate(row)

    def update_animal_group(
        self,
        animal_group_id: UUID,
        animal_group: AnimalGroupUpdate,
        farm_ids: list[str],
    ) -> AnimalGroupResponse:
        self._get_row(animal_group_id, farm_ids)
        update_data = animal_group.model_dump(mode="json", exclude_unset=True)
        if not update_data:
            raise InvalidAnimalGroupUpdateError("Provide at least one field to update")

        try:
            row = self._repository.update(
                str(animal_group_id),
                farm_ids,
                update_data,
            )
        except AnimalGroupDataAccessError as exc:
            raise AnimalGroupUnavailableError from exc
        if row is None:
            raise AnimalGroupNotFoundError
        return AnimalGroupResponse.model_validate(row)

    def delete_animal_group(
        self,
        animal_group_id: UUID,
        farm_ids: list[str],
    ) -> None:
        self._get_row(animal_group_id, farm_ids)
        try:
            deleted = self._repository.delete(str(animal_group_id), farm_ids)
        except AnimalGroupDataAccessError as exc:
            raise AnimalGroupUnavailableError from exc
        if not deleted:
            raise AnimalGroupNotFoundError

    def _get_row(
        self,
        animal_group_id: UUID,
        farm_ids: list[str],
    ) -> dict[str, object]:
        if not farm_ids:
            raise AnimalGroupNotFoundError
        try:
            row = self._repository.get_by_id(str(animal_group_id), farm_ids)
        except AnimalGroupDataAccessError as exc:
            raise AnimalGroupUnavailableError from exc
        if row is None:
            raise AnimalGroupNotFoundError
        return row
