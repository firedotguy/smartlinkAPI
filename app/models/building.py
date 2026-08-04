from typing import Annotated

from pydantic import BeforeValidator, Field, field_validator

from app.enums import BuildingType
from app.models import BaseModel
from app.models.customer import CustomerBuilding
from app.utils.pd import Coordinates, addata, str2list_validator

_other_providers = Annotated[list[str], BeforeValidator(str2list_validator), addata(63)]
_build_status = Annotated[str | None, addata(60)]
_install_type = Annotated[str | None, addata(64)]
_agreement_type = Annotated[str | None, addata(65)]


class Building(BaseModel):
    id: int
    building_id: int
    type: BuildingType = Field(validation_alias="type_id")
    coordinates: Coordinates | None = None

    floors: int | None = Field(None, validation_alias="floor")
    entrances: int | None = Field(None, validation_alias="entrance")
    aparts: int | None = Field(None, validation_alias="apart")

    short_name: str = Field(validation_alias="name")
    name: str = Field(validation_alias="full_name")

    parent_id: int | None = None
    parent_ids: list[int] = []

    comment: str | None = None
    task_comment: str | None = None

    is_active: bool = Field(True, validation_alias="is_not_use")
    is_show_on_map: bool = True

    manager_id: int | None = Field(validation_alias="manager_employee_id")

    other_providers: _other_providers = Field([], validate_default=True)
    build_status: _build_status = Field(None, validate_default=True)
    install_type: _install_type = Field(None, validate_default=True)

    customers: list[CustomerBuilding] = []  # fill manually

    @field_validator("is_active", mode="before")
    @classmethod
    def validate_is_active(cls, is_not_use: bool):
        return not is_not_use
