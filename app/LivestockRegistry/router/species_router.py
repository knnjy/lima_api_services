from fastapi import APIRouter

from app.LivestockRegistry.controllers.species_controller import SpeciesController
from app.LivestockRegistry.dto.species_schema import SpeciesResponse

router = APIRouter(prefix="/species", tags=["species"])
species_controller = SpeciesController()

router.add_api_route(
    "",
    species_controller.list_species,
    methods=["GET"],
    response_model=list[SpeciesResponse],
)
router.add_api_route(
    "/{species_id}",
    species_controller.get_species,
    methods=["GET"],
    response_model=SpeciesResponse,
)
