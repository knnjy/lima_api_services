from uuid import UUID

from fastapi import Depends, HTTPException, Response, status

from app.LivestockRegistry.dto.farm_schema import FarmCreate, FarmResponse, FarmUpdate
from app.LivestockRegistry.services.farm_service import (
    FarmAccessDeniedError,
    FarmCreationRollbackError,
    FarmService,
    FarmUnavailableError,
)
from app.LivestockRegistry.errors import FarmNotFoundError
from app.LivestockRegistry.utils.farm_dependencies import get_farm_service
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    get_authenticated_farm_user,
)


class FarmController:
    def list_farms(
        self,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        farm_service: FarmService = Depends(get_farm_service),
    ) -> list[FarmResponse]:
        try:
            return farm_service.list_farms(self._farm_ids(context))
        except FarmUnavailableError as exc:
            raise self._unavailable_error() from exc

    def create_farm(
        self,
        farm: FarmCreate,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        farm_service: FarmService = Depends(get_farm_service),
    ) -> FarmResponse:
        try:
            return farm_service.create_farm(
                farm,
                context.authenticated_user.user.id,
            )
        except FarmCreationRollbackError as exc:
            raise self._unavailable_error(
                "Farm creation failed and cleanup could not be completed"
            ) from exc
        except FarmUnavailableError as exc:
            raise self._unavailable_error() from exc

    def get_farm(
        self,
        farm_id: UUID,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        farm_service: FarmService = Depends(get_farm_service),
    ) -> FarmResponse:
        try:
            return farm_service.get_farm(farm_id, self._farm_ids(context))
        except FarmNotFoundError as exc:
            raise self._not_found_error() from exc
        except FarmUnavailableError as exc:
            raise self._unavailable_error() from exc

    def update_farm(
        self,
        farm_id: UUID,
        farm: FarmUpdate,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        farm_service: FarmService = Depends(get_farm_service),
    ) -> FarmResponse:
        try:
            return farm_service.update_farm(
                farm_id,
                farm,
                self._farm_ids(context),
                self._owner_farm_ids(context),
            )
        except FarmNotFoundError as exc:
            raise self._not_found_error() from exc
        except FarmAccessDeniedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only farm owners can update this farm",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except FarmUnavailableError as exc:
            raise self._unavailable_error() from exc

    def delete_farm(
        self,
        farm_id: UUID,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        farm_service: FarmService = Depends(get_farm_service),
    ) -> Response:
        try:
            farm_service.delete_farm(
                farm_id,
                self._farm_ids(context),
                self._owner_farm_ids(context),
            )
        except FarmNotFoundError as exc:
            raise self._not_found_error() from exc
        except FarmAccessDeniedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only farm owners can delete this farm",
            ) from exc
        except FarmUnavailableError as exc:
            raise self._unavailable_error() from exc
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _farm_ids(context: AuthenticatedFarmUser) -> list[str]:
        return [membership.farm_id for membership in context.memberships]

    @staticmethod
    def _owner_farm_ids(context: AuthenticatedFarmUser) -> list[str]:
        return [
            membership.farm_id
            for membership in context.memberships
            if membership.role_id == "1"
        ]

    @staticmethod
    def _not_found_error() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found",
        )

    @staticmethod
    def _unavailable_error(
        detail: str = "Farm service is unavailable",
    ) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
