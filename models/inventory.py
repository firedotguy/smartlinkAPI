from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator
from enums import InventoryCategoryType

class InventoryCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    type: InventoryCategoryType
    parent_id: Optional[int] = None

    @field_validator("type", mode="before")
    @classmethod
    def cast_type(cls, v):
        return v if isinstance(v, InventoryCategoryType) else InventoryCategoryType(int(v))
