from app.api import api_call
from app.models.item import Olt
from app.utils.logger import get_logger

l = get_logger("api.device")


def get_customer_olt(id: int) -> int | None:
    l.info("get customer olt id=%s", id)
    olt = api_call("commutation", "get_data", object_type="customer", object_id=id, is_finish_data=True)["data"]

    if "finish" not in olt or olt["finish"].get("object_type") != "switch":
        l.warning("customer olt not found")
        return None

    return olt["finish"]["object_id"]


def get_ont_olt(sn: str) -> int | None:
    l.info("get ont's olt sn=%s", sn)
    ont = api_call("device", "get_ont_data", id=sn)["data"]

    if isinstance(ont, dict) and "device_id" in ont:
        return ont["device_id"]

    l.error("ont not found")


def get_olts() -> dict[int, Olt]:
    l.info("get olts")
    return {
        int(id): Olt.model_validate(olt)
        for id, olt in api_call("device", "get_data", object_type="olt", is_hide_ifaces_data=True)["data"].items()
        if olt["host"]
    }
