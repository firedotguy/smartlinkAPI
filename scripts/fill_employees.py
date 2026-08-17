from app.api.employee import get_employees
from app.api.inventory import get_employees_inventory_ids
from app.db import create_db, get_db
from app.db.models import Employee

create_db()
db = next(get_db())

inventories = get_employees_inventory_ids()
for employee in get_employees():
    db_employee = db.query(Employee).where(Employee.id == employee.id).first()

    if db_employee:
        db_employee.name = employee.name
        db_employee.username = employee.username
        db_employee.role = employee.role
        db_employee.inventory_id = inventories.get(employee.name)

    else:
        db.add(Employee(id=employee.id, name=employee.name, username=employee.username, role=employee.role, inventory_id=inventories.get(employee.name)))

db.commit()
