from fastapi import Depends, HTTPException, status

from app.LivestockRegistry.dto.species_schema import SpeciesResponse
from app.LivestockRegistry.services.species_service import (
    SpeciesNotFoundError,
    SpeciesService,
    SpeciesUnavailableError,
)
from app.LivestockRegistry.utils.species_dependencies import get_species_service


class SpeciesController:
    def list_species(
        self,
        species_service: SpeciesService = Depends(get_species_service),
    ) -> list[SpeciesResponse]:
        try:
            return species_service.list_species()
        except SpeciesUnavailableError as exc:
            raise self._unavailable_error() from exc

    def get_species(
        self,
        species_id: int,
        species_service: SpeciesService = Depends(get_species_service),
    ) -> SpeciesResponse:
        try:
            return species_service.get_species(species_id)
        except SpeciesNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Species not found",
            ) from exc
        except SpeciesUnavailableError as exc:
            raise self._unavailable_error() from exc

    @staticmethod
    def _unavailable_error() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Species service is unavailable",
        )
