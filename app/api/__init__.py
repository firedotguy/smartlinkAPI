from datetime import datetime
from enum import Enum
from time import time
from typing import Literal, overload

from requests import RequestException, Session
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from app.config import API_KEY, BASE_URL, US_LOGIN, US_PASSWORD
from app.utils.logger import get_logger

l = get_logger("api")
session = Session()
authed = False
disable_warnings(category=InsecureRequestWarning)


class UpstreamError(Exception):
    def __init__(self, message: str, status: int = 502, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.payload = payload


# def get_page(url: str) -> Response:
#     l.debug('get %s', url)
#     res = get(BASE_URL + url)
#     if not res.ok:
#         l.warning('get res not ok code=%s', res.status_code)
#     return res


@overload
def api_call(
    cat: str, action: str, post: bool = ..., raw: Literal[False] = ..., file: tuple[str, bytes, str] | None = ..., timeout: int = ..., **params
) -> dict: ...


@overload
def api_call(
    cat: str, action: str, post: bool = ..., raw: Literal[True] = ..., file: tuple[str, bytes, str] | None = ..., timeout: int = ..., **params
) -> bytes: ...


def api_call(
    cat: str, action: str, post: bool = False, raw: bool = False, file: tuple[str, bytes, str] | None = None, timeout: int = 30, **params
) -> dict | bytes:
    _params = {}
    for k, v in params.items():
        k = k.rstrip("_")
        if isinstance(v, bool):
            _params[k] = int(v)
        elif isinstance(v, Enum):
            _params[k] = v.value
        elif isinstance(v, datetime):
            _params[k] = v.isoformat()
        elif v is not None:
            _params[k] = v

    l.debug("> %s.%s %s", cat, action, {k: v if k != "pass" or not isinstance(v, str) else "*" * len(v) for k, v in _params.items()})  # hide password

    start = time()
    if post:
        method = session.post
    else:
        method = session.get

    try:
        res = method(
            BASE_URL + "api.php",
            params={"cat": cat, "action": action, "key": API_KEY, **_params},
            files={"file": file} if file else None,
            timeout=timeout,
            verify=False
        )
    except RequestException as e:
        l.error("api_call failed: %s", e)
        raise UpstreamError(f"upstream unreachable: {e}", 504) from e

    if raw:
        l.debug("< raw")
        return res.content

    if not res.ok:
        l.warning("api_call res not ok code=%s", res.status_code)

    try:
        data = res.json()
    except ValueError as e:
        l.debug("< %s in %sms", res.text, round((time() - start) * 1000))
        raise UpstreamError(f"{cat}.{action} returned non-json", 502, {"body": res.text[:500]}) from e
    l.debug("< %s in %sms", data, round((time() - start) * 1000))

    if (
        isinstance(data, dict) and (data.get("Error") or data.get("error") or (str(data.get("result", "")).isdigit() and bool(int(data.get("result", 0)))))
    ) or not res.ok:
        error = data.get("Error") or data.get("error") or data.get("msg") or "unknown error"
        l.error("error: %s code=%s", error, res.status_code)
        raise UpstreamError(error, 502, data)

    return data


def custom_api_call(url: str, *, json: bool = True, **params):
    global authed
    if not authed:
        auth_us()

    l.debug("> %s %s", url, params)
    res = session.get(BASE_URL + url, params=params, timeout=30, verify=False)

    if 'url: "/body/login",' in res.text:
        l.warning("custom api call failed: re-auth")
        auth_us()
        res = session.get(BASE_URL + url, params=params, timeout=30, verify=False)

    l.debug("< %s", res.text[:1000])

    if not res.ok:
        l.warning("custom_api_call res not ok code=%s", res.status_code)
    if json and res.text:
        return res.json()
    return res.text


# def sql_call(query: str):
# return convert(
#     session.post("https://us.neotelecom.kg/settings_main/sql", data=f"command={query}", headers={"Content-Type": "application/x-www-form-urlencoded"}).text
# )


def auth_us(page: str | None = None):
    global authed

    l.info("auth userside")
    csrf = (page or session.get(BASE_URL, verify=False).text).split("_csrf: '")[-1].split("',")[0]
    session.post(f"{BASE_URL}body/login", params={"username": US_LOGIN, "password": US_PASSWORD, "_csrf": csrf}, verify=False)
    authed = True
