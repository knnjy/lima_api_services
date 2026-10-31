from fastapi import APIRouter, status

from app.IdentityAndAccess.controllers.profile_controller import (
    ProfileController,
)
from app.IdentityAndAccess.controllers.user_preferences_controller import (
    UserPreferencesController,
)
from app.IdentityAndAccess.dto.profile_schema import ProfileResponse
from app.IdentityAndAccess.dto.user_preferences_schema import (
    UserPreferencesResponse,
    UserViewResponse,
)


router = APIRouter(prefix="/me", tags=["me"])
controller = ProfileController()
preferences_controller = UserPreferencesController()

router.add_api_route(
    "/profile",
    controller.get_my_profile,
    methods=["GET"],
    response_model=ProfileResponse,
)

router.add_api_route(
    "",
    preferences_controller.get_my_user_view,
    methods=["GET"],
    response_model=UserViewResponse,
)

router.add_api_route(
    "/preferences",
    preferences_controller.get_my_user_preferences,
    methods=["GET"],
    response_model=UserPreferencesResponse,
)

router.add_api_route(
    "/preferences",
    preferences_controller.create_my_user_preferences,
    methods=["POST"],
    response_model=UserPreferencesResponse,
    status_code=status.HTTP_201_CREATED,
)

router.add_api_route(
    "/preferences",
    preferences_controller.update_my_user_preferences,
    methods=["PATCH"],
    response_model=UserPreferencesResponse,
)

router.add_api_route(
    "/profile",
    controller.create_my_profile,
    methods=["POST"],
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
)

router.add_api_route(
    "/profile",
    controller.update_my_profile,
    methods=["PATCH"],
    response_model=ProfileResponse,
)
