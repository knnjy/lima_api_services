from fastapi import APIRouter, status

from app.Farm.FarmManagement.controllers.farm_controller import FarmController
from app.Farm.FarmManagement.dto.farm_schema import FarmListResponse, FarmResponse

router = APIRouter(prefix="/farms", tags=["farms"])
farm_controller = FarmController()

router.add_api_route(
    "",
    farm_controller.list_farms,
    methods=["GET"],
    response_model=FarmListResponse,
)
router.add_api_route(
    "",
    farm_controller.create_farm,
    methods=["POST"],
    response_model=FarmResponse,
    status_code=status.HTTP_201_CREATED,
)
router.add_api_route(
    "/{farm_id}",
    farm_controller.get_farm,
    methods=["GET"],
    response_model=FarmResponse,
)
router.add_api_route(
    "/{farm_id}",
    farm_controller.update_farm,
    methods=["PATCH"],
    response_model=FarmResponse,
)
router.add_api_route(
    "/{farm_id}",
    farm_controller.delete_farm,
    methods=["DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
)