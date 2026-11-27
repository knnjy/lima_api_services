from fastapi import APIRouter, status

from app.Farm.FarmInvitations.controllers.farm_invitation_controller import (
    FarmInvitationController,
)
from app.Farm.FarmInvitations.dto.farm_invitation_schema import (
    CreatedInvitationResponse,
    FarmInvitationCreatedResponse,
    FarmInvitationListResponse,
    FarmInvitationResponse,
)

router = APIRouter(
    prefix="/farms/{farm_id}/invitations",
    tags=["farm-invitations"],
)
invitation_controller = FarmInvitationController()
accept_router = APIRouter(prefix="/invitations", tags=["farm-invitations"])

accept_router.add_api_route(
    "",
    invitation_controller.list_received_invitations,
    methods=["GET"],
    response_model=FarmInvitationListResponse,
)

accept_router.add_api_route(
    "/accept",
    invitation_controller.accept_invitation,
    methods=["POST"],
    response_model=FarmInvitationResponse,
)

router.add_api_route(
    "",
    invitation_controller.list_invitations,
    methods=["GET"],
    response_model=list[CreatedInvitationResponse],
)
router.add_api_route(
    "",
    invitation_controller.create_invitation,
    methods=["POST"],
    response_model=FarmInvitationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/{invitation_id}",
    invitation_controller.cancel_invitation,
    methods=["POST"],
    status_code=status.HTTP_204_NO_CONTENT,
)

