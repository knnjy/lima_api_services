import logging

import httpx
from postgrest.exceptions import APIError
from supabase import Client

from app.LivestockRegistry.errors import FarmNotFoundError

logger = logging.getLogger(__name__)


class FarmDataAccessError(Exception):
    pass


class FarmAuthError(Exception):
    pass


class FarmRepository:
    def __init__(self, supabase_client: Client) -> None:
        self._supabase_client = supabase_client

    def list_by_ids(self, farm_ids: list[str]) -> list[dict[str, object]]:
        if not farm_ids:
            return []

        try:
            response = (
                self._supabase_client.table("farm")
                .select("*")
                .in_("farm_id", farm_ids)
                .order("created_at", desc=True)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("Farm list query failed")
            raise FarmDataAccessError from exc
        return response.data

    def get_by_id(self, farm_id: str) -> dict[str, object] | None:
        try:
            response = (
                self._supabase_client.table("farm")
                .select("*")
                .eq("farm_id", farm_id)
                .limit(1)
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise FarmDataAccessError from exc
        return response.data[0] if response.data else None

    def create(self, farm_data: dict[str, object]) -> dict[str, object]:
        try:
            response = self._supabase_client.rpc(
                "create_farm",
                {
                    "p_farm_name": farm_data["farm_name"],
                    "p_province":  farm_data["province"],
                    "p_city":      farm_data["city_municipality"],
                    "p_address":   farm_data.get("address_line"),
                },
            ).execute()
        except (APIError, httpx.HTTPError) as exc:
            logger.exception("create_farm failed")
            raise FarmDataAccessError from exc
        if not response.data:
            raise FarmDataAccessError("create_farm returned no data")
        return response.data  # {"farm": {...}, "membership": {...}}
    
    def update(
        self,
        farm_id: str,
        farm_data: dict[str, object],
    ) -> dict[str, object] | None:
        try:
            response = (
                self._supabase_client.table("farm")
                .update(farm_data)
                .eq("farm_id", farm_id)
                .select("*")
                .execute()
            )
        except (APIError, httpx.HTTPError) as exc:
            raise FarmDataAccessError from exc
        return response.data[0] if response.data else None


    def delete(self, farm_id: str) -> dict[str, object]:
        try:
            response = self._supabase_client.rpc(
                "delete_farm", {"p_farm_id": farm_id}
            ).execute()
        except APIError as exc:
            logger.exception("delete_farm failed (code=%s)", exc.code)
            if exc.code == "P0002":
                raise FarmNotFoundError from exc
            if exc.code == "28000":
                raise FarmAuthError from exc
            raise FarmDataAccessError from exc
        except httpx.HTTPError as exc:
            logger.exception("delete_farm request failed")
            raise FarmDataAccessError from exc

        if not response.data:
            raise FarmDataAccessError("delete_farm returned no data")
        return response.data      # {"action": "deleted" | "deactivated", "farm_id": "..."}