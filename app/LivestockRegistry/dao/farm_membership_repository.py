import logging

import httpx
from postgrest.exceptions import APIError
from supabase import Client

from app.LivestockRegistry.dto.farm_membership_schema import FarmMembershipCreate


logger = logging.getLogger(__name__)


class FarmMembershipDataAccessError(Exception):
    pass


class FarmMembershipRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def get_active_memberships(self, user_id: str) -> list[dict[str, object]]:
        try:
            response = (
                self._client.table("farm_membership")
                .select("*")
                .eq("user_id", user_id)
                .eq("status", "active")
                .order("joined_at")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Farm membership lookup failed")
            raise FarmMembershipDataAccessError from exc

        return response.data

    def farm_exists(self, farm_id: str) -> bool:
        try:
            response = (
                self._client.table("farm")
                .select("farm_id")
                .eq("farm_id", farm_id)
                .limit(1)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Farm existence lookup failed")
            raise FarmMembershipDataAccessError from exc

        return bool(response.data)

    def create_membership(self, member_data: FarmMembershipCreate) -> dict[str, object]:
        try:
            response = (
                self._client.table("farm_membership")
                .insert(
                    {
                        "user_id": str(member_data.user_id),
                        "farm_id": str(member_data.farm_id),
                        "role_id": member_data.role_id,
                    }
                )
                .select("*")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Farm membership insert failed")
            raise FarmMembershipDataAccessError from exc

        if not response.data:
            raise FarmMembershipDataAccessError(
                "Farm membership insert returned no row"
            )
        return response.data[0]
