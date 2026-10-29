from app.LivestockRegistry.dao.farm_membership_repository import (
    FarmMembershipDataAccessError,
    FarmMembershipRepository,
)
from app.LivestockRegistry.dto.farm_membership_schema import FarmMembershipCreate


class FarmMembershipUnavailableError(Exception):
    pass


class FarmNotFoundError(Exception):
    pass


class FarmMembershipService:
    def __init__(self, repository: FarmMembershipRepository) -> None:
        self._repository = repository

    def get_active_memberships(self, user_id: str) -> list[dict[str, object]]:
        try:
            return self._repository.get_active_memberships(user_id)
        except FarmMembershipDataAccessError as exc:
            raise FarmMembershipUnavailableError from exc

    def create_membership(
        self, member_data: FarmMembershipCreate
    ) -> dict[str, object]:
        try:
            if not self._repository.farm_exists(str(member_data.farm_id)):
                raise FarmNotFoundError

            return self._repository.create_membership(member_data)
        except FarmMembershipDataAccessError as exc:
            raise FarmMembershipUnavailableError from exc
