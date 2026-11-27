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

    def list_by_email(self, email: str) -> list[dict[str, object]]:
        try:
            response = (
                self._client.table("farm_invitation")
                .select("*")
                .eq("email", email)
                .order("created_at", desc=True)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Farm invitation recipient list failed")
            raise FarmInvitationDataAccessError from exc
        return self._include_inviter_emails(response.data)

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

    def accept_by_token_hash(self, token_hash: str) -> dict[str, object]:
        try:
            response = self._client.rpc(
                "accept_farm_invitation",
                {"p_token_hash": token_hash},
            ).execute()
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Farm invitation acceptance failed")
            raise FarmInvitationDataAccessError from exc
        if not isinstance(response.data, dict):
            raise FarmInvitationDataAccessError(
                "Farm invitation acceptance returned an invalid response"
            )
        result = dict(response.data)
        invitation = result.get("invitation")
        if isinstance(invitation, dict):
            result["invitation"] = self._include_inviter_emails([invitation])[0]
        return result

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
        return self._include_inviter_emails(response.data)[0]

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

    def _include_inviter_emails(
        self,
        invitations: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        membership_ids = sorted(
            {
                str(invitation["invited_by"])
                for invitation in invitations
                if invitation.get("invited_by") is not None
            }
        )
        if not membership_ids:
            return [
                {**invitation, "invited_by_email": None}
                for invitation in invitations
            ]

        try:
            memberships = (
                self._client.table("farm_membership")
                .select("id,user_id")
                .in_("id", membership_ids)
                .execute()
                .data
            )
            user_ids = sorted(
                {
                    str(membership["user_id"])
                    for membership in memberships
                    if membership.get("user_id") is not None
                }
            )
            profiles = (
                self._client.table("profile")
                .select("user_id,email")
                .in_("user_id", user_ids)
                .execute()
                .data
                if user_ids
                else []
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Farm invitation sender lookup failed")
            raise FarmInvitationDataAccessError from exc

        user_ids_by_membership = {
            str(membership["id"]): str(membership["user_id"])
            for membership in memberships
            if membership.get("id") is not None
            and membership.get("user_id") is not None
        }
        emails_by_user = {
            str(profile["user_id"]): profile.get("email")
            for profile in profiles
            if profile.get("user_id") is not None
        }
        enriched_invitations = []
        for invitation in invitations:
            user_id = user_ids_by_membership.get(
                str(invitation.get("invited_by"))
            )
            enriched_invitations.append(
                {
                    **invitation,
                    "invited_by_email": (
                        emails_by_user.get(user_id) if user_id else None
                    ),
                }
            )
        return enriched_invitations

