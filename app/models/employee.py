from pydantic import Field, ValidationInfo, field_validator

from app.enums import Role
from app.models import BaseModel
from app.models.division import EmployeeDivision
from app.utils.pd import Phone, dict2list, dict2models, int2bool, str4date, str4datetime


class EmployeeName(BaseModel):
    id: int
    name: str


class Employee(EmployeeName):
    username: str = Field(validation_alias="login")
    short_name: str | None = None
    email: str | None = None
    phone: Phone | None = None

    created_at: str4date = Field(validation_alias="date_in")
    last_active_at: str4datetime = Field(validation_alias="last_activity_time")

    is_working: int2bool = Field(validation_alias="is_work")
    is_blocked: int2bool = False

    divisions: dict2models[EmployeeDivision] = Field(validation_alias="division")
    rights: dict2list[int]
    role: Role = Field(validation_alias="profile_id")
    allowed_addresses: dict2list[int] = Field([], validation_alias="access_address_id")
    allowed_task_assigning_addresses: dict2list[int] = Field([], validation_alias="task_allow_assign_address_id")

    inventory_id: int | None = None

    @field_validator("inventory_id", mode="after")
    @classmethod
    def validate_inventory_id(cls, _: None, info: ValidationInfo):
        assert info.context
        return info.context["inventory_resolver"](info.context["id"])
