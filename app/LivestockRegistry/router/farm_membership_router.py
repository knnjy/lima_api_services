from fastapi import APIRouter

from app.LivestockRegistry.controllers.farm_membership_controllers import (
    FarmMembershipController,
)
router = APIRouter(prefix="/me", tags=["me"])

controller = FarmMembershipController()

router.add_api_route(
    "/farms",
    controller.get_my_farm_memberships,
    methods=["GET"],
    response_model=list[dict],
)