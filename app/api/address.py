from app.api import api_call
from app.models.building import Building
from app.models.province import Province
from app.utils.logger import get_logger
from app.utils.pd import list2model_validator

l = get_logger("api.employee")


def get_provinces():
    l.info("get provinces")
    return [Province.model_validate(province, context=province) for province in api_call("address", "get_province")["data"].values()]


def get_building(id: int) -> Building | None:
    l.info("get building id=%s", id)
    building = api_call("address", "get_house", building_id=id).get("data")

    if building is None:
        l.error("building not found")
        return None

    return Building.model_validate(list2model_validator(building), context=list2model_validator(building))
