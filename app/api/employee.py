from app.api import api_call
from app.models.division import Division
from app.models.employee import Employee
from app.utils.logger import get_logger

l = get_logger("api.employee")


def get_employee_id(*, username: str) -> int | None:
    l.info("get employee id username=%s", username)
    id = api_call("employee", "get_employee_id", data_typer="login", data_value=username).get("id")

    if id is None:
        l.error("employee not found")
        return None
    return id


def get_employee(id: int) -> Employee | None:
    l.info("get employee id=%s", id)
    employee = api_call("employee", "get_data", id=id).get("data", {}).get(str(id))

    if employee is None:
        l.error("employee not found")
        return None

    return Employee.model_validate(employee, context=employee)


def get_employees() -> list[Employee]:
    l.info("get employee")
    employees = api_call("employee", "get_data")["data"]

    return [Employee.model_validate(employee, context=employee) for employee in employees.values()]


def check_creds(username: str, password: str) -> bool:
    l.info("check creds username=%s password=%s", username, "*" * len(password))
    return api_call("employee", "check_pass", login=username, pass_=password).get("result") == "OK"


def get_division(id: int) -> Division | None:
    l.debug("get division id=%s", id)
    division = api_call("employee", "get_division", id=id).get("data")

    if not division:
        l.error("division not found")
        return None

    division = list(division.values())[0]
    return Division.model_validate(division, context=division)


def get_divisions() -> list[Division]:
    l.debug("get divisions")
    divisions = api_call("employee", "get_division")["data"]

    return [Division.model_validate(division, context=division) for division in divisions.values()]
