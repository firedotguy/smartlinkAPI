from html import unescape
from ipaddress import IPv4Address
from typing import Annotated

from pydantic import Field, ValidationInfo, field_validator, model_validator

from app.enums import CustomerStatus
from app.models import BaseModel
from app.models.tariff import Tariff
from app.utils import storage
from app.utils.link import make_tgis_link
from app.utils.mac import format_mac
from app.utils.pd import Coordinates, NullablePhone, Phone, addata, date2str, int2bool, list2model, list2model_validator, str4date, str4datetime


class Agreement(BaseModel):
    number: str
    created_at: str4date = Field(validation_alias="date")


class Address(BaseModel):
    id: int | None = Field(None, validation_alias="house_id")
    floor: int | None = None
    entrance: int | None = None
    apartment: str | None = None
    label: str | None = Field(None, validate_default=True)

    @field_validator("apartment", mode="before")
    @classmethod
    def validate_apartment(cls, apartment: dict | None):
        if apartment:
            return apartment["number"]

    @field_validator("id", mode="after")
    @classmethod
    def validate_id(cls, id: int | None):
        if not id:  # if zero, it is none
            return None
        return id

    @field_validator("label", mode="before")
    @classmethod
    def validate_label(cls, _: None, info: ValidationInfo):
        assert info.context
        return info.context.get("label")


class Group(BaseModel):
    id: int
    name: str


_tgis_link = Annotated[str | None, addata(6)]
_connect_type = Annotated[str | None, addata(10)]


class CustomerSearch(BaseModel):
    id: int
    name: str = Field(validation_alias="full_name")
    sn: str | None = Field(None, validate_default=True)
    agreement: str | None = None

    @field_validator("name", mode="after")
    @classmethod
    def validate_name(cls, name: str):
        if " (" in name:
            return name.split(" (")[0]
        return name

    @field_validator("sn", mode="after")
    @classmethod
    def validate_sn(cls, _: None, info: ValidationInfo):
        assert info.context
        name = info.context.get("full_name") or info.context.get("name") or info.context.get("Фамилия Имя Отчество")
        if " (" in name:
            sn = name.split(" (")[-1].rstrip(")")
            if sn:
                return sn


class CustomerBuilding(CustomerSearch):
    name: str = Field(validation_alias="Фамилия Имя Отчество")
    agreement: str | None = Field(None, validation_alias="Договор")
    status: CustomerStatus = Field(validation_alias="Статус")
    tariff: str | None = Field(None, validation_alias="Тариф")

    connected_at: str4date | None = Field(validation_alias="Дата подключения")
    added_at: str4date = Field(validation_alias="Дата добавления")
    last_active_at: str4datetime | None = Field(validation_alias="Активность в сети")
    address: str | None = Field(None, validation_alias="Заметки")

    onu_level: float | None = Field(None, validation_alias="Уровень сигнала (dBm)")

    @field_validator("agreement", mode="before")
    @classmethod
    def validate_agreement(cls, agreement: str | None):
        if agreement:
            return agreement.split("\n")[0]

    @field_validator("onu_level", mode="before")
    @classmethod
    def validate_onu_level(cls, onu_level: str | None):
        if onu_level:
            onu_level = onu_level.split("\n")[0]
        if onu_level is None or "-" not in onu_level:
            return None
        return onu_level


