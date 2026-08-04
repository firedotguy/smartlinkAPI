from app.api import api_call
from app.enums import AttachObjectType
from app.models.attach import Attach
from app.utils.logger import get_logger
from app.utils.pd import dict2list_validator

l = get_logger("api.employee")


def get_customer_attachs(id: int) -> list[Attach]:
    l.info("get customer attachs id=%s", id)
    return [
        Attach.model_validate(attach, context=attach)
        for attach in dict2list_validator(api_call("attach", "get", object_id=id, object_type=AttachObjectType.customer)["data"])
    ]


def get_task_attachs(id: int):
    l.info("get task attachs id=%s", id)
    return [
        Attach.model_validate(attach, context=attach)
        for attach in dict2list_validator(api_call("attach", "get", object_id=id, object_type=AttachObjectType.task)["data"])
    ]
