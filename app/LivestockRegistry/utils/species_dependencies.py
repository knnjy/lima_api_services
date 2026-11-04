from fastapi import Depends

from app.Authentication.dependencies import (
    AuthenticatedUser,
    get_authenticated_user,
)
from app.LivestockRegistry.dao.species_repository import SpeciesRepository
from app.LivestockRegistry.services.species_service import SpeciesService
from app.core.db.supabase_client import create_authenticated_supabase_client


def get_species_service(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> SpeciesService:
    client = create_authenticated_supabase_client(
        authenticated_user.access_token
    )
    return SpeciesService(SpeciesRepository(client))