class Customer(CustomerSearch):
    created_at: str4datetime = Field(validation_alias="date_create")
    connected_at: str4date | None = Field(validation_alias="date_connect")
    last_positive_balance_at: str4date = Field(validation_alias="date_positive_balance")
    last_active_at: str4datetime = Field(validation_alias="date_activity")
    disconnect_at: date2str | None = None  # always none, can be manually filled after validation

    is_corporate: bool = Field(False, validation_alias="flag_corporate")
    is_disabled: int2bool = Field(False, validation_alias="is_disable")
    is_potential: int2bool = False

    phones: list[Phone] = Field([], validation_alias="phone")
    phone: NullablePhone = Field(None, validate_default=True, validation_alias="phone_that_will_definitely_not_exists")

    address: Address | None = None
    group: Group | None = Field(None, validate_default=True)
    coordinates: Coordinates | None = None
    tgis_link: _tgis_link = Field(None, validate_default=True)

    status: CustomerStatus = Field(validation_alias="state_id")
    agreement: list2model[Agreement] | None
    has_billing: int2bool = Field(validation_alias="is_in_billing")
    balance: float = 0
    tariffs: list[Tariff] = Field(validation_alias="tariff")

    ip: IPv4Address | None = Field(None, validate_default=True)
    mac: str | None = Field(None, validate_default=True)
    olt_id: int | None = None  # always none, can be manually filled after validation

    manager_id: int | None = None
    comment: str | None = Field(None, validation_alias="comment2")
    connect_type: _connect_type | None = Field(None, validate_default=True)

    @field_validator("address", mode="before")
    @classmethod
    def validate_address(cls, address: list, info: ValidationInfo):
        return Address.model_validate(list2model_validator(address), context={"label": addata(42).func(None, info)})  # ty: ignore

    @field_validator("coordinates", mode="after")
    @classmethod
    def validate_coordinates(cls, coordinates: list[float] | None, info: ValidationInfo):
        assert info.context
        return coordinates or list(map(float, addata(7).func(info.context["additional_data"], info).split(",")))  # ty: ignore

    @field_validator("agreement", mode="before")
    @classmethod
    def validate_agreement(cls, agreement: list[dict]):
        if not agreement or (agreement and agreement[0].get("number") is None):
            return None
        return agreement

    @field_validator("tgis_link", mode="after")
    @classmethod
    def validate_tgis_link(cls, tgis_link: str | None, info: ValidationInfo):
        if tgis_link is not None:
            return unescape(tgis_link)

        if info.data["coordinates"]:
            return make_tgis_link(*info.data["coordinates"])

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, _: None, info: ValidationInfo):
        assert info.context
        if info.context["phone"]:
            return info.context["phone"][0]

    @field_validator("phones", mode="before")
    @classmethod
    def validate_phones(cls, phones: list[dict]):
        return [phone for phone in phones if phone.get("number")]  # exclude empty or nulls

    @field_validator("phones", mode="after")
    @classmethod
    def validate_phones_after(cls, phones: list[dict]):
        return list(set(phones))  # remove duplicate

    @field_validator("ip", mode="before")
    @classmethod
    def validate_ip(cls, _: str, info: ValidationInfo):
        assert info.context
        if info.context.get("ip_mac"):
            return int(next(iter(info.context["ip_mac"].values()))["ip"])

    @field_validator("mac", mode="before")
    @classmethod
    def validate_mac(cls, _: str, info: ValidationInfo):
        assert info.context
        if info.context.get("ip_mac"):
            return format_mac(next(iter(info.context["ip_mac"].values()))["mac"])

    @field_validator("tariffs", mode="before")
    @classmethod
    def validate_tariffs(cls, tariffs: dict[str, list[dict[str, str]]]):
        return [storage.tariffs[int(tariff["id"])] for tariff in tariffs.get("current", []) if tariff.get("id")]

    @field_validator("group", mode="before")
    @classmethod
    def validate_group(cls, group_id: dict[str, dict[str, int]] | None):
        if not group_id:
            return
        id = int(list(group_id.values())[0]["id"])
        return {
            "id": id,
            "name": [
                "GPON Ош частный дом",
                "GPON Ош многоэтажный дом",
                "Равшан",
                "GPON Бишкек частный дом",
                "GPON Бишкек многоэтажный дом",
                "GPON Токмок многоэтажный дом",
                "GPON Токмок частный дом",
                "GPON Узген многоэтажный дом",
                "GPON Узген частный дом"
            ][id - 3]
        }

    @model_validator(mode="after")
    def validate_model(self):
        if self.address and self.address.label is None:
            self.address.label = self.comment
        return self
