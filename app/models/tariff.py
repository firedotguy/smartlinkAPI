from re import escape, search

from app.enums import TariffType
from app.models import BaseModel


class Tariff(BaseModel):
    content: str
    price: int = 0
    free_days: int = 0
    sale: int = 0
    sale_days: int = 0
    type: TariffType

    @classmethod
    def new(cls, content: str):
        price = 0
        free_days = 0
        sale = 0
        sale_days = 0

        _content = content.lower()

        if search(r"\(\d+\s*сом\)", _content):
            type = TariffType.base
            match = search(r"\((\d+)\s*сом\)", _content)
            if match:
                price = int(match.group(1))

        elif "бесплатно" in _content:
            type = TariffType.promo
            match = search(r"(\S+)\s+бесплатно", _content)
            if match:
                word = match.group(1)

                multiplier_match = search(rf"(\d+)\s+{escape(match.group(1))}", _content)
                multiplier = multiplier_match.group(1) if multiplier_match else 1

                if "месяц" in word:
                    free_days = 30 * int(multiplier)

                elif "день" in word or "дн" in word:
                    free_days = int(multiplier)

        elif "%" in _content:
            type = TariffType.sale
            match = search(r"(\d+)%", _content)
            if match:
                sale = int(match.group(1))

                word_match = search(rf"{sale}%\s+на\s+(\w+)", _content)
                if word_match:
                    word = word_match.group(1)

                    if "год" in word:
                        sale_days = 365
        else:
            type = TariffType.none

        return cls(content=content, type=type, free_days=free_days, sale=sale, sale_days=sale_days, price=price)
