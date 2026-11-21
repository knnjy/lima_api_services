from fastapi import Depends, HTTPException, status

from app.Authentication.dependencies import (
    AuthenticatedUser,
    get_authenticated_user,
)
from app.IdentityAndAccess.dto.profile_schema import (
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdate,
)
from app.IdentityAndAccess.services.profile_service import (
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
    ProfileService,
    ProfileUnavailableError,
)
from app.IdentityAndAccess.utils.profile_dependencies import get_profile_service


class ProfileController:
    def get_my_profile(
        self,
        authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
        profile_service: ProfileService = Depends(get_profile_service),
    ) -> ProfileResponse:
        try:
            return profile_service.get_profile(authenticated_user.user.id)
        except ProfileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found",
            ) from exc
        except ProfileUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Profile service is unavailable",
            ) from exc

    def create_my_profile(
        self,
        profile: ProfileCreateRequest,
        authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
        profile_service: ProfileService = Depends(get_profile_service),
    ) -> ProfileResponse:
        try:
            return profile_service.create_profile(
                profile,
                authenticated_user.user.id,
            )
        except ProfileAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Profile already exists",
            ) from exc
        except ProfileUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Profile service is unavailable",
            ) from exc

    def update_my_profile(
        self,
        profile: ProfileUpdate,
        authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
        profile_service: ProfileService = Depends(get_profile_service),
    ) -> ProfileResponse:
        try:
            return profile_service.update_profile(
                profile,
                authenticated_user.user.id,
            )
        except ProfileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found",
            ) from exc
        except ProfileUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Profile service is unavailable",
            ) from exc