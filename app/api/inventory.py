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


def get_employee_items(id: int) -> list[Item]:
    l.info("get employee items id=%s", id)
    return [
        Item.model_validate(item)
        for item in dict2list_validator(api_call("inventory", "get_inventory_amount", location=ItemLocation.storage, object_id=id)["data"])
    ]


def get_task_items(id: int) -> list[Item]:
    l.info("get task items id=%s", id)
    return [
        Item.model_validate(item)
        for item in dict2list_validator(api_call("inventory", "get_inventory_amount", location=ItemLocation.task, object_id=id)["data"])
    ]


def split_inventory(id: int, amount: int) -> int:
    l.info("split inventory id=%s amount=%s", id, amount)
    return api_call("inventory", "split_inventory", post=True, id=id, amount=amount)["new_id"]


def transfer_inventory(id: int, destination: str, employee_id: int):  # id not list because userside always transfers only first item
    l.info("transfer inventory id=%s dst=%s employee_id=%s", id, destination, employee_id)
    api_call("inventory", "transfer_inventory", post=True, inventory_id=id, dst_account=destination, employee_id=employee_id)


def get_employees_inventory_ids() -> dict[str, int]:
    l.info("get employees inventory ids")
    return {inventory["name"]: int(id) for id, inventory in api_call("inventory", "get_inventory_storage")["data"].items()}
