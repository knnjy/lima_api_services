import hashlib
import secrets
from html import escape
from uuid import UUID

from app.common.services.email_service import EmailDeliveryError, EmailService
from app.Farm.FarmInvitations.dao.farm_invitation_repository import (
    FarmInvitationDataAccessError,
    PendingFarmInvitationExistsError,
    FarmInvitationRepository,
)
from app.Farm.FarmInvitations.dto.farm_invitation_schema import (
    CreatedInvitationResponse,
    FarmInvitationAccept,
    FarmInvitationCreate,
    FarmInvitationCreatedResponse,
    FarmInvitationListResponse,
    FarmInvitationResponse,
)
from app.Farm.FarmManagement.services.farm_service import FARM_ROLE_NAMES


class FarmInvitationUnavailableError(Exception):
    pass


class FarmInvitationAlreadyExistsError(Exception):
    pass


class FarmInvitationNotFoundError(Exception):
    pass


class InvalidFarmInvitationStateError(Exception):
    pass


class FarmInvitationContactMismatchError(Exception):
    pass


class FarmInvitationService:
    def __init__(
        self,
        repository: FarmInvitationRepository,
        email_service: EmailService | None = None,
    ) -> None:
        self._repository = repository
        self._email_service = email_service

    def list_invitations(self, farm_id: UUID) -> list[CreatedInvitationResponse]:
        try:
            rows = self._repository.list_by_farm(str(farm_id))
        except FarmInvitationDataAccessError as exc:
            raise FarmInvitationUnavailableError from exc
        return [CreatedInvitationResponse.model_validate(row) for row in rows]

    def list_received_invitations(
        self,
        email: str,
    ) -> FarmInvitationListResponse:
        try:
            rows = self._repository.list_by_email(email.strip().lower())
        except FarmInvitationDataAccessError as exc:
            raise FarmInvitationUnavailableError from exc
        return FarmInvitationListResponse(
            invitations=[
                FarmInvitationResponse.model_validate(
                    self._include_response_details(row)
                )
                for row in rows
            ]
        )

    def create_invitation(
        self,
        farm_id: UUID,
        invited_by: str,
        invitation: FarmInvitationCreate,
    ) -> FarmInvitationCreatedResponse:
        email_service = None
        if invitation.email:
            email_service = self._email_service or EmailService()
            if not email_service.frontend_url:
                raise FarmInvitationUnavailableError(
                    "FRONTEND_URL is required to send invitation emails"
                )

        token = secrets.token_urlsafe(32)
        invitation_data = invitation.model_dump(mode="json")
        invitation_data.update(
            {
                "farm_id": str(farm_id),
                "invited_by": invited_by,
                "status": "pending",
                "token_hash": hashlib.sha256(token.encode("utf-8")).hexdigest(),
            }
        )
        try:
            row = self._repository.create(invitation_data)
        except PendingFarmInvitationExistsError as exc:
            raise FarmInvitationAlreadyExistsError from exc
        except FarmInvitationDataAccessError as exc:
            raise FarmInvitationUnavailableError from exc
        created_invitation = FarmInvitationCreatedResponse.model_validate(
            {**row, "invitation_token": token}
        )
        if email_service and invitation.email:
            frontend_url = escape(email_service.frontend_url, quote=True)
            farm_id_text = escape(str(farm_id))
            token_text = escape(token)
            role_id_text = str(invitation.role_id)
            html = (
                "<p>A farm owner has invited you to join a farm.</p>"
                f"<p>Farm ID: <strong>{farm_id_text}</strong></p>"
                f"<p>Assigned role ID: <strong>{role_id_text}</strong></p>"
                f'<p><a href="{frontend_url}">Open LiMa</a>, then sign in or '
                "create an account to accept the invitation.</p>"
                f"<p>Your invitation token: <strong>{token_text}</strong></p>"
            )
            text = (
                "A farm owner has invited you to join a farm.\n"
                f"Farm ID: {farm_id}\n"
                f"Assigned role ID: {invitation.role_id}\n"
                f"Open LiMa at {email_service.frontend_url}, then sign in or "
                "create an account to accept the invitation.\n"
                f"Your invitation token: {token}"
            )
            try:
                email_message_id = email_service.send_email(
                    invitation.email,
                    "You are invited to join a farm",
                    html,
                    text,
                )
            except EmailDeliveryError as exc:
                try:
                    cancelled = self._repository.cancel(
                        str(farm_id), str(created_invitation.invitation_id)
                    )
                except FarmInvitationDataAccessError as cancel_exc:
                    raise FarmInvitationUnavailableError(
                        "Invitation email failed and the pending invitation "
                        "could not be cancelled"
                    ) from cancel_exc
                if not cancelled:
                    raise FarmInvitationUnavailableError(
                        "Invitation email failed and the pending invitation "
                        "remains active"
                    ) from exc
                raise FarmInvitationUnavailableError(
                    "Invitation email could not be sent; the invitation was "
                    "cancelled"
                ) from exc
            created_invitation = created_invitation.model_copy(
                update={
                    "email_delivery_status": "accepted_by_provider",
                    "email_message_id": email_message_id,
                }
            )
        return created_invitation

    def cancel_invitation(self, farm_id: UUID, invitation_id: UUID) -> None:
        current = self._get_row(farm_id, invitation_id)
        if current.get("status") != "pending":
            raise InvalidFarmInvitationStateError(
                "Only pending invitations can be cancelled"
            )
        try:
            cancelled = self._repository.cancel(str(farm_id), str(invitation_id))
        except FarmInvitationDataAccessError as exc:
            raise FarmInvitationUnavailableError from exc
        if not cancelled:
            raise FarmInvitationNotFoundError

    def accept_invitation(
        self,
        invitation: FarmInvitationAccept,
    ) -> FarmInvitationResponse:
        token_hash = hashlib.sha256(
            invitation.invitation_token.encode("utf-8")
        ).hexdigest()
        try:
            result = self._repository.accept_by_token_hash(token_hash)
        except FarmInvitationDataAccessError as exc:
            raise FarmInvitationUnavailableError from exc

        result_status = result.get("result")
        if result_status == "not_found":
            raise FarmInvitationNotFoundError
        if result_status == "contact_mismatch":
            raise FarmInvitationContactMismatchError
        if result_status in ("expired", "invalid_state"):
            raise InvalidFarmInvitationStateError(
                "Farm invitation is expired or no longer pending"
            )

        accepted_invitation = result.get("invitation")
        if result_status != "accepted" or not isinstance(accepted_invitation, dict):
            raise FarmInvitationUnavailableError(
                "Farm invitation acceptance returned an invalid response"
            )
        return FarmInvitationResponse.model_validate(
            self._include_response_details(accepted_invitation)
        )

    def _include_response_details(
        self,
        invitation: dict[str, object],
    ) -> dict[str, object]:
        farm_id = invitation.get("farm_id")
        if not isinstance(farm_id, str):
            raise FarmInvitationUnavailableError(
                "Farm invitation returned an invalid farm ID"
            )
        try:
            farm_name = self._repository.get_farm_name(farm_id)
        except FarmInvitationDataAccessError as exc:
            raise FarmInvitationUnavailableError from exc
        if farm_name is None:
            raise FarmInvitationUnavailableError(
                "Farm name could not be found for the invitation"
            )
        try:
            role_name = FARM_ROLE_NAMES[int(invitation["role_id"])]
        except (KeyError, TypeError, ValueError) as exc:
            raise FarmInvitationUnavailableError(
                "Farm invitation returned an invalid role ID"
            ) from exc
        return {
            **invitation,
            "farm_name": farm_name,
            "role": role_name,
        }

    def _get_row(
        self,
        farm_id: UUID,
        invitation_id: UUID,
    ) -> dict[str, object]:
        try:
            row = self._repository.get_by_id(str(farm_id), str(invitation_id))
        except FarmInvitationDataAccessError as exc:
            raise FarmInvitationUnavailableError from exc
        if row is None:
            raise FarmInvitationNotFoundError
        return row
