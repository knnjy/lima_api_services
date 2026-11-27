from fastapi import Depends

from app.Authentication.dependencies import (
    AuthenticatedUser,
    get_authenticated_user,
)
from app.Farm.FarmInvitations.dao.farm_invitation_repository import (
    FarmInvitationRepository,
)
from app.Farm.FarmInvitations.services.farm_invitation_service import (
    FarmInvitationService,
)
from app.core.db.supabase_client import create_authenticated_supabase_client


def get_farm_invitation_service(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> FarmInvitationService:
    client = create_authenticated_supabase_client(
        authenticated_user.access_token
    )
    return FarmInvitationService(FarmInvitationRepository(client))
