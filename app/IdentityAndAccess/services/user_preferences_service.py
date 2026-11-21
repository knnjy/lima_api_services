from uuid import UUID

from app.IdentityAndAccess.dao.user_preferences_repository import (
    UserPreferencesAlreadyExistsDataError,
    UserPreferencesDataAccessError,
    UserPreferencesRepository,
)
from app.IdentityAndAccess.dto.user_preferences_schema import (
    UserPreferencesCreate,
    UserPreferencesCreateRequest,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)


class UserPreferencesNotFoundError(Exception):
    pass


class UserPreferencesUnavailableError(Exception):
    pass


class UserPreferencesAlreadyExistsError(Exception):
    pass


class UserPreferencesService:
    def __init__(self, repository: UserPreferencesRepository) -> None:
        self._repository = repository

    def get_user_preferences(self, user_id: UUID) -> UserPreferencesResponse:
        try:
            row = self._repository.get_by_user_id(str(user_id))
        except UserPreferencesDataAccessError as exc:
            raise UserPreferencesUnavailableError from exc

        if row is None:
            raise UserPreferencesNotFoundError

        return UserPreferencesResponse.model_validate(row)

    def create_user_preferences(
        self,
        preferences: UserPreferencesCreateRequest,
        user_id: UUID,
    ) -> UserPreferencesResponse:
        try:
            if self._repository.get_by_user_id(str(user_id)) is not None:
                raise UserPreferencesAlreadyExistsError
            created_preferences = self._repository.create(
                UserPreferencesCreate(
                    user_id=user_id,
                    **preferences.model_dump(),
                ).model_dump(mode="json")
            )
        except UserPreferencesAlreadyExistsDataError as exc:
            raise UserPreferencesAlreadyExistsError from exc
        except UserPreferencesDataAccessError as exc:
            raise UserPreferencesUnavailableError from exc

        return UserPreferencesResponse.model_validate(created_preferences)

    def update_user_preferences(
        self,
        preferences: UserPreferencesUpdate,
        user_id: UUID,
    ) -> UserPreferencesResponse:
        try:
            updated_preferences = self._repository.update_by_user_id(
                str(user_id),
                preferences.model_dump(mode="json", exclude_unset=True),
            )
        except UserPreferencesDataAccessError as exc:
            raise UserPreferencesUnavailableError from exc

        if updated_preferences is None:
            raise UserPreferencesNotFoundError

        return UserPreferencesResponse.model_validate(updated_preferences)
