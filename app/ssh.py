from re import search
from select import select
from time import sleep, time

from paramiko import AutoAddPolicy, Channel, SSHClient

from app.config import SSH_PASSWORD, SSH_USER
from app.utils.logger import get_logger

PAGINATION_WITH_SPACES = "---- More ( Press 'Q' to break ) ----\x1b[37D                                   \x1b[37D  "
DIVIDER = "-" * 78
# RE_ONT_SUMMARY_DATA1 = r'^(\d*)\s*(online|offline)\s*((?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})|-)\s*((?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})|-)\s*(.*?)(?:\s*)$'
# RE_ONT_SUMMARY_DATA2 = r'^(\d*)\s*([A-Z0-9]+)\s*([A-Z0-9\-]+)\s*(-|\d*)\s*([0-9\-.]+)\/([0-9\-.]+).*$'

# sequence: fibre -> service -> port -> ont
l = get_logger("ssh")


def send(channel: Channel, command: str, *, delay: float = 0.08, capture: bool = True) -> str:
    l.debug("> %s", command)
    channel.send(bytes(command + "\n", "utf-8"))
    sleep(delay)
    if capture:
        output = read_output(channel)
        l.debug("< %s", output)
        return output
    else:
        clear_buffer(channel)
        return ""


def connect_ssh(ip: str) -> tuple[Channel, SSHClient]:
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(ip, username=SSH_USER, password=SSH_PASSWORD, timeout=5, auth_timeout=5, banner_timeout=3, look_for_keys=False, allow_agent=False)

    channel = ssh.invoke_shell()
    sleep(0.2)
    clear_buffer(channel)

    send(channel, "enable", capture=False)
    send(channel, "config", capture=False)
    return channel, ssh


def get_ont(channel: Channel, sn: str) -> dict:
    ont = send(channel, f"display ont info by-sn {sn}", delay=0.1)

    if "The required ONT does not exist" in ont:
        l.error("ont not found")
        return {"detail": "ont not found", "code": 404}

    interface = search(r"F\/S\/P\s+: (\d+)\/(\d+)\/(\d+)", ont)
    if not interface:
        l.error("interface not found")
        return {"detail": "interface not found", "code": 500}

    id = search(r"ONT-ID\s+: (\d+)", ont)
    if not id:
        l.error("ont id not found")
        return {"detail": "ont id not found", "code": 500}

    return {"interface": interface, "id": int(id.group(1))}


def restart(ip: str, sn: str) -> dict | None:
    channel, ssh = connect_ssh(ip)

    ont = get_ont(channel, sn)
    if "detail" in ont:
        return ont  # dict with detail and code

    interface = ont["interface"]
    id = ont["id"]

    send(channel, f"interface gpon {interface.group(1)}/{interface.group(2)}", capture=False)
    send(channel, f"ont reset {interface.group(3)} {id}", delay=0.2, capture=False)
    res = send(channel, "y", delay=2)

    if "Failure:" in res:
        error = res.split("Failure:")[1].split("\n")[0].strip()
        l.error("error restart ont: %s", error)
        return {"detail": error, "code": 400}

    channel.close()
    ssh.close()


def toggle_catv(ip: str, sn: str, catv_id: int, state: bool) -> dict | None:
    channel, ssh = connect_ssh(ip)

    ont = get_ont(channel, sn)
    if "detail" in ont:
        return ont

    interface = ont["interface"]
    id = ont["id"]

    send(channel, f"interface gpon {interface.group(1)}/{interface.group(2)}", capture=False)
    res = send(channel, f"ont port attribute {interface.group(3)} {id} catv {catv_id} operational-state {'on' if state else 'off'}")

    if "Failure: Make configuration repeatedly" in res:
        l.error("catv port already in requested state")
        return {"detail": "port is already in the requested state", "code": 409}

    if "Failure: The ONT port ID does not exist" in res:
        l.error("catv port not found")
        return {"detail": "port not found", "code": 404}

    if "Failure:" in res:
        error = res.split("Failure:")[1].split("\n")[0].strip()
        l.error("error toggle catv: %s", error)
        return {"detail": error, "code": 400}

    channel.close()
    ssh.close()


def clear_buffer(channel: Channel):
    if channel.recv_ready():
        channel.recv(32768)


def read_output(channel: Channel):
    output = ""
    last_data_time = time()
    start_time = time()

    while True:
        ready, _, _ = select([channel], [], [], 0.05)
        if ready:
            data = channel.recv(32768).decode("utf-8", errors="ignore")
            if data:
                output += data
                last_data_time = time()
                if "---- More ( Press 'Q' to break ) ----" in data:
                    channel.send(b" ")
                    continue

                if output.strip().endswith("#") and (len(output.strip().strip("\n").splitlines()) > 5):
                    break
                sleep(0.05)

        if time() - last_data_time > 2 and len(output.strip().strip("\n").splitlines()) > 5:
            print("no new data more than 2 seconds")
            break
        if time() - last_data_time > 10 and len(output.strip().strip("\n").splitlines()) <= 5:
            print("no new data more than 10 seconds")
            print(output)
            break
        if time() - start_time > 5:
            print("read output takes more than 5 seconds")
            break
        sleep(0.01)
    return "\n".join(output.splitlines()[1:]) if output.count("\n") > 1 else output
