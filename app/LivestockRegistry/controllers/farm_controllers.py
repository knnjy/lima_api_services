from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.Authentication.dependencies import (
    AuthenticatedUser,
    get_authenticated_user,
)
from app.LivestockRegistry.membership_dependencies import get_farm_membership_service
from app.LivestockRegistry.services.farm_membership_service import (
    FarmMembershipService,
    FarmMembershipUnavailableError,
)


class FarmMembershipController:
    def get_my_farm_memberships(
        self,
        authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
        membership_service: FarmMembershipService = Depends(
            get_farm_membership_service
        ),
    ) -> list[dict[str, Any]]:
        try:
            return membership_service.get_active_memberships(
                str(authenticated_user.user.id)
            )
        except FarmMembershipUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Farm membership service is unavailable",
            ) from exc


router = APIRouter(prefix="/me", tags=["me"])
farm_membership_controller = FarmMembershipController()

router.add_api_route(
    "/farms",
    farm_membership_controller.get_my_farm_memberships,
    methods=["GET"],
    response_model=list[dict[str, Any]],
)