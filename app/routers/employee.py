from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.employee import check_creds, get_employee, get_employee_id
from app.api.task import get_task, get_task_ids
from app.db import Session
from app.db.crud import get_division_name, get_divisions, get_employee_name, set_employee
from app.models.employee import Employee
from app.utils.dependencies import db_dependency, employee_dependency
from app.utils.token import gen_token

router = APIRouter(prefix="/employees")


@router.post("/login")
def api_post_login(response: Response, username: str, password: str, db: Session = Depends(db_dependency)):
    if not check_creds(username, password):
        return JSONResponse({"detail": "invalid login or password"}, 401)

    id = get_employee_id(username=username)
    if id is None:
        return JSONResponse({"detail": "employee id not found"}, 500)

    token = gen_token()
    set_employee(db, id, username, token)
    response.set_cookie("token", token, httponly=True, secure=True)

    return {"id": id}


@router.get("/me", response_model=Employee)
def api_get_employee_me(employee: Employee = Depends(employee_dependency)):
    return api_get_employee(int(employee.id))


@router.get("/me/tasks")
def api_get_employee_me_tasks(
    status: str = "", type: str = "", limit: int | None = None, employee: Employee = Depends(employee_dependency), db: Session = Depends(db_dependency)
):
    types = list(map(int, type.split(","))) if type else None
    statuses = list(map(int, status.split(","))) if status else None

    ids = get_task_ids(type=types, status=statuses, employee_id=employee.id, limit=limit)

    if len(ids) > 100:
        return JSONResponse({"detail": "too wide query"}, 400)

    return get_task(*ids, employee_resolver=lambda id: get_employee_name(db, id), division_resolver=lambda id: get_division_name(db, id))


@router.get("/divisions")
def api_get_divisions(db: Session = Depends(db_dependency)):
    return get_divisions(db)


@router.get("/{id}", response_model=Employee)
def api_get_employee(id: int):
    employee = get_employee(id)
    if employee is None:
        return JSONResponse({"detail": "employee not found"}, 404)

    return employee
