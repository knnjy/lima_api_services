from uuid import UUID

from app.IdentityAndAccess.dao.profile_repository import (
    ProfileDataAccessError,
    ProfileRepository,
)
from app.IdentityAndAccess.dao.user_preferences_repository import (
    UserPreferencesDataAccessError,
    UserPreferencesRepository,
)
from app.IdentityAndAccess.dto.profile_schema import ProfileResponse
from app.IdentityAndAccess.dto.user_preferences_schema import (
    UserPreferencesResponse,
    UserViewResponse,
)


class UserViewNotFoundError(Exception):
    pass


class UserViewUnavailableError(Exception):
    pass


class UserViewService:
    def __init__(
        self,
        profile_repository: ProfileRepository,
        preferences_repository: UserPreferencesRepository,
    ) -> None:
        self._profile_repository = profile_repository
        self._preferences_repository = preferences_repository

    def get_user_view(self, user_id: UUID) -> UserViewResponse:
        try:
            profile = self._profile_repository.get_by_user_id(str(user_id))
            preferences = self._preferences_repository.get_by_user_id(
                str(user_id)
            )
        except (ProfileDataAccessError, UserPreferencesDataAccessError) as exc:
            raise UserViewUnavailableError from exc

        if profile is None or preferences is None:
            raise UserViewNotFoundError

        return UserViewResponse(
            profile=ProfileResponse.model_validate(profile),
            user_preferences=UserPreferencesResponse.model_validate(preferences),
        )
