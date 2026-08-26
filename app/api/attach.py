from app.api import api_call
from app.enums import AttachObjectType
from app.models.attach import Attach
from app.utils.logger import get_logger
from app.utils.pd import dict2list_validator

l = get_logger("api.attach")


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


def upload_attach(object_id: int, object_type: AttachObjectType, file: tuple[str, bytes, str]):
    l.info("upload attach object_id=%s object_type=%s filename=%s content_type=%s", object_id, object_type, file[0], file[2])
    return api_call("attach", "upload", post=True, file=file, object_id=object_id, object_type=object_type, comment="Загружено через smartlinkAPI")["file_uuid"]


def get_attach(id: str) -> bytes:
    return api_call("attach", "get_file", raw=True, uuid=id)
