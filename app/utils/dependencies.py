from fastapi import Depends, HTTPException, Request

from app.db import Session
from app.db import get_db as db_dependency
from app.db.crud import get_employee


def employee_dependency(request: Request, db: Session = Depends(db_dependency)):
    token = request.cookies.get("token")
    if token is None:
        raise HTTPException(detail="unauthorized", status_code=401)

    employee = get_employee(db, token)
    if employee is None:
        raise HTTPException(detail="token not found", status_code=401)

    return employee
