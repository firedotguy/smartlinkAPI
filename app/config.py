from os import getenv
from typing import overload

from dotenv import load_dotenv

load_dotenv()


@overload
def get_str(name: str, default: str) -> str: ...


@overload
def get_str(name: str, default: None = None) -> str | None: ...


def get_str(name: str, default: str | None = None) -> str | None:
    return getenv(name, default)


def get_str_force(name: str) -> str:
    res = getenv(name)
    if res is None:
        raise ValueError(f"{name} is required dotenv param")
    return res


def get_int(name: str, default: int = 0) -> int:
    return int(getenv(name, default))


def get_bool(name: str) -> bool:
    return eval(getenv(name, "False").title())


BASE_URL = get_str_force("BASE_URL")
API_KEY = get_str_force("API_KEY")
US_LOGIN = get_str_force("US_LOGIN")
US_PASSWORD = get_str_force("US_PASSWORD")
LOG_LEVEL = get_str("LOG_LEVEL", "INFO")
LOG_COLORFUL = get_bool("LOG_COLORFUL")
HOST = get_str("HOST", "localhost")
PORT = get_int("PORT", 1000)

INSIDE_TOKEN = get_str("INSIDE_TOKEN")

SSH_USER = get_str_force("SSH_USER")
SSH_PASSWORD = get_str_force("SSH_PASSWORD")

UPDATE_ONT_INDEXES_ON_STARTUP = get_bool("UPDATE_ONT_INDEXES_ON_STARTUP")
