from uuid import UUID

from fastapi import Depends, HTTPException, Response, status

from app.LivestockRegistry.dto.animal_create import AnimalCreate
from app.LivestockRegistry.dto.animal_response import AnimalResponse
from app.LivestockRegistry.dto.animal_update import AnimalUpdate
from app.LivestockRegistry.services.animal_service import (
    AnimalNotFoundError,
    AnimalService,
    AnimalUnavailableError,
    FarmAccessDeniedError,
    InvalidAnimalUpdateError,
)
from app.LivestockRegistry.utils.animal_dependencies import get_animal_service
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    get_authenticated_farm_user,
)


class AnimalController:
    def list_animals(
        self,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        animal_service: AnimalService = Depends(get_animal_service),
    ) -> list[AnimalResponse]:
        try:
            return animal_service.list_animals(self._farm_ids(context))
        except AnimalUnavailableError as exc:
            raise self._unavailable_error() from exc

    def create_animal(
        self,
        animal: AnimalCreate,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        animal_service: AnimalService = Depends(get_animal_service),
    ) -> AnimalResponse:
        try:
            return animal_service.create_animal(
                animal,
                self._farm_ids(context),
            )
        except FarmAccessDeniedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this farm",
            ) from exc
        except AnimalUnavailableError as exc:
            raise self._unavailable_error() from exc

    def get_animal(
        self,
        animal_id: UUID,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        animal_service: AnimalService = Depends(get_animal_service),
    ) -> AnimalResponse:
        try:
            return animal_service.get_animal(
                animal_id,
                self._farm_ids(context),
            )
        except AnimalNotFoundError as exc:
            raise self._not_found_error() from exc
        except AnimalUnavailableError as exc:
            raise self._unavailable_error() from exc

    def update_animal(
        self,
        animal_id: UUID,
        animal: AnimalUpdate,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        animal_service: AnimalService = Depends(get_animal_service),
    ) -> AnimalResponse:
        try:
            return animal_service.update_animal(
                animal_id,
                animal,
                self._farm_ids(context),
            )
        except AnimalNotFoundError as exc:
            raise self._not_found_error() from exc
        except FarmAccessDeniedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this farm",
            ) from exc
        except InvalidAnimalUpdateError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except AnimalUnavailableError as exc:
            raise self._unavailable_error() from exc

    def delete_animal(
        self,
        animal_id: UUID,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        animal_service: AnimalService = Depends(get_animal_service),
    ) -> Response:
        try:
            animal_service.delete_animal(
                animal_id,
                self._farm_ids(context),
            )
        except AnimalNotFoundError as exc:
            raise self._not_found_error() from exc
        except AnimalUnavailableError as exc:
            raise self._unavailable_error() from exc
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _farm_ids(context: AuthenticatedFarmUser) -> list[str]:
        return [membership.farm_id for membership in context.memberships]

    @staticmethod
    def _not_found_error() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal not found",
        )

    @staticmethod
    def _unavailable_error() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Animal service is unavailable",
        )
