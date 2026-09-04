from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.attach import get_customer_attachs
from app.api.customer import get_customer, rewrite_mac, rewrite_sn, search_customers, update_customer
from app.api.device import get_customer_olt, get_ont_olt
from app.api.inventory import get_customer_items
from app.api.task import get_task_ids, get_tasks
from app.db.crud import get_division_name, get_employee_name
from app.enums import CustomerStatus
from app.utils.calc_diconnect import calc_disconnect
from app.utils.dependencies import db_dependency

router = APIRouter(prefix="/customers")


@router.get("/search")
def api_get_customer_search(q: str):
    return search_customers(q)


@router.get("/{id}")
def api_get_customer(id: int, full: bool = True):
    customer = get_customer(id)

    if customer is None:
        return JSONResponse({"detail": "customer not found"}, 404)

    if full:
        if customer.sn:
            customer.olt_id = get_customer_olt(id) or get_ont_olt(customer.sn)
        if customer.status == CustomerStatus.active and customer.connected_at is not None:
            customer.disconnect_at = calc_disconnect(customer.tariffs, customer.balance, customer.connected_at)

    return customer


@router.get("/{id}/tasks")
def api_get_customer_tasks(id: int, db: Session = Depends(db_dependency)):
    ids = get_task_ids(customer_id=id)
    if not ids:
        return []
    return get_tasks(*ids, employee_resolver=lambda id: get_employee_name(db, id), division_resolver=lambda id: get_division_name(db, id))


@router.get("/{id}/attachs")
def api_get_customer_attachs(id: int):
    return get_customer_attachs(id)


@router.get("/{id}/items")
def api_get_customer_items(id: int):
    return get_customer_items(id)


@router.patch("/{id}", status_code=204)
def api_patch_customer(id: int, phones: str):
    list_phones = phones.split(",")
    if len(list_phones) < 2:
        return JSONResponse({"detail": "customer can have at least 2 phone numbers"}, 422)

    update_customer(id, list_phones)


@router.post("/{id}/rewrite-sn", status_code=204)
def api_post_customer_rewrite_sn(id: int, agreement: str, sn: str):
    res = rewrite_sn(id, agreement, sn)
    if res:
        return JSONResponse({"detail": res}, 400)


@router.post("/{id}/rewrite-mac", status_code=204)
def api_post_customer_rewrite_mac(id: int, agreement: str):
    res = rewrite_mac(id, agreement)
    if res:
        return JSONResponse({"detail": res}, 400)
