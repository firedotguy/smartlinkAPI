from datetime import datetime
from enum import Enum
from time import time

from requests import Session

from app.config import API_KEY, BASE_URL, US_LOGIN, US_PASSWORD
from app.utils.logger import get_logger

l = get_logger("api")
session = Session()
authed = False

# def get_page(url: str) -> Response:
#     l.debug('get %s', url)
#     res = get(BASE_URL + url)
#     if not res.ok:
#         l.warning('get res not ok code=%s', res.status_code)
#     return res


def api_call(cat: str, action: str, post: bool = False, **params) -> dict:
    _params = {}
    for k, v in params.items():
        k = k.rstrip("_")
        if isinstance(v, bool):
            _params[k] = int(v)
        elif isinstance(v, Enum):
            _params[k] = v.value
        elif isinstance(v, datetime):
            _params[k] = v.strftime("%Y.%m.%d %H:%M:%S")
        elif v:
            _params[k] = v

    l.debug("> %s.%s %s", cat, action, {k: v if k != "pass" or not isinstance(v, str) else "*" * len(v) for k, v in _params.items()})  # hide password

    start = time()
    if post:
        res = session.post(BASE_URL + "api.php", params={"cat": cat, "action": action, "key": API_KEY, **_params}, timeout=30)
    else:
        res = session.get(BASE_URL + "api.php", params={"cat": cat, "action": action, "key": API_KEY, **_params}, timeout=30)

    l.debug("< %s in %sms", res.json(), round((time() - start) * 1000))

    if not res.ok:
        l.warning("api_call res not ok code=%s", res.status_code)
    return res.json()


def custom_api_call(url: str, *, json: bool = True, **params):
    global authed
    if not authed:
        auth_us()

    l.debug("> %s %s", url, params)
    res = session.get(BASE_URL + url, params=params, timeout=30)

    if 'url: "/body/login",' in res.text:
        l.warning("custom api call failed: re-auth")
        auth_us()
        res = session.get(BASE_URL + url, params=params, timeout=30)

    l.debug("< %s", res.text)

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
    csrf = (page or session.get("https://us.neotelecom.kg/").text).split("_csrf: '")[-1].split("',")[0]
    session.post("https://us.neotelecom.kg/body/login", params={"username": US_LOGIN, "password": US_PASSWORD, "_csrf": csrf})
    authed = True
