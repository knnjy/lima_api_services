from fastapi import Depends, HTTPException, status

from app.Authentication.dependencies import (
    AuthenticatedUser,
    get_authenticated_user,
)
from app.IdentityAndAccess.dto.user_preferences_schema import (
    UserPreferencesCreateRequest,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserViewResponse,
)
from app.IdentityAndAccess.services.user_preferences_service import (
    UserPreferencesAlreadyExistsError,
    UserPreferencesNotFoundError,
    UserPreferencesService,
    UserPreferencesUnavailableError,
)
from app.IdentityAndAccess.services.user_view_service import (
    UserViewNotFoundError,
    UserViewService,
    UserViewUnavailableError,
)
from app.IdentityAndAccess.utils.user_preferences_dependencies import (
    get_user_preferences_service,
    get_user_view_service,
)


class UserPreferencesController:
    def get_my_user_preferences(
        self,
        authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
        preferences_service: UserPreferencesService = Depends(
            get_user_preferences_service
        ),
    ) -> UserPreferencesResponse:
        try:
            return preferences_service.get_user_preferences(
                authenticated_user.user.id
            )
        except UserPreferencesNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found",
            ) from exc
        except UserPreferencesUnavailableError as exc:
            raise self._unavailable_error() from exc

    def create_my_user_preferences(
        self,
        preferences: UserPreferencesCreateRequest,
        authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
        preferences_service: UserPreferencesService = Depends(
            get_user_preferences_service
        ),
    ) -> UserPreferencesResponse:
        try:
            return preferences_service.create_user_preferences(
                preferences,
                authenticated_user.user.id,
            )
        except UserPreferencesAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User preferences already exist",
            ) from exc
        except UserPreferencesUnavailableError as exc:
            raise self._unavailable_error() from exc

    def update_my_user_preferences(
        self,
        preferences: UserPreferencesUpdate,
        authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
        preferences_service: UserPreferencesService = Depends(
            get_user_preferences_service
        ),
    ) -> UserPreferencesResponse:
        try:
            return preferences_service.update_user_preferences(
                preferences,
                authenticated_user.user.id,
            )
        except UserPreferencesNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found",
            ) from exc
        except UserPreferencesUnavailableError as exc:
            raise self._unavailable_error() from exc

    def get_my_user_view(
        self,
        authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
        user_view_service: UserViewService = Depends(get_user_view_service),
    ) -> UserViewResponse:
        try:
            return user_view_service.get_user_view(
                authenticated_user.user.id
            )
        except UserViewNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile or user preferences not found",
            ) from exc
        except UserViewUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="User profile view is unavailable",
            ) from exc

    @staticmethod
    def _unavailable_error() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User preferences service is unavailable",
        )
