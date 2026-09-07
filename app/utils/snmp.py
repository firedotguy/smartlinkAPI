from datetime import datetime
from re import fullmatch


def decode_sn(value: str) -> str:
    raw = value.strip()
    compact = raw.replace(" ", "")
    data: bytes | None = None

    if fullmatch(r"[A-Za-z]{4}[0-9A-Fa-f]{8}", compact):
        return compact.upper()

    if len(compact) == 16:
        try:
            data = bytes.fromhex(compact)
        except ValueError:
            data = None

    if data is None and len(raw) == 8:
        data = raw.encode("latin-1")

    if data is None or len(data) != 8:
        raise ValueError(f"unexpected sn format {value!r} ({len(raw)} chars)")

    return data[:4].decode("ascii") + data[4:].hex().upper()


def convert_status(status: int | None) -> bool | None:
    if status is None or status == -1:
        return
    return not bool(int(status) - 1)


def decode_datetime(data: str | None) -> str | None:
    if data is None:
        return

    hex = bytes.fromhex(data)
    if len(hex) < 7 or hex[:7] == b"\x00" * 7:
        return None
    year = (hex[0] << 8) | hex[1]
    return datetime(year, hex[2], hex[3], hex[4], hex[5], hex[6]).strftime("%Y.%m.%d %H:%M:%S")


def get_eth_speed(speed: int) -> int | str | None:
    if speed in (10, 5, 1):
        return 10
    if speed in (100, 6, 2):
        return 100
    if speed in (1000, 7, 3):
        return 1000
    if speed in (8, 9):
        return 10000
    if speed == 4:
        return "neg"
    return None


def check_none(value: str | int) -> str | int | None:
    if value in ("", -1, 0):
        return None
    return value
