from datetime import datetime
from typing import Callable

from app.api import api_call
from app.enums import TaskType
from app.models.task import Task
from app.utils.logger import get_logger
from app.utils.pd import dict2list_validator

l = get_logger("api.task")


def get_task(id: int, employee_resolver: Callable[[int], str | None], division_resolver: Callable[[int], str | None]) -> Task | None:
    l.info("get task id=%s", id)
    task = api_call("task", "show", id=id).get("data")

    if task is None:
        l.error("task not found")
        return None

    return Task.model_validate(task, context={**task, "employee_resolver": employee_resolver, "division_resolver": division_resolver})


def get_task_ids(
    *,
    customer_id: int | None = None,
    type: list[int] | None = None,
    status: list[int] | None = None,
    author_id: list[int] | None = None,
    employee_id: int | None = None,
    completed_at_from: datetime | None = None,
    completed_at_to: datetime | None = None,
    limit: int | None = None
) -> list[int]:
    l.info(
        "get task ids customer_id=%s type=%s status=%s author_id=%s employee_id=%s completed_at_from=%s completed_at_to=%s limit=%s",
        customer_id,
        type,
        status,
        author_id,
        employee_id,
        completed_at_from,
        completed_at_to,
        limit
    )
    tasks = api_call(
        "task",
        "get_list",
        customer_id=customer_id,
        type_id=",".join(map(str, type)) if type else None,
        state_id=",".join(map(str, status)) if status else None,
        author_employee_id=",".join(map(str, author_id)) if author_id else None,
        employee_id=employee_id,
        date_finish_from=completed_at_from,
        date_finish_to=completed_at_to,
        limit=limit,
        order_by="date_finish"
    )["list"].split(",")
    if not tasks:
        return []
    return [int(task) for task in tasks if task][::-1]


def get_tasks(*ids: int, employee_resolver: Callable[[int], str | None], division_resolver: Callable[[int], str | None]) -> list[Task]:
    l.info("get tasks ids=%s", ids)
    tasks = api_call("task", "show", id=",".join(map(str, ids)), timeout=60).get("data")

    if tasks is None:
        return []

    if len(ids) > 1:
        tasks = dict2list_validator(tasks)

        if "error" in tasks:
            l.error("some task(s) not found")
        return [
            Task.model_validate(task, context={**task, "employee_resolver": employee_resolver, "division_resolver": division_resolver})
            for task in tasks
            if task != "error"
        ]

    return [Task.model_validate(tasks, context={**tasks, "employee_resolver": employee_resolver, "division_resolver": division_resolver})]


def add_comment(task_id: int, content: str, author_id: int | None = None) -> int:
    l.info("add comment task_id=%s author_id=%s content=%s", task_id, author_id, content)
    return api_call("task", "comment_add", post=True, id=task_id, employee_id=author_id, comment=content)["Id"]


def add_task(
    author_id: int,
    type: TaskType,
    address_id: int | None = None,
    customer_id: int | None = None,
    description: str | None = None,
    divisions: list[int] = [],
    reason: str | None = None,
    appeal_phone: int | None = None,
    appeal_type: str | None = None
) -> int:
    l.info(
        "add task type=%s author_id=%s address_id=%s customer_id=%s description=%s divisions=%s reason=%s appeal_phone=%s appeal_type=%s",
        type.name,
        author_id,
        address_id,
        customer_id,
        description,
        divisions,
        reason,
        appeal_phone,
        appeal_type
    )
    return api_call(
        "task",
        "add",
        post=True,
        work_typer=type,
        work_datedo=datetime.now(),
        deadline_hour=72,
        division_id=",".join(map(str, divisions)),
        author_employee_id=author_id,
        address_id=address_id,
        customer_id=customer_id,
        opis=description,
        dopf_30=reason,
        dopf_29=appeal_phone,
        dopf_28=appeal_type
    )["Id"]


def change_status(id: int, status_id: int, author_id: int) -> None:
    l.info("change task status id=%s status=%s auhtor=%s", id, status_id, author_id)
    api_call("task", "change_state", post=True, id=id, state_id=status_id, employee_id=author_id, nogi="bogi")
