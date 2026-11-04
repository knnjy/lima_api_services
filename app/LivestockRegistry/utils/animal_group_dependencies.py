from fastapi import Depends

from app.LivestockRegistry.dao.animal_group_repository import AnimalGroupRepository
from app.LivestockRegistry.services.animal_group_service import AnimalGroupService
from app.LivestockRegistry.dao.species_repository import SpeciesRepository
from app.LivestockRegistry.services.species_service import SpeciesService
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    get_authenticated_farm_user,
)
from app.core.db.supabase_client import create_authenticated_supabase_client


def get_animal_group_service(
    context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
) -> AnimalGroupService:
    client = create_authenticated_supabase_client(
        context.authenticated_user.access_token
    )
    repository = AnimalGroupRepository(client)
    species_service = SpeciesService(SpeciesRepository(client))
    return AnimalGroupService(repository, species_service)
