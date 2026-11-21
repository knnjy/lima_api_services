from fastapi import Depends

from app.Authentication.dependencies import (
    AuthenticatedUser,
    get_authenticated_user,
)
from app.IdentityAndAccess.dao.profile_repository import ProfileRepository
from app.IdentityAndAccess.dao.user_preferences_repository import (
    UserPreferencesRepository,
)
from app.IdentityAndAccess.services.user_preferences_service import (
    UserPreferencesService,
)
from app.IdentityAndAccess.services.user_view_service import UserViewService
from app.core.db.supabase_client import create_authenticated_supabase_client


def get_user_preferences_service(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> UserPreferencesService:
    client = create_authenticated_supabase_client(authenticated_user.access_token)
    return UserPreferencesService(UserPreferencesRepository(client))


def get_user_view_service(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> UserViewService:
    client = create_authenticated_supabase_client(authenticated_user.access_token)
    return UserViewService(
        ProfileRepository(client),
        UserPreferencesRepository(client),
    )
