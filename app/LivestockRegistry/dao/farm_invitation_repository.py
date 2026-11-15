import logging

import httpx
from postgrest.exceptions import APIError
from supabase import Client


logger = logging.getLogger(__name__)


class FarmInvitationDataAccessError(Exception):
    pass


class PendingFarmInvitationExistsError(Exception):
    pass


class FarmInvitationRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def list_by_farm(self, farm_id: str) -> list[dict[str, object]]:
        try:
            response = (
                self._client.table("farm_invitation")
                .select("*")
                .eq("farm_id", farm_id)
                .order("created_at", desc=True)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Farm invitation list failed")
            raise FarmInvitationDataAccessError from exc
        return response.data

    def get_by_id(
        self,
        farm_id: str,
        invitation_id: str,
    ) -> dict[str, object] | None:
        try:
            response = (
                self._client.table("farm_invitation")
                .select("*")
                .eq("farm_id", farm_id)
                .eq("invitation_id", invitation_id)
                .limit(1)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Farm invitation lookup failed")
            raise FarmInvitationDataAccessError from exc
        return response.data[0] if response.data else None

    def create(self, invitation_data: dict[str, object]) -> dict[str, object]:
        try:
            response = (
                self._client.table("farm_invitation")
                .insert(invitation_data)
                .select("*")
                .execute()
            )
        except APIError as exc:
            if (
                exc.code == "23505"
                and any(
                    constraint in exc.message
                    for constraint in (
                        "uq_invitation_pending_phone",
                        "uq_invitation_pending_email",
                    )
                )
            ):
                raise PendingFarmInvitationExistsError from exc
            logger.exception("Farm invitation insert failed")
            raise FarmInvitationDataAccessError from exc
        except httpx.HTTPError as exc:
            logger.exception("Farm invitation insert failed")
            raise FarmInvitationDataAccessError from exc
        if not response.data:
            raise FarmInvitationDataAccessError(
                "Farm invitation insert returned no row"
            )
        return response.data[0]

    def cancel(self, farm_id: str, invitation_id: str) -> bool:
        try:
            response = (
                self._client.table("farm_invitation")
                .update({"status": "cancelled"})
                .eq("farm_id", farm_id)
                .eq("invitation_id", invitation_id)
                .eq("status", "pending")
                .select("invitation_id")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Farm invitation cancellation failed")
            raise FarmInvitationDataAccessError from exc
        return bool(response.data)
