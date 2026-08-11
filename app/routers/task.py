from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.attach import get_task_attachs
from app.api.task import add_comment, add_task, get_task, get_task_ids, get_tasks
from app.db.crud import get_division_name, get_employee_name
from app.db.models import Employee
from app.enums import TaskType
from app.utils.dependencies import db_dependency, employee_dependency

router = APIRouter(prefix="/tasks")


@router.get("/{id}")
def api_get_task(id: int, db: Session = Depends(db_dependency)):
    task = get_task(id, lambda id: get_employee_name(db, id), division_resolver=lambda id: get_division_name(db, id))

    if task is None:
        return JSONResponse({"detail": "task not found"}, 404)

    return task


@router.post("/{id}/comments")
def api_post_task_comments(id: int, content: str, employee: Employee = Depends(employee_dependency)):
    return {"id": add_comment(id, content, employee.id)}


@router.get("/{id}/attachs")
def api_get_task_attachs(id: int):
    return get_task_attachs(id)


@router.get("/attachs")
def api_get_task_multiple_attachs(ids: list[int]):
    attachs = []
    for id in ids:
        attachs.extend(get_task_attachs(id))
    return attachs


@router.post("")
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
    db: Session = Depends(db_dependency)
):
    types = list(map(int, type.split(","))) if type else None
    authors = list(map(int, author_id.split(","))) if author_id else None

    ids = get_task_ids(completed_at_from=completed_at_from, completed_at_to=completed_at_to, type=types, author_id=authors)

    if len(ids) > 100:
        return JSONResponse({"detail": "too wide query"}, 400)

    return get_tasks(*ids, employee_resolver=lambda id: get_employee_name(db, id), division_resolver=lambda id: get_division_name(db, id))
