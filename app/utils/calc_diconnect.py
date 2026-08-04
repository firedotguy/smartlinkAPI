from datetime import date, timedelta

from app.enums import TariffType
from app.models.tariff import Tariff


def calc_disconnect(tariffs: list[Tariff], balance: float, connected_at: date) -> date | None:
    base_sum = sum([t.price for t in tariffs]) / 30  # sum per day
    if base_sum == 0:
        return None

    sale_tariff = next((t for t in tariffs if t.type == TariffType.sale), None)  # first sale tariff
    now = date.today()
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
