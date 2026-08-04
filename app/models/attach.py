from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field

from app.utils.pd import str4datetime


class Attach(BaseModel):
    id: UUID = Field(validation_alias=AliasChoices("id", "uuid"))
    # object_type: AttachObjectType = Field(validation_alias="category_uuid")
    # object_id: int
    name: str = Field(validation_alias=AliasChoices("filename", "fileName"))
    internal_name: str = Field(validation_alias=AliasChoices("internal_filepath", "fileSystemPath"))
    comment: str | None = None
    created_at: str4datetime = Field(validation_alias=AliasChoices("date_add", "dateAdd"))
    employee_id: int | None = None
