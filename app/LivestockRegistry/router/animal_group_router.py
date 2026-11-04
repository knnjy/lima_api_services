from fastapi import APIRouter, status


from app.LivestockRegistry.controllers.animal_group_controller import AnimalGroupController
from app.LivestockRegistry.dto.animal_group_schema import AnimalGroupResponse

router = APIRouter(prefix="/me/animal-groups", tags=["animal-groups"])
animal_group_controller = AnimalGroupController()

router.add_api_route(
    "",
    animal_group_controller.list_animal_groups,
    methods=["GET"],
    response_model=list[AnimalGroupResponse],
)
router.add_api_route(
    "",
    animal_group_controller.create_animal_group,
    methods=["POST"],
    response_model=AnimalGroupResponse,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/{animal_group_id}",
    animal_group_controller.get_animal_group,
    methods=["GET"],
    response_model=AnimalGroupResponse,
)
router.add_api_route(
    "/{animal_group_id}",
    animal_group_controller.update_animal_group,
    methods=["PATCH"],
    response_model=AnimalGroupResponse,
)
router.add_api_route(
    "/{animal_group_id}",
    animal_group_controller.delete_animal_group,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)
