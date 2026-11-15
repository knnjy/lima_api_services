from uuid import UUID

from fastapi import Depends, HTTPException, Response, status

from app.LivestockRegistry.dto.farm_invitation_schema import (
    FarmInvitationCreate,
    FarmInvitationCreatedResponse,
    FarmInvitationResponse,
)
from app.LivestockRegistry.services.farm_invitation_service import (
    FarmInvitationAlreadyExistsError,
    FarmInvitationNotFoundError,
    FarmInvitationService,
    FarmInvitationUnavailableError,
    InvalidFarmInvitationStateError,
)
from app.LivestockRegistry.utils.farm_invitation_dependencies import (
    get_farm_invitation_service,
)
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    FarmRoleMembership,
    get_authenticated_farm_user,
)


class FarmInvitationController:
    def list_invitations(
        self,
        farm_id: UUID,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        invitation_service: FarmInvitationService = Depends(
            get_farm_invitation_service
        ),
    ) -> list[FarmInvitationResponse]:
        self._require_owner(context, farm_id)
        try:
            return invitation_service.list_invitations(farm_id)
        except FarmInvitationUnavailableError as exc:
            raise self._unavailable_error() from exc

    def create_invitation(
        self,
        farm_id: UUID,
        invitation: FarmInvitationCreate,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        invitation_service: FarmInvitationService = Depends(
            get_farm_invitation_service
        ),
    ) -> FarmInvitationCreatedResponse:
        owner_membership = self._require_owner(context, farm_id)
        if owner_membership.membership_id is None:
            raise self._unavailable_error(
                "Farm owner membership is missing its identifier"
            )
        try:
            return invitation_service.create_invitation(
                farm_id,
                owner_membership.membership_id,
                invitation,
            )
        except FarmInvitationAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "pending_invitation_exists",
                    "message": (
                        "A pending invitation already exists for this contact."
                    ),
                },
            ) from exc
        except FarmInvitationUnavailableError as exc:
            raise self._unavailable_error() from exc

    def cancel_invitation(
        self,
        farm_id: UUID,
        invitation_id: UUID,
        context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
        invitation_service: FarmInvitationService = Depends(
            get_farm_invitation_service
        ),
    ) -> Response:
        self._require_owner(context, farm_id)
        try:
            invitation_service.cancel_invitation(farm_id, invitation_id)
        except FarmInvitationNotFoundError as exc:
            raise self._not_found_error() from exc
        except InvalidFarmInvitationStateError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except FarmInvitationUnavailableError as exc:
            raise self._unavailable_error() from exc
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _require_owner(
        context: AuthenticatedFarmUser,
        farm_id: UUID,
    ) -> FarmRoleMembership:
        farm_id_str = str(farm_id)
        for membership in context.memberships:
            if membership.farm_id == farm_id_str and membership.role_id == "1":
                return membership
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only farm owners can manage invitations",
        )

    @staticmethod
    def _not_found_error() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm invitation not found",
        )

    @staticmethod
    def _unavailable_error(
        detail: str = "Farm invitation service is unavailable",
    ) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
