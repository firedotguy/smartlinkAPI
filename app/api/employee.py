from app.api import api_call
from app.models.employee import Employee
from app.utils.logger import get_logger

l = get_logger("api.employee")


def get_employee_id(*, username: str) -> int | None:
    l.info("get employee id username=%s", username)
    id = api_call("employee", "get_employee_id", data_typer="login", data_value=username).get("id")

    if id is None:
        l.error("employee not found")
        return None

    l.info("found employee id=%s", id)
    return id


def get_employee(id: int) -> Employee | None:
    l.info("get employee id=%s", id)
    res = api_call("employee", "get_data", id=id).get("data", {}).get(str(id))

    if res is None:
        l.error("employee not found")
        return None

    employee = Employee.model_validate(res, context=res)
    l.info("found employee username=%s", employee.username)
    return employee


def check_creds(username: str, password: str) -> bool:
    l.info("check creds username=%s password=%s", username, "*" * len(password))
    res: bool = api_call("employee", "check_pass", login=username, pass_=password).get("result") == "OK"

    l.log((int(not res) + 2) * 10, "check creds result=%s", res)
    return res
