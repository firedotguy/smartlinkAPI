from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.enums import Role


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, index=True)
    last_seen: Mapped[datetime | None]

    role: Mapped[Role] = mapped_column(default=Role.operator)
    username: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    token: Mapped[str | None]


class Division(Base):
    __tablename__ = "divisions"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, index=True)
    name: Mapped[str]
    comment: Mapped[str | None]


# class Action(Base):
#     __tablename__ = "actions"

#     id: Mapped[int] = mapped_column(primary_key=True, unique=True, index=True)
#     made_at: Mapped[datetime] = mapped_column(server_default=func.now())
#     type: Mapped[ActionType]


class Ont(Base):
    __tablename__ = "onts"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, index=True)
    sn: Mapped[str] = mapped_column(unique=True, index=True)
    # olt_id: Mapped[int]
    ont_id: Mapped[int]
    ifindex: Mapped[int]
