from re import fullmatch

from bs4 import BeautifulSoup

from app.api import api_call, custom_api_call
from app.models.customer import Customer, CustomerBuilding, CustomerSearch
from app.utils.logger import get_logger
from app.utils.parse_table import parse

l = get_logger("api.customer")


def get_customer(id: int) -> Customer | None:
    l.info("get customer id=%s", id)
    customer = api_call("customer", "get_data", id=id).get("data")

    if customer is None:
        l.error("customer not found")
        return None

    return Customer.model_validate(customer, context=customer)


def search_customers(query: str) -> list[CustomerSearch]:
    l.info("search customers q=%s", query)
    res = custom_api_call("customer_list/ajax_search", search=query)
    if not res:
        return []

    customers = []
    for tag in BeautifulSoup(res["data"], "html.parser").find_all("a"):
        if "/customer/" not in tag["href"]:
            continue
        match = fullmatch(r'<a href="/customer/(\d+)"> <i class="erp-icon far fa-bars"> </i> (\d+) · (.+) - (.+)</a>', tag.prettify().replace("\n", ""))
        assert match, f"match failed ({tag.prettify().replace('\n', '')})"

        data = {"id": match.group(1), "agreement": match.group(2), "full_name": match.group(3), "login": match.group(4)}
        customers.append(CustomerSearch.model_validate(data, context=data))

    return customers
    # l.info("search customers q=%s by=%s", query, by)
    # res = sql_call(f"select * from customers where {by} ilike '%{query}%' limit 15")

    # customers = [Customer.model_validate(customer) for customer in res]
    # if customers:
    #     l.info("cound %s customers", customers)
    # else:
    #     l.warning("customers not found")

    # return customers


def get_building_customers(id: int) -> list[CustomerBuilding]:
    l.info("get building customers id=%s", id)
    customers = custom_api_call("building/tab_body", json=False, section="customer", id=id)

    if f"Building #{id} not found" in customers:
        l.error("building not found")
        return []

    return [CustomerBuilding.model_validate(customer, context=customer) for customer in parse(customers, add_ids=True) if customer.get("Фамилия Имя Отчество")]


def rewrite_sn(id: int, agreement: str, sn: str) -> str | None:
    l.info("rewrite sn id=%s agreement=%s sn=%s", id, agreement, sn)
    res = api_call(
        "customer", "mark_add", timeout=360, nogi="bogi", mark_id=1, customer_id=id, _command="attach_onu", _onu_serial=sn, _contract_number=agreement
    )
    if int(res["result"]):
        l.error("fail to rewrite sn: %s", res["msg"])
        return res["msg"]


def rewrite_mac(id: int, agreement: str) -> str | None:
    l.info("rewrite mac id=%s agreement=%s", id, agreement)
    res = api_call(
        "customer", "mark_add", nogi="bogi", mark_id=1, customer_id=id, _command="renew_mac_address", _userside_customer_id=id, _contract_number=agreement
    )
    if int(res["result"]):
        l.error("fail to rewrite mac: %s", res["msg"])
        return res["msg"]


def update_customer(id: int, phones: list[str]) -> None:
    api_call(
        "customer",
        "edit",
        post=True,
        id=id,
        phone0=phones[0],
        phone1=phones[1],
        phone2=phones[2] if len(phones) > 2 else None,
        phone3=phones[3] if len(phones) > 3 else None,
        phone4=phones[4] if len(phones) > 4 else None
    )
