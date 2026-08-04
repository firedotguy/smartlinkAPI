from app.api import api_call
from app.enums import ItemLocation
from app.models.item import Item, ItemCategory
from app.utils.logger import get_logger
from app.utils.pd import dict2list_validator

l = get_logger("api.inventory")


def get_item_categories() -> dict[int, ItemCategory]:
    l.info("get item categories")
    return {int(id): ItemCategory.model_validate(category) for id, category in api_call("inventory", "get_inventory_catalog")["data"].items()}


def get_customer_items(id: int) -> list[Item]:
    l.info("get customer items id=%s", id)
    return [
        Item.model_validate(item)
        for item in dict2list_validator(api_call("inventory", "get_inventory_amount", location=ItemLocation.customer, object_id=id)["data"])
    ]
