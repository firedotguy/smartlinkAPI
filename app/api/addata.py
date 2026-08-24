from datetime import datetime

from app.api import api_call
from app.enums import AddataObjectType
from app.utils.logger import get_logger

l = get_logger("api.addata")


def set_adddata(id: int, object_type: AddataObjectType, field_id: int, value: str | int | datetime | list | bool):
    if isinstance(value, list):
        value = ",".join(value)
    if isinstance(value, datetime):
        value = value.isoformat()
    l.info("set addata id=%s type=%s field=%s value=%s", id, object_type.value, field_id, value)
    return api_call("additional_data", "change_value", post=True, field_id=field_id, object_id=id, value=value, cat_id=object_type)
