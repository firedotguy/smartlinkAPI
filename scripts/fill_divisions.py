from app.api.employee import get_divisions
from app.db import create_db, get_db
from app.db.models import Division

create_db()
db = next(get_db())

divisions = get_divisions()
for division in divisions:
    db_division = db.query(Division).where(Division.id == division.id).first()

    if db_division:
        db_division.name = division.name
        db_division.comment = division.comment

    else:
        db.add(Division(id=division.id, name=division.name, comment=division.comment))

db.commit()
