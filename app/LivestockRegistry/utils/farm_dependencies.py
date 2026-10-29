from fastapi import Depends

from app.LivestockRegistry.dao.farm_membership_repository import (
    FarmMembershipRepository,
)
from app.LivestockRegistry.dao.farm_repository import FarmRepository
from app.LivestockRegistry.services.farm_service import FarmService
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    get_authenticated_farm_user,
)
from app.core.db.supabase_client import create_authenticated_supabase_client


def get_farm_service(
    context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
) -> FarmService:
    client = create_authenticated_supabase_client(
        context.authenticated_user.access_token
    )
    return FarmService(
        FarmRepository(client),
        FarmMembershipRepository(client),
    )
