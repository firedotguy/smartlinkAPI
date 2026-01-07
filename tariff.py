from re import search, escape
from enum import Enum
from datetime import datetime, timedelta
from functools import reduce

class TariffType(Enum):
    BASE = 'base' # priced
    PROMO = 'promo' # free
    SALE = 'sale' # % sale
    NONE = 'none' # no price/sale

class Tariff:
    def __init__(self, content: str):
        # self.id = id
        self.content = content
        self.price = 0
        self.free_days = 0
        self.sale = 0
        self.sale_days = 0

        content = content.lower()

        if search(r'\(\d+\s*сом\)', content):
            self.type = TariffType.BASE
            match = search(r'\((\d+)\s*сом\)', content)
            if match:
                self.price = int(match.group(1))

        elif 'бесплатно' in content:
            self.type = TariffType.PROMO
            match = search(r'(\S+)\s+бесплатно', content)
            if match:
                word = match.group(1)

                multiplier_match = search(rf'(\d+)\s+{escape(match.group(1))}', content)
                multiplier = multiplier_match.group(1) if multiplier_match else 1

                if 'месяц' in word:
                    self.free_days = 30 * int(multiplier)

                elif 'день' in word or 'дн' in word:
                    self.free_days = int(multiplier)

        elif '%' in content:
            self.type = TariffType.SALE
            match = search(r'(\d+)%', content)
            if match:
                sale = match.group(1)
                self.sale = int(sale)

                word_match = search(fr'{sale}%\s+на\s+(\w+)', content)
                if word_match:
                    word = word_match.group(1)

                    if 'год' in word:
                        self.sale_days = 365
        else:
            self.type = TariffType.NONE


def calc_disconnect(tariffs: list[Tariff], balance: float, connected_at: datetime) -> datetime | None:
    base_sum = sum([t.price for t in tariffs]) / 30 # sum per day
    if base_sum == 0:
        return None

    sale_tariff = next((t for t in tariffs if t.type == TariffType.SALE), None) # first sale tariff
    now = datetime.now()
    days_since_connect = (now - connected_at).days
    free_days = sum(t.free_days for t in tariffs)
    free = max(0, free_days - days_since_connect)

    if sale_tariff:
        sale_multiplier = 1 - sale_tariff.sale / 100
        sale_remaining = max(0, sale_tariff.sale_days - days_since_connect) if sale_tariff.sale_days > 0 else 0
    else:
        sale_multiplier = 1
        sale_remaining = 0

    saled_sum = base_sum * sale_multiplier

    # spend balance
    if sale_remaining > 0:
        # sale period cost
        sale_period_cost = sale_remaining * saled_sum

        if balance >= sale_period_cost:
            # balance enough for whole sale period
            balance -= sale_period_cost
            days = free + sale_remaining + balance / base_sum
        else:
            # disconnect while sale period
            days = free + balance / saled_sum
    else:
        # sale expired or no sale
        days = free + balance / (saled_sum if sale_tariff and sale_tariff.sale_days == 0 else base_sum)

    return now + timedelta(days=int(days))
