from dataclasses import dataclass

from fastapi import Depends, HTTPException, status

from app.Authentication.dependencies import AuthenticatedUser, get_authenticated_user
from app.LivestockRegistry.utils.membership_dependencies import (
    get_farm_membership_service,
)
from app.LivestockRegistry.services.farm_membership_service import (
    FarmMembershipService,
    FarmMembershipUnavailableError,
)


@dataclass(frozen=True)
class FarmRoleMembership:
    farm_id: str
    role_id: str


@dataclass(frozen=True)
class AuthenticatedFarmUser:
    authenticated_user: AuthenticatedUser
    memberships: list[FarmRoleMembership]


def get_authenticated_farm_user(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    membership_service: FarmMembershipService = Depends(get_farm_membership_service),
) -> AuthenticatedFarmUser:
    try:
        rows = membership_service.get_active_memberships(
            str(authenticated_user.user.id)
        )
    except FarmMembershipUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Farm membership service is unavailable",
        ) from exc

    memberships = [
        FarmRoleMembership(
            farm_id=str(row["farm_id"]),
            role_id=str(row["role_id"]),
        )
        for row in rows
    ]

    return AuthenticatedFarmUser(authenticated_user, memberships)