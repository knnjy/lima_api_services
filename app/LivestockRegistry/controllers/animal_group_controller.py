from uuid import UUID

from fastapi import Depends, HTTPException, Response, status

from app.LivestockRegistry.dto.animal_group_schema import (
    AnimalGroupCreate,
    AnimalGroupResponse,
    AnimalGroupUpdate,
)
from app.LivestockRegistry.services.animal_group_service import (
    AnimalGroupFarmAccessDeniedError,
    AnimalGroupNotFoundError,
    AnimalGroupService,
    AnimalGroupSpeciesNotFoundError,
    AnimalGroupUnavailableError,
    InvalidAnimalGroupUpdateError,
)
from app.LivestockRegistry.utils.animal_group_dependencies import (
    get_animal_group_service,
)
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    get_authenticated_farm_user,
)


class AnimalGroupController:
    def list_animal_groups(
        self,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        animal_group_service: AnimalGroupService = Depends(get_animal_group_service),
    ) -> list[AnimalGroupResponse]:
        try:
            return animal_group_service.list_animal_groups(self._farm_ids(context))
        except AnimalGroupUnavailableError as exc:
            raise self._unavailable_error() from exc

    def create_animal_group(
        self,
        animal_group: AnimalGroupCreate,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        animal_group_service: AnimalGroupService = Depends(get_animal_group_service),
    ) -> AnimalGroupResponse:
        try:
            return animal_group_service.create_animal_group(
                animal_group,
                self._farm_ids(context),
            )
        except AnimalGroupFarmAccessDeniedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this farm",
            ) from exc
        except AnimalGroupSpeciesNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Species not found",
            ) from exc
        except AnimalGroupUnavailableError as exc:
            raise self._unavailable_error() from exc

    def get_animal_group(
        self,
        animal_group_id: UUID,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        animal_group_service: AnimalGroupService = Depends(get_animal_group_service),
    ) -> AnimalGroupResponse:
        try:
            return animal_group_service.get_animal_group(
                animal_group_id,
                self._farm_ids(context),
            )
        except AnimalGroupNotFoundError as exc:
            raise self._not_found_error() from exc
        except AnimalGroupUnavailableError as exc:
            raise self._unavailable_error() from exc

    def update_animal_group(
        self,
        animal_group_id: UUID,
        animal_group: AnimalGroupUpdate,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        animal_group_service: AnimalGroupService = Depends(get_animal_group_service),
    ) -> AnimalGroupResponse:
        try:
            return animal_group_service.update_animal_group(
                animal_group_id,
                animal_group,
                self._farm_ids(context),
            )
        except AnimalGroupNotFoundError as exc:
            raise self._not_found_error() from exc
        except InvalidAnimalGroupUpdateError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except AnimalGroupUnavailableError as exc:
            raise self._unavailable_error() from exc

    def delete_animal_group(
        self,
        animal_group_id: UUID,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        animal_group_service: AnimalGroupService = Depends(get_animal_group_service),
    ) -> Response:
        try:
            animal_group_service.delete_animal_group(
                animal_group_id,
                self._farm_ids(context),
            )
        except AnimalGroupNotFoundError as exc:
            raise self._not_found_error() from exc
        except AnimalGroupUnavailableError as exc:
            raise self._unavailable_error() from exc
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _farm_ids(context: AuthenticatedFarmUser) -> list[str]:
        return [membership.farm_id for membership in context.memberships]

    @staticmethod
    def _not_found_error() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal group not found",
        )

    @staticmethod
    def _unavailable_error() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Animal group service is unavailable",
        )
