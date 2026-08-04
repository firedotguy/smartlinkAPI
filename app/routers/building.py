from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.address import get_building
from app.api.customer import get_building_customers

router = APIRouter(prefix="/buildings")


@router.get("/{id}")
def api_get_building(id: int):
    building = get_building(id)

    if building is None:
        return JSONResponse({"detail": "building not found"}, 404)

    building.customers = get_building_customers(id)
    return building
