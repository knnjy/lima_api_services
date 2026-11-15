import hashlib
import secrets
from uuid import UUID

from app.LivestockRegistry.dao.farm_invitation_repository import (
    FarmInvitationDataAccessError,
    PendingFarmInvitationExistsError,
    FarmInvitationRepository,
)
from app.LivestockRegistry.dto.farm_invitation_schema import (
    FarmInvitationCreate,
    FarmInvitationCreatedResponse,
    FarmInvitationResponse,
)


class FarmInvitationUnavailableError(Exception):
    pass


class FarmInvitationAlreadyExistsError(Exception):
    pass


class FarmInvitationNotFoundError(Exception):
    pass


class InvalidFarmInvitationStateError(Exception):
    pass


class FarmInvitationService:
    def __init__(self, repository: FarmInvitationRepository) -> None:
        self._repository = repository

    def list_invitations(self, farm_id: UUID) -> list[FarmInvitationResponse]:
        try:
            rows = self._repository.list_by_farm(str(farm_id))
        except FarmInvitationDataAccessError as exc:
            raise FarmInvitationUnavailableError from exc
        return [FarmInvitationResponse.model_validate(row) for row in rows]

    def create_invitation(
        self,
        farm_id: UUID,
        invited_by: str,
        invitation: FarmInvitationCreate,
    ) -> FarmInvitationCreatedResponse:
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
        return FarmInvitationCreatedResponse.model_validate(
            {**row, "invitation_token": token}
        )

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
