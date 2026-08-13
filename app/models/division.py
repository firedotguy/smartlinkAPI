from pydantic import Field

from app.models import BaseModel
from app.utils.pd import int2bool, str4date


class Division(BaseModel):
    id: int
    name: str
    parent_id: int | None = None
    comment: str | None = None
    # employees: list[Employee]
    # ex_employees: list[Employee]


class EmployeeDivision(BaseModel):
    id: int = Field(validation_alias="division_id")
    id2: int | None = Field(None, validation_alias="id")

    position: str | None = None
    is_member: int2bool = Field(True, validation_alias="is_work")

    added_at: str4date = Field(validation_alias="date_add")
    kicked_at: str4date | None = Field(None, validation_alias="date_out")
