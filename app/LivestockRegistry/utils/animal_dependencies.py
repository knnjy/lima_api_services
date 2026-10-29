from fastapi import Depends

from app.LivestockRegistry.dao.animal_repository import AnimalRepository
from app.LivestockRegistry.services.animal_service import AnimalService
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    get_authenticated_farm_user,
)
from app.core.db.supabase_client import create_authenticated_supabase_client


def get_animal_service(
    context: AuthenticatedFarmUser = Depends(get_authenticated_farm_user),
) -> AnimalService:
    client = create_authenticated_supabase_client(
        context.authenticated_user.access_token
    )
    repository = AnimalRepository(client)
    return AnimalService(repository)
