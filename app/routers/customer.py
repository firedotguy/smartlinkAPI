from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.attach import get_customer_attachs
from app.api.customer import get_customer, search_customers
from app.api.device import get_customer_olt, get_ont_olt
from app.api.inventory import get_customer_items
from app.api.task import get_task_ids, get_tasks
from app.enums import CustomerStatus
from app.utils.calc_diconnect import calc_disconnect

router = APIRouter(prefix="/customers")


@router.get("/search")
def api_get_customer_search(q: str):
    return search_customers(q)


@router.get("/{id}")
def api_get_customer(id: int):
    customer = get_customer(id)

    if customer is None:
        return JSONResponse({"detail": "customer not found"}, 404)

    if customer.sn:
        customer.olt_id = get_customer_olt(id) or get_ont_olt(customer.sn)
    if customer.status == CustomerStatus.active and customer.connected_at is not None:
        customer.disconnect_at = calc_disconnect(customer.tariffs, customer.balance, customer.connected_at)

    return customer


@router.get("/{id}/tasks")
def api_get_customer_tasks(id: int):
    ids = get_task_ids(id)
    return get_tasks(*ids)


@router.get("/{id}/attachs")
def api_get_customer_attachs(id: int):
    return get_customer_attachs(id)


@router.get("/{id}/items")
def api_get_customer_items(id: int):
    return get_customer_items(id)
