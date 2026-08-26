from asyncio import gather, get_running_loop
from collections import defaultdict
from datetime import datetime
from functools import partial
from json import loads

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.addata import set_adddata
from app.api.attach import get_task_attachs, upload_attach
from app.api.customer import get_customer as api_get_customer
from app.api.inventory import get_employee_items, get_task_items, split_inventory, transfer_inventory
from app.api.task import add_comment, add_task, change_status, get_task, get_task_ids, get_tasks
from app.db.crud import get_division_name, get_employee_name
from app.db.models import Employee
from app.enums import AddataObjectType, AttachObjectType, TaskType
from app.models.item import Item
from app.utils.dependencies import db_dependency, employee_dependency
from app.utils.items import fold_categories

router = APIRouter(prefix="/tasks")


@router.get("/{id}")
def api_get_task(id: int, get_customer: bool = False, db: Session = Depends(db_dependency)):
    task = get_task(id, lambda id: get_employee_name(db, id), division_resolver=lambda id: get_division_name(db, id))

    if task is None:
        return JSONResponse({"detail": "task not found"}, 404)

    if get_customer and task.customer_id:
        task.customer = api_get_customer(task.customer_id)

    return task


@router.patch("/{id}", status_code=204)
def api_patch_task(id: int, tariff: str | None = None, catv: int | None = None):
    if tariff:
        set_adddata(id, AddataObjectType.task, 25, tariff)
    if catv:
        set_adddata(id, AddataObjectType.task, 69, catv)


@router.get("/{id}/items")
def api_get_task_items(id: int):
    return fold_categories(get_task_items(id))


@router.post("/{id}/items", status_code=204)
def api_post_task_items(id: int, items: str, employee: Employee = Depends(employee_dependency)):
    if employee.inventory_id is None:
        return JSONResponse({"detail": "employee has not storage"}, 404)

    requested: dict[int, int] = {int(k): int(v) for k, v in loads(items).items()}
    employee_items = get_employee_items(employee.inventory_id)
    employee_items.sort(key=lambda item: item.amount)

    by_category: dict[int, list[Item]] = defaultdict(list)
    for item in employee_items:
        by_category[item.category.id].append(item)

    for category, required in requested.items():
        if required <= 0:
            return JSONResponse({"detail": f"invalid amount {required} for category {category}"}, 422)
        available = sum(i.amount for i in by_category[category])
        if available == 0:
            return JSONResponse({"detail": f"employee has no items with category {category}"}, 404)
        if available < required:
            return JSONResponse({"detail": f"employee only has {available} of category {category} (tried to transfer {required})"}, 406)

    to_transfer_ids: list[int] = []
    for category, required in requested.items():
        amount = 0
        for item in employee_items:
            if item.category.id != category:
                continue
            to_transfer_ids.append(item.id)

            amount += item.amount
            if amount > required:
                split_inventory(item.id, item.amount - (amount - required))
                break
            if amount == required:
                break

    for item_id in to_transfer_ids:
        transfer_inventory(item_id, f"21203{id:07}", employee.id)


@router.delete("/{id}/items/{category_id}", status_code=204)
def api_delete_task_items(id: int, category_id: int, employee: Employee = Depends(employee_dependency)):
    if employee.inventory_id is None:
        return JSONResponse({"detail": "employee has not storage"}, 404)

    items = [item.id for item in get_task_items(id) if item.category.id == category_id]
    if not items:
        return JSONResponse({"detail": "category not found"}, 404)

    for item in items:
        transfer_inventory(item, f"20403{employee.inventory_id:07}", employee.id)


@router.post("/{id}/comments", status_code=201)
def api_post_task_comments(id: int, content: str, employee: Employee = Depends(employee_dependency)):
    return {"id": add_comment(id, content, employee.id)}


@router.get("/{id}/attachs")
def api_get_task_attachs(id: int):
    return get_task_attachs(id)


