from fastapi import Depends

from app.Authentication.dependencies import AuthenticatedUser, get_authenticated_user
from app.LivestockRegistry.dao.farm_membership_repository import FarmMembershipRepository
from app.LivestockRegistry.services.farm_membership_service import FarmMembershipService
from app.common.db.supabase_client import create_authenticated_supabase_client


def get_farm_membership_service(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> FarmMembershipService:
    client = create_authenticated_supabase_client(authenticated_user.access_token)
    repository = FarmMembershipRepository(client)
    return FarmMembershipService(repository)
