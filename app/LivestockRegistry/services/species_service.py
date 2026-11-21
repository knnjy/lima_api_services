from app.LivestockRegistry.dao.species_repository import (
    SpeciesDataAccessError,
    SpeciesRepository,
)
from app.LivestockRegistry.dto.species_schema import SpeciesResponse


class SpeciesUnavailableError(Exception):
    pass


class SpeciesNotFoundError(Exception):
    pass


class SpeciesService:
    def __init__(self, repository: SpeciesRepository) -> None:
        self._repository = repository

    def list_species(self) -> list[SpeciesResponse]:
        try:
            rows = self._repository.list_all()
        except SpeciesDataAccessError as exc:
            raise SpeciesUnavailableError from exc
        return [SpeciesResponse.model_validate(row) for row in rows]

    def get_species(self, species_id: int) -> SpeciesResponse:
        try:
            row = self._repository.get_by_id(species_id)
        except SpeciesDataAccessError as exc:
            raise SpeciesUnavailableError from exc
        if row is None:
            raise SpeciesNotFoundError
        return SpeciesResponse.model_validate(row)