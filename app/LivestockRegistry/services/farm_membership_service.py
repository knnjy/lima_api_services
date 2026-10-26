from app.LivestockRegistry.dao.farm_membership_repository import (
    FarmMembershipDataAccessError,
    FarmMembershipRepository,
)


class FarmMembershipUnavailableError(Exception):
    pass


class FarmMembershipService:
    def __init__(self, repository: FarmMembershipRepository) -> None:
        self._repository = repository

    def get_active_memberships(self, user_id: str) -> list[dict[str, object]]:
        try:
            return self._repository.get_active_memberships(user_id)
        except FarmMembershipDataAccessError as exc:
            raise FarmMembershipUnavailableError from exc
