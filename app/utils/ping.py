from re import search
from subprocess import run

from app.utils.logger import get_logger

l = get_logger("utils.ping")


def ping(ip: str, count: int = 3) -> list[float] | None:
    l.info("ping %s count=%s", ip, count)
    try:
        result = run(["ping", "-c", str(count), "-w", str((count * 2) + 1), ip], capture_output=True, text=True, timeout=count * 2)  # max 200ms
        l.debug("ping res:")
        l.debug(result.stderr or result.stdout)

        if result.returncode != 0:
            l.warning("invalid return code %s", result.returncode)
            return

        pings = []
        for line in result.stdout.splitlines():
            match = search(r"time=(\d+.\d+) ", line)
            if match:
                pings.append(float(match.group(1)))

        return pings
    except Exception as e:
        l.error("error while ping: %s: %s", e.__class__.__name__, e)
