from uuid import UUID

from app.IdentityAndAccess.dao.profile_repository import (
    ProfileAlreadyExistsDataError,
    ProfileDataAccessError,
    ProfileRepository,
)
from app.IdentityAndAccess.dto.profile_schema import (
    ProfileCreate,
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdate,
)


class ProfileNotFoundError(Exception):
    pass


class ProfileUnavailableError(Exception):
    pass


class ProfileAlreadyExistsError(Exception):
    pass


class ProfileService:
    def __init__(self, repository: ProfileRepository) -> None:
        self._repository = repository

    def get_profile(self, user_id: UUID) -> ProfileResponse:
        try:
            profile = self._repository.get_by_user_id(str(user_id))
        except ProfileDataAccessError as exc:
            raise ProfileUnavailableError from exc

        if profile is None:
            raise ProfileNotFoundError

        return ProfileResponse.model_validate(profile)

    def create_profile(
        self,
        profile: ProfileCreateRequest,
        user_id: UUID,
    ) -> ProfileResponse:
        try:
            if self._repository.get_by_user_id(str(user_id)) is not None:
                raise ProfileAlreadyExistsError
            created_profile = self._repository.create(
                ProfileCreate(
                    user_id=user_id,
                    **profile.model_dump(),
                ).model_dump(mode="json")
            )
        except ProfileAlreadyExistsDataError as exc:
            raise ProfileAlreadyExistsError from exc
        except ProfileDataAccessError as exc:
            raise ProfileUnavailableError from exc

        return ProfileResponse.model_validate(created_profile)

    def update_profile(
        self,
        profile: ProfileUpdate,
        user_id: UUID,
    ) -> ProfileResponse:
        try:
            updated_profile = self._repository.update_by_user_id(
                str(user_id),
                profile.model_dump(mode="json", exclude_unset=True),
            )
        except ProfileDataAccessError as exc:
            raise ProfileUnavailableError from exc

        if updated_profile is None:
            raise ProfileNotFoundError

        return ProfileResponse.model_validate(updated_profile)
