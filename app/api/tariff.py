from app.api import api_call
from app.models.tariff import Tariff
from app.utils.logger import get_logger

l = get_logger("api.tariff")


def get_tariffs() -> dict[int, Tariff]:
    l.info("get tariffs")
    return {int(tariff["billing_uuid"]): Tariff.new(tariff["name"]) for tariff in api_call("tariff", "get")["data"].values()}
