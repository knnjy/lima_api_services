from fastapi import APIRouter, status

from app.LivestockRegistry.controllers.animal_controller import AnimalController
from app.LivestockRegistry.dto.animal_response import AnimalResponse

router = APIRouter(prefix="/me/animals", tags=["animals"])
animal_controller = AnimalController()

router.add_api_route(
    "",
    animal_controller.list_animals,
    methods=["GET"],
    response_model=list[AnimalResponse],
)
router.add_api_route(
    "",
    animal_controller.create_animal,
    methods=["POST"],
    response_model=AnimalResponse,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/{animal_id}",
    animal_controller.get_animal,
    methods=["GET"],
    response_model=AnimalResponse,
)
router.add_api_route(
    "/{animal_id}",
    animal_controller.update_animal,
    methods=["PATCH"],
    response_model=AnimalResponse,
)
router.add_api_route(
    "/{animal_id}",
    animal_controller.delete_animal,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)