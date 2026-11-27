from uuid import UUID

from app.common.dependencies.farm_access import FarmRoleMembership
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
from app.LivestockRegistry.dto.farm_schema import (
    FarmCreate,
    FarmListItem,
    FarmListResponse,
    FarmLocation,
    FarmMembershipRole,
    FarmResponse,
    FarmUpdate,
)
from app.LivestockRegistry.errors import FarmNotFoundError


OWNER_ROLE_ID = "1"
FARM_LIST_PAGE_SIZE = 10
FARM_ROLE_NAMES = {1: "Owner", 2: "Worker"}


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

    def list_farms(
        self, memberships: list[FarmRoleMembership]
    ) -> FarmListResponse:
        membership_by_farm_id = {
            membership.farm_id: membership for membership in memberships
        }
        try:
            rows = self._farm_repository.list_by_ids(
                list(membership_by_farm_id)
            )
        except FarmDataAccessError as exc:
            raise FarmUnavailableError from exc

        items = []
        for row in rows[:FARM_LIST_PAGE_SIZE]:
            membership = membership_by_farm_id[str(row["farm_id"])]
            role_id = int(membership.role_id)
            try:
                role_name = FARM_ROLE_NAMES[role_id]
            except KeyError as exc:
                raise ValueError(f"Unsupported farm role ID: {role_id}") from exc
            if membership.membership_id is None:
                raise ValueError(
                    f"Membership ID is missing for farm {membership.farm_id}"
                )

            items.append(
                FarmListItem(
                    farm_id=row["farm_id"],
                    farm_name=row["farm_name"],
                    location=FarmLocation(
                        province=row["province"],
                        city_municipality=row["city_municipality"],
                        address_line=row.get("address_line"),
                    ),
                    role=FarmMembershipRole(
                        membership_id=membership.membership_id,
                        role_id=role_id,
                        role_name=role_name,
                    ),
                )
            )

        total = len(rows)
        total_pages = (
            (total + FARM_LIST_PAGE_SIZE - 1) // FARM_LIST_PAGE_SIZE
        )
        return FarmListResponse(
            data=items,
            meta={
                "page": 1,
                "page_size": FARM_LIST_PAGE_SIZE,
                "total": total,
                "total_pages": total_pages,
            },
        )

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
