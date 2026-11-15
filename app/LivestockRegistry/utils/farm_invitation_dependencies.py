from fastapi import Depends

from app.LivestockRegistry.dao.farm_invitation_repository import (
    FarmInvitationRepository,
)
from app.LivestockRegistry.services.farm_invitation_service import (
    FarmInvitationService,
)
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    get_authenticated_farm_user,
)
from app.core.db.supabase_client import create_authenticated_supabase_client


def get_farm_invitation_service(
    context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
) -> FarmInvitationService:
    client = create_authenticated_supabase_client(
        context.authenticated_user.access_token
    )
    return FarmInvitationService(FarmInvitationRepository(client))
