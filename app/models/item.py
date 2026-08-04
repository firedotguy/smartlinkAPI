from pydantic import Field, field_validator

from app.enums import ItemLocation, ItemType
from app.models import BaseModel
from app.utils import storage
from app.utils.pd import int2bool, str4date


class ItemCategory(BaseModel):
    id: int
    name: str
    type: ItemType = Field(validation_alias="inventory_section_catalog_id")
    unit: str = Field("шт", validation_alias="unit_name")

    @field_validator("unit", mode="after")
    @classmethod
    def validate_unit(cls, unit: str):
        return unit.rstrip(".")  # шт. -> шт


class Item(BaseModel):
    id: int
    category: ItemCategory = Field(validation_alias="catalog_id")
    amount: int = 1
    cost: int = 0

    account: str = Field(validation_alias="acount")

    document_number: str | None = None
    document_signed_at: str4date = Field(validation_alias="document_date")

    sn: str | None = Field(None, validation_alias="serial_number")
    mac: str | None = None

    location: ItemLocation = Field(validation_alias="location_type")
    location_id: int | None = None

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, id: int):
        return storage.item_categories[id]


class Olt(BaseModel):
    id: int
    name: str
    ip: str = Field(validation_alias="host")
    added_at: str4date = Field(validation_alias="date_add")
    location: str
    online: int2bool = Field(validation_alias="is_online")
    snmp_protocol: int = Field(validation_alias="snmp_proto")
    snmp_community: str
