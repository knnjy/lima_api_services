import httpx
from postgrest.exceptions import APIError
from supabase import Client


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
            raise FarmMembershipDataAccessError from exc

        return response.data
