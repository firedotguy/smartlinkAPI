from app.models import BaseModel


class Province(BaseModel):
    id: int
    name: str
    parent_ids: list[int]
    parent_id: int | None = None
    # gov_id: int | None = None
