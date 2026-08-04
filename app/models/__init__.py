from enum import Enum
from html import unescape

from pydantic import BaseModel as PDBaseModel
from pydantic import ConfigDict, field_validator


class BaseModel(PDBaseModel):
    @field_validator("*", mode="after")
    def validate(cls, value):
        # if "str" in str(cast(FieldInfo, cls.model_fields[info.field_name]).annotation):  # genius (right side will be like "<class 'str'>" or "str | None") # wait i can just check value type i am stupid
        if value in ("n&#047;a", "n/a", "", "-"):
            return None
        if isinstance(value, str):
            return unescape(value.replace("flat", "кв.").strip())
        return value

    model_config = ConfigDict(json_encoders={Enum: lambda e: e.name})
