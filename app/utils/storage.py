from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.item import ItemCategory, Olt
    from app.models.tariff import Tariff

tariffs: dict[int, Tariff] = {}
item_categories: dict[int, ItemCategory] = {}
olts: dict[int, Olt] = {}