@router.post("/{id}/attachs", status_code=201)
async def api_post_task_attachs(id: int, attachs: list[UploadFile]):
    loop = get_running_loop()
    return await gather(
        *[
            loop.run_in_executor(
                None,
                partial(upload_attach, id, AttachObjectType.task, (attach.filename or "image.png", await attach.read(), attach.content_type or "image/png"))
            )
            for attach in attachs
        ]
    )


@router.post("/{id}/get-agreement", status_code=204)
def api_post_task_get_agreement(id: int, employee: Employee = Depends(employee_dependency)):
    change_status(id, 16, employee.id)


@router.post("/{id}/add-ont", status_code=204)
def api_post_task_add_ont(id: int, employee: Employee = Depends(employee_dependency)):
    change_status(id, 17, employee.id)


@router.post("/{id}/register-ont", status_code=204)
def api_post_task_register_ont(id: int, employee: Employee = Depends(employee_dependency)):
    change_status(id, 19, employee.id)


@router.post("/{id}/complete", status_code=204)
def api_post_task_complete(id: int, employee: Employee = Depends(employee_dependency)):
    change_status(id, 12, employee.id)


@router.post("/{id}/start", status_code=204)
def api_post_task_start(id: int, employee: Employee = Depends(employee_dependency)):
    change_status(id, 3, employee.id)


@router.get("/attachs")
def api_get_task_multiple_attachs(ids: list[int]):
    attachs = []
    for id in ids:
        attachs.extend(get_task_attachs(id))
    return attachs


@router.post("", status_code=201)
def api_post_task(
    type: TaskType,
    customer_id: int | None = None,
    address_id: int | None = None,
    reason: str | None = None,
    appeal_phone: int | None = None,
    appeal_type: str | None = None,
    description: str | None = None,
    divisions: str = "",
    employee: Employee = Depends(employee_dependency)
):
    list_divisions = list(map(int, divisions.split(","))) if divisions else []
    if (bool(customer_id) and bool(address_id)) or (not bool(customer_id) and not bool(address_id)):
        return JSONResponse({"detail": "only one of customer_id or address_id allowed"}, 422)

    if customer_id is None and type in (TaskType.repair, TaskType.repair_ravshan, TaskType.uninstall):
        return JSONResponse({"detail": "customer id is required"}, 422)

    if address_id is None and type in (TaskType.repair_magistral, TaskType.magistral):
        return JSONResponse({"detail": "address id (building) is required"}, 422)

    if reason is None and type in (TaskType.repair, TaskType.inactive, TaskType.repair_ravshan, TaskType.repair_magistral, TaskType.magistral):
        return JSONResponse({"detail": "reason is required"}, 422)

    if appeal_phone is None and type in (TaskType.repair, TaskType.inactive, TaskType.repair_ravshan, TaskType.uninstall, TaskType.magistral):
        return JSONResponse({"detail": "appeal phone is required"}, 422)

    if appeal_type is None and type in (TaskType.repair, TaskType.inactive, TaskType.repair_ravshan, TaskType.repair_magistral):
        return JSONResponse({"detail": "appeal type is required"}, 422)

    return {"id": add_task(employee.id, type, address_id, customer_id, description, list_divisions, reason, appeal_phone, appeal_type)}


@router.get("")
def api_get_tasks(
    type: str | None = None,
    author_id: str | None = None,
    completed_at_from: datetime | None = None,
    completed_at_to: datetime | None = None,
    get_customers: bool = False,
    db: Session = Depends(db_dependency)
):
    types = list(map(int, type.split(","))) if type else None
    authors = list(map(int, author_id.split(","))) if author_id else None

    ids = get_task_ids(completed_at_from=completed_at_from, completed_at_to=completed_at_to, type=types, author_id=authors)

    if len(ids) > 100:
        return JSONResponse({"detail": "too wide query"}, 400)

    if not ids:
        return []

    tasks = get_tasks(*ids, employee_resolver=lambda id: get_employee_name(db, id), division_resolver=lambda id: get_division_name(db, id))
    if get_customers:
        for task in tasks:
            if task.customer_id:
                task.customer = api_get_customer(task.customer_id)
    return tasks
