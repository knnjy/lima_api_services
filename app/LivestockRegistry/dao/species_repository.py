import httpx
from postgrest.exceptions import APIError
from supabase import Client


class SpeciesDataAccessError(Exception):
    pass


class SpeciesRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def list_all(self) -> list[dict[str, object]]:
        try:
            response = (
                self._client.table("species")
                .select("*")
                .order("species_id")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise SpeciesDataAccessError from exc
        return response.data

    def get_by_id(self, species_id: int) -> dict[str, object] | None:
        try:
            response = (
                self._client.table("species")
                .select("*")
                .eq("species_id", species_id)
                .limit(1)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise SpeciesDataAccessError from exc
        return response.data[0] if response.data else None
