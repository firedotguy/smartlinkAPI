from re import search
from subprocess import run


def _ping(ip: str) -> int | None:
    """Ping ONT by IP"""
    try:
        result = run(["ping", "-c", "1", "-W", "300", ip], capture_output=True, text=True, timeout=1)

        if result.returncode == 0:
            time_match = search(r"time=([0-9.]+)", result.stdout)
            if time_match:
                return int(time_match.group(1))

    except Exception:
        return
