import httpx
from postgrest.exceptions import APIError
from supabase import Client


class AnimalDataAccessError(Exception):
    pass


class AnimalRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def list_by_farms(self, farm_ids: list[str]) -> list[dict[str, object]]:
        try:
            response = (
                self._client.table("animal")
                .select("*")
                .in_("farm_id", farm_ids)
                .order("created_at", desc=True)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise AnimalDataAccessError from exc
        return response.data

    def get_by_id(
        self,
        animal_id: str,
        farm_ids: list[str],
    ) -> dict[str, object] | None:
        try:
            response = (
                self._client.table("animal")
                .select("*")
                .eq("animal_id", animal_id)
                .in_("farm_id", farm_ids)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise AnimalDataAccessError from exc
        return response.data[0] if response.data else None

    def create(self, animal_data: dict[str, object]) -> dict[str, object]:
        try:
            response = (
                self._client.table("animal")
                .insert(animal_data)
                .select("*")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise AnimalDataAccessError from exc
        if not response.data:
            raise AnimalDataAccessError("Animal insert returned no row")
        return response.data[0]

    def update(
        self,
        animal_id: str,
        farm_ids: list[str],
        animal_data: dict[str, object],
    ) -> dict[str, object] | None:
        try:
            response = (
                self._client.table("animal")
                .update(animal_data)
                .eq("animal_id", animal_id)
                .in_("farm_id", farm_ids)
                .select("*")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise AnimalDataAccessError from exc
        return response.data[0] if response.data else None

    def delete(self, animal_id: str, farm_ids: list[str]) -> bool:
        try:
            response = (
                self._client.table("animal")
                .delete()
                .eq("animal_id", animal_id)
                .in_("farm_id", farm_ids)
                .select("animal_id")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise AnimalDataAccessError from exc
        return bool(response.data)
