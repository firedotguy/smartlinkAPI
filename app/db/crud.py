from app.api.employee import get_division as api_get_division
from app.api.employee import get_employee as api_get_employee
from app.db import Session
from app.db.models import Division, Employee, Ont
from app.utils.logger import get_logger
from app.utils.token import mask_token

l = get_logger("db.crud")


def set_employee(db: Session, id: int, username: str, token: str):
    l.info("set employee id=%s username=%s token=%s", id, username, mask_token(token))

    employee = db.query(Employee).where(Employee.id == id).first()
    if employee:
        employee.username = username  # на всякий случай
        employee.token = token
        l.debug("update employee")
    else:
        employee = api_get_employee(id)
        if not employee:
            l.error("employee not found")
            return

        db.add(Employee(id=id, username=username, token=token, name=employee.name, role=employee.role))
        l.debug("create employee")
    db.commit()


def get_employee_name(db: Session, id: int) -> str | None:
    l.debug("get employee name id=%s", id)
    employee = db.query(Employee).where(Employee.id == id).first()
    if employee:
        return employee.name

    l.warning("employee not found in db")
    employee = api_get_employee(id)
    if employee:
        db.add(Employee(id=id, role=employee.role, username=employee.username, name=employee.name))
        db.commit()
        return employee.name
    l.error("employee not found")


def get_division_name(db: Session, id: int) -> str | None:
    l.debug("get division name id=%s", id)
    division = db.query(Division).where(Division.id == id).first()
    if division:
        return division.name

    l.warning("division not found in db")
    division = api_get_division(id)
    if division:
        db.add(Division(id=id, name=division.name, comment=division.comment))
        db.commit()
        return division.name
    l.error("division not found")


def get_divisions(db: Session) -> list[Division]:
    l.debug("get divisions")
    return db.query(Division).all()


def check_token(db: Session, token: str):
    l.debug("check token token=%s", mask_token(token))
    res = db.query(Employee).where(Employee.token == token).first() is not None

    l.log((int(not res) + 1) * 10, "check token result=%s", res)
    return res


def get_employee(db: Session, token: str):
    l.info("get employee token=%s", mask_token(token))
    employee = db.query(Employee).where(Employee.token == token).first()

    if employee is None:
        l.error("employee not found")
        return None

    l.debug("found employee id=%s", employee.id)
    return employee


def set_ont(db: Session, sn: str, ifindex: int, ont_id: int):
    # l.info("set ont sn=%s ifindex=%s ont_id=%s", sn, ifindex, ont_id)

    ont = db.query(Ont).where(Ont.sn == sn).first()
    if ont:
        ont.ont_id = ont_id
        ont.ifindex = ifindex
        # l.debug("update ont")
    else:
        db.add(Ont(sn=sn, ont_id=ont_id, ifindex=ifindex))
        # l.debug("create ont")

    # db.commit()


def get_ont(db: Session, sn: str) -> Ont | None:
    l.info("get ont sn=%s", sn)

    ont = db.query(Ont).where(Ont.sn == sn).first()

    if ont is None:
        l.error("ont not found")
        return None

    l.debug("found ont ifindex=%s", ont.ifindex)
    return ont
