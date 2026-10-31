from fastapi import Depends

from app.Authentication.dependencies import (
    AuthenticatedUser,
    get_authenticated_user,
)
from app.IdentityAndAccess.dao.profile_repository import ProfileRepository
from app.IdentityAndAccess.services.profile_service import ProfileService
from app.core.db.supabase_client import create_authenticated_supabase_client


def get_profile_service(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ProfileService:
    client = create_authenticated_supabase_client(authenticated_user.access_token)
    return ProfileService(ProfileRepository(client))
