import httpx
from postgrest.exceptions import APIError
from supabase import Client


class AnimalGroupDataAccessError(Exception):
    pass


class AnimalGroupRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def list_by_farms(self, farm_ids: list[str]) -> list[dict[str, object]]:
        try:
            response = (
                self._client.table("animal_group")
                .select("*")
                .in_("farm_id", farm_ids)
                .order("created_at", desc=True)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise AnimalGroupDataAccessError from exc
        return response.data

    def get_by_id(
        self,
        animal_group_id: str,
        farm_ids: list[str],
    ) -> dict[str, object] | None:
        try:
            response = (
                self._client.table("animal_group")
                .select("*")
                .eq("animal_group_id", animal_group_id)
                .in_("farm_id", farm_ids)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise AnimalGroupDataAccessError from exc
        return response.data[0] if response.data else None

    def create(self, animal_group_data: dict[str, object]) -> dict[str, object]:
        try:
            response = (
                self._client.table("animal_group")
                .insert(animal_group_data)
                .select("*")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise AnimalGroupDataAccessError from exc
        if not response.data:
            raise AnimalGroupDataAccessError("Animal group insert returned no row")
        return response.data[0]

    def update(
        self,
        animal_group_id: str,
        farm_ids: list[str],
        animal_group_data: dict[str, object],
    ) -> dict[str, object] | None:
        try:
            response = (
                self._client.table("animal_group")
                .update(animal_group_data)
                .eq("animal_group_id", animal_group_id)
                .in_("farm_id", farm_ids)
                .select("*")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise AnimalGroupDataAccessError from exc
        return response.data[0] if response.data else None

    def delete(self, animal_group_id: str, farm_ids: list[str]) -> bool:
        try:
            response = (
                self._client.table("animal_group")
                .delete()
                .eq("animal_group_id", animal_group_id)
                .in_("farm_id", farm_ids)
                .select("animal_group_id")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise AnimalGroupDataAccessError from exc
        return bool(response.data)
