from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.api.employee import check_creds, get_employee, get_employee_id
from app.db import Session
from app.db.crud import set_employee
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
    response.set_cookie("token", token, httponly=True)

    return {"id": id}


@router.get("/me", response_model=Employee)
def api_get_employee_me(request: Request, employee: Employee = Depends(employee_dependency)):
    return api_get_employee(int(employee.id))


@router.get("/{id}", response_model=Employee)
def api_get_employee(id: int):
    employee = get_employee(id)
    if employee is None:
        return JSONResponse({"detail": "employee not found"}, 404)

    return employee
