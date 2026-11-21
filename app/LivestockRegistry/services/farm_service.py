from uuid import UUID

from app.LivestockRegistry.dao.farm_membership_repository import (
    FarmMembershipDataAccessError,
    FarmMembershipRepository,
)
from app.LivestockRegistry.dao.farm_repository import (
    FarmDataAccessError,
    FarmAuthError,
    FarmRepository,
)
from app.LivestockRegistry.dto.farm_membership_schema import FarmMembershipCreate
from app.LivestockRegistry.dto.farm_schema import FarmCreate, FarmResponse, FarmUpdate
from app.LivestockRegistry.errors import FarmNotFoundError


OWNER_ROLE_ID = "1"


class FarmUnavailableError(Exception):
    pass


class FarmAccessDeniedError(Exception):
    pass


class FarmCreationRollbackError(Exception):
    pass


class FarmService:
    def __init__(
        self,
        farm_repository: FarmRepository,
        membership_repository: FarmMembershipRepository,
    ) -> None:
        self._farm_repository = farm_repository
        self._membership_repository = membership_repository

    def list_farms(self, farm_ids: list[str]) -> list[FarmResponse]:
        try:
            rows = self._farm_repository.list_by_ids(farm_ids)
        except FarmDataAccessError as exc:
            raise FarmUnavailableError from exc
        return [FarmResponse.model_validate(row) for row in rows]

    def get_farm(self, farm_id: UUID, farm_ids: list[str]) -> FarmResponse:
        self._require_membership(str(farm_id), farm_ids)
        try:
            row = self._farm_repository.get_by_id(str(farm_id))
        except FarmDataAccessError as exc:
            raise FarmUnavailableError from exc
        if row is None:
            raise FarmNotFoundError
        return FarmResponse.model_validate(row)

    def create_farm(self, farm: FarmCreate, user_id: UUID) -> FarmResponse:
        farm_data = farm.model_dump(mode="json", exclude={"created_by"})
        farm_data["created_by"] = str(user_id)

        try:
            result = self._farm_repository.create(farm_data)
        except FarmDataAccessError as exc:
            raise FarmUnavailableError from exc

        farm_row = result.get("farm")
        if not isinstance(farm_row, dict):
            raise FarmUnavailableError("Farm creation returned an invalid response")

        return FarmResponse.model_validate(farm_row)

    def update_farm(
        self,
        farm_id: UUID,
        farm: FarmUpdate,
        farm_ids: list[str],
        owner_farm_ids: list[str],
    ) -> FarmResponse:
        self._require_membership(str(farm_id), farm_ids)
        self._require_owner(str(farm_id), owner_farm_ids)
        farm_data = farm.model_dump(mode="json", exclude_unset=True)
        if not farm_data:
            raise ValueError("Provide at least one field to update")

        try:
            row = self._farm_repository.update(str(farm_id), farm_data)
        except FarmDataAccessError as exc:
            raise FarmUnavailableError from exc
        if row is None:
            raise FarmNotFoundError
        return FarmResponse.model_validate(row)

    def delete_farm(
        self,
        farm_id: UUID,
        farm_ids: list[str],
        owner_farm_ids: list[str],
    ) -> None:
        self._require_membership(str(farm_id), farm_ids)
        self._require_owner(str(farm_id), owner_farm_ids)
        try:
            deleted = self._farm_repository.delete(str(farm_id))
        except FarmAuthError as exc:
            raise FarmAccessDeniedError from exc
        except FarmNotFoundError:
            raise
        except FarmDataAccessError as exc:
            raise FarmUnavailableError from exc
        if not deleted:
            raise FarmNotFoundError

    @staticmethod
    def _require_membership(farm_id: str, farm_ids: list[str]) -> None:
        if farm_id not in farm_ids:
            raise FarmNotFoundError

    @staticmethod
    def _require_owner(farm_id: str, owner_farm_ids: list[str]) -> None:
        if farm_id not in owner_farm_ids:
            raise FarmAccessDeniedError
