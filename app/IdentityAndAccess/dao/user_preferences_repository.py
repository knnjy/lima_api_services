import logging

import httpx
from postgrest.exceptions import APIError
from supabase import Client


logger = logging.getLogger(__name__)


class UserPreferencesDataAccessError(Exception):
    pass


class UserPreferencesAlreadyExistsDataError(Exception):
    pass


class UserPreferencesRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def get_by_user_id(self, user_id: str) -> dict[str, object] | None:
        try:
            response = (
                self._client.table("user_preferences")
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("User preferences lookup failed")
            raise UserPreferencesDataAccessError from exc

        return response.data[0] if response.data else None

    def create(
        self,
        preferences_data: dict[str, object],
    ) -> dict[str, object]:
        try:
            response = (
                self._client.table("user_preferences")
                .insert(preferences_data)
                .select("*")
                .execute()
            )
        except APIError as exc:
            if exc.code == "23505":
                raise UserPreferencesAlreadyExistsDataError from exc
            logger.exception("User preferences creation failed")
            raise UserPreferencesDataAccessError from exc
        except httpx.HTTPError as exc:
            logger.exception("User preferences creation request failed")
            raise UserPreferencesDataAccessError from exc

        if not response.data:
            raise UserPreferencesDataAccessError(
                "User preferences insert returned no row"
            )
        return response.data[0]

    def update_by_user_id(
        self,
        user_id: str,
        preferences_data: dict[str, object],
    ) -> dict[str, object] | None:
        try:
            response = (
                self._client.table("user_preferences")
                .update(preferences_data)
                .eq("user_id", user_id)
                .select("*")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("User preferences update failed")
            raise UserPreferencesDataAccessError from exc

        return response.data[0] if response.data else None
