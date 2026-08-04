from datetime import date, datetime
from enum import Enum
from json import loads
from re import fullmatch
from typing import Annotated, Any, TypeVar, cast

from pydantic import BaseModel, BeforeValidator, PlainSerializer, PlainValidator, ValidationInfo

from app.utils.coords import from_polygon


def int2bool_validator(value: int | bool) -> bool:
    return bool(value)


int2bool = Annotated[bool, BeforeValidator(int2bool_validator)]


T = TypeVar("T")


def dict2list_validator(value: dict[str | int, T] | list[T]) -> list[T]:
    if isinstance(value, list):
        return value
    return list(value.values())


dict2list = Annotated[list[T], BeforeValidator(dict2list_validator)]


def str2date_validator(value: str) -> date | None:
    if not value or value == "-":
        return None
    if "." in value:
        return date.strptime(value, "%d.%m.%Y")  # ty: ignore # false, it exists
    return date.strptime(value, "%Y-%m-%d")  # ty: ignore


def str2datetime_validator(value: str) -> datetime | None:
    if not value or value == "-":
        return None
    if fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", value):
        return datetime.strptime(value, "%Y-%m-%d %H:%M")
    if fullmatch(r"\d{2}.\d{2}.\d{4} \d{2}:\d{2}", value):
        return datetime.strptime(value, "%d.%m.%Y %H:%M")
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def phone_validator(value: str | dict) -> int | None:
    if isinstance(value, dict):
        value = value["number"]
    value = value.replace(" ", "").replace("(", "").replace(")", "")
    if value.startswith("+996"):
        value = value.split("+996")[1]
    if value.startswith("996"):
        value = value.split("996")[1]
    if not value:
        return None
    return int(value)


Phone = Annotated[int, BeforeValidator(phone_validator)]
NullablePhone = Annotated[int | None, BeforeValidator(phone_validator)]


def coordinates_validator(value: dict[str, float] | list[list[float]]) -> list[float] | None:
    if isinstance(value, list):
        return from_polygon(value)
    return [value["lat"], value["lon"]]


Coordinates = Annotated[list[float] | None, BeforeValidator(coordinates_validator)]


T = TypeVar("T")


def list2model_validator(value: list[T] | dict[str, T]) -> T | None:
    if isinstance(value, list):
        if value:
            return value[0]
    else:
        return next(iter(value.values()), None)


list2model = Annotated[T, BeforeValidator(list2model_validator)]


def addata(id: int, *other_ids: int) -> BeforeValidator:
    ids = list(other_ids)
    ids.append(id)

    def addata_validator(_: dict, info: ValidationInfo):
        assert info.context

        for id in ids:
            if str(id) in info.context.get("additional_data", []):
                v = info.context["additional_data"][str(id)]
                if isinstance(v, dict):
                    return v["value"]
                return v

    return BeforeValidator(addata_validator)


def str2list_validator(value: str | None) -> list:
    if value is None:
        return []
    return loads(value)


str2list = Annotated[list, BeforeValidator(str2list_validator)]


T = TypeVar("T", bound=Enum)


def date2str_serializer(value: date | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y.%m.%d")


date2str = Annotated[date, PlainSerializer(date2str_serializer)]


def datetime2str_serializer(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y.%m.%d %H:%M:%S")


T = TypeVar("T", bound=BaseModel)


def models2dict_serializer(value: list[T]) -> list[dict[str, Any]]:
    return [cast(BaseModel, item).model_dump() for item in value]


# 4 because it 2+2
str4datetime = Annotated[datetime, PlainValidator(str2datetime_validator), PlainSerializer(datetime2str_serializer)]
str4date = Annotated[date, PlainValidator(str2date_validator), PlainSerializer(date2str_serializer)]

T = TypeVar("T", bound=BaseModel)
dict2models = Annotated[list[T], BeforeValidator(dict2list_validator), PlainSerializer(models2dict_serializer)]
