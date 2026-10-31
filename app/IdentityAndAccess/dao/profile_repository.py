import logging

import httpx
from postgrest.exceptions import APIError
from supabase import Client


logger = logging.getLogger(__name__)


class ProfileDataAccessError(Exception):
    pass


class ProfileAlreadyExistsDataError(Exception):
    pass


class ProfileRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def get_by_user_id(self, user_id: str) -> dict[str, object] | None:
        try:
            response = (
                self._client.table("profile")
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Profile lookup failed")
            raise ProfileDataAccessError from exc

        return response.data[0] if response.data else None

    def create(self, profile_data: dict[str, object]) -> dict[str, object]:
        try:
            response = (
                self._client.table("profile")
                .insert(profile_data)
                .select("*")
                .execute()
            )
        except APIError as exc:
            if exc.code == "23505":
                raise ProfileAlreadyExistsDataError from exc
            logger.exception("Profile creation failed")
            raise ProfileDataAccessError from exc
        except httpx.HTTPError as exc:
            logger.exception("Profile creation request failed")
            raise ProfileDataAccessError from exc

        if not response.data:
            raise ProfileDataAccessError("Profile insert returned no row")
        return response.data[0]

    def update_by_user_id(
        self,
        user_id: str,
        profile_data: dict[str, object],
    ) -> dict[str, object] | None:
        try:
            response = (
                self._client.table("profile")
                .update(profile_data)
                .eq("user_id", user_id)
                .select("*")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Profile update failed")
            raise ProfileDataAccessError from exc

        return response.data[0] if response.data else None
