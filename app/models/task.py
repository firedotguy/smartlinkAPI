from typing import Annotated

from pydantic import BeforeValidator, Field, ValidationInfo, field_validator, model_validator

from app.models import BaseModel
from app.models.attach import Attach
from app.models.division import Division
from app.models.employee import EmployeeName
from app.utils.pd import Phone, addata, dict2list, dict2list_validator, list2model, str2list_validator, str4datetime


class TaskType(BaseModel):
    id: int
    name: str


class TaskStatus(BaseModel):
    id: int
    name: str
    system_name: str = Field(validation_alias="system_role_text")


class TaskAddress(BaseModel):
    id: int | None = Field(None, validation_alias="addressId")
    label: str | None = Field(None, validation_alias="text")
    apartment: int | None = None


class HistoryAction(BaseModel):
    type: int = Field(validation_alias="type_id")
    employee: EmployeeName | None = None
    created_at: str4datetime = Field(validation_alias="date")
    comment: str | None = None


class Comment(BaseModel):
    id: int
    created_at: str4datetime = Field(validation_alias="dateAdd")
    author: EmployeeName | None = Field(None, validation_alias="employee_id")
    content: str = Field(validation_alias="comment")

    @field_validator("author", mode="before")
    @classmethod
    def validate_author(cls, author_id: int | None, info: ValidationInfo):
        assert info.context
        if author_id:
            return {"id": author_id, "name": info.context["employee_resolver"](author_id)}

    @model_validator(mode="after")
    def validate_model(self):
        if self.content.startswith("<b>BGB ERROR</b>"):
            self.author = EmployeeName(id=0, name="Биллинг")
            self.content = self.content.split("<b>BGB ERROR</b>: ")[-1]
        return self


_appeal_type = Annotated[str | None, addata(28)]
_appeal_phone = Annotated[Phone | None, addata(29)]
_appeal_reason = Annotated[str | None, addata(32, 30)]
_not_use_reason = Annotated[str | None, addata(37)]
_solve = Annotated[str | None, addata(86, 36)]
_price = Annotated[float | None, addata(26)]
_connect_type = Annotated[str | None, addata(27)]
_tariff = Annotated[str | None, addata(25)]
_extra_services = Annotated[list[str] | None, BeforeValidator(str2list_validator), addata(83)]


class Task(BaseModel):
    id: int
    parent_id: int | None = Field(None, validation_alias="parentTaskId")

    type: TaskType
    status: TaskStatus = Field(validation_alias="state")
    history: list[HistoryAction] = []

    created_at: str4datetime = Field(validation_alias="date")
    planned_to: str4datetime = Field(validation_alias="date")
    updated_at: str4datetime = Field(validation_alias="date")
    completed_at: str4datetime | None = Field(None, validation_alias="date")

    address: TaskAddress
    coordinates: list[float] | None = Field(None, validate_default=True)

    description: str | None = None
    short_description: str | None = Field(None, validation_alias="description_short")

    author: EmployeeName | None = Field(None, validation_alias="author_employee_id")
    employees: list[EmployeeName] = Field([], validation_alias="staff")
    divisions: list[Division] = Field([], validation_alias="staff")
    watchers: list[EmployeeName] = Field([], validation_alias="watcher_employee_list")
    comments: dict2list[Comment] = []
    attachs: dict2list[Attach] = Field([], validation_alias="attach")

    customer_id: list2model[int] | None = Field(None, validation_alias="customer")
    tariff: _tariff = Field(None, validate_default=True)
    appeal_type: _appeal_type = Field(None, validate_default=True)
    appeal_phone: _appeal_phone = Field(None, validate_default=True)
    appeal_reason: _appeal_reason = Field(None, validate_default=True)
    not_use_reason: _not_use_reason = Field(None, validate_default=True)

    solve: _solve = Field(None, validate_default=True)
    price: _price = Field(None, validate_default=True)
    connect_type: _connect_type = Field(None, validate_default=True)
    extra_services: _extra_services = Field(None, validate_default=True)

    @field_validator("employees", mode="before")
    @classmethod
    def validate_employees(cls, employee_ids: dict[str, dict[str | int, int]], info: ValidationInfo):
        assert info.context
        return [{"id": id, "name": info.context["employee_resolver"](id)} for id in dict2list_validator(employee_ids.get("employee", []))]

    @field_validator("divisions", mode="before")
    @classmethod
    def validate_divisions(cls, divison_ids: dict[str, dict[str | int, int]], info: ValidationInfo):
        assert info.context
        return [{"id": id, "name": info.context["division_resolver"](id)} for id in dict2list_validator(divison_ids.get("division", []))]

    @field_validator("watchers", mode="before")
    @classmethod
    def validate_watchers(cls, watcher_ids: list[int], info: ValidationInfo):
        assert info.context
        return [{"id": id, "name": info.context["employee_resolver"](id)} for id in watcher_ids]

    @field_validator("author", mode="before")
    @classmethod
    def validate_author(cls, author_id: int | None, info: ValidationInfo):
        assert info.context
        if author_id:
            return {"id": author_id, "name": info.context["employee_resolver"](author_id)}

    @field_validator("created_at", "planned_to", "updated_at", "completed_at", mode="before")
    @classmethod
    def validate_dates(cls, date: dict, info: ValidationInfo):
        assert info.field_name
        return date.get({"created_at": "create", "planned_to": "todo", "updated_at": "update", "completed_at": "complete"}[info.field_name])

    @field_validator("coordinates", mode="before")
    @classmethod
    def validate_coordinates(cls, _: None, info: ValidationInfo):
        coords = addata(7).func(None, info)  # ty: ignore
        if "Нет координат" in str(coords):
            return
        if coords:
            return list(map(float, coords.split(",")))
