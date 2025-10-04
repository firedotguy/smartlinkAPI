"""Module for actions with SSH OLT"""
from time import sleep, time
from select import select
from subprocess import run
from re import search, fullmatch, split

from paramiko import SSHClient, AutoAddPolicy, Channel
from config import SSH_USER, SSH_PASSWORD

CONNECT_TIMEOUT = 5
AUTH_TIMEOUT = 5
BANNER_TIMEOUT = 3

PAGINATION = "---- More ( Press 'Q' to break ) ----"
PAGINATION_WITH_SPACES = "---- More ( Press 'Q' to break ) ----\x1b[37D                                   \
\x1b[37D  "
DIVIDER = '-' * 78
RE_ONT_SUMMARY_TOTAL = r'^In port \d*/\d*/\d*, the total of ONTs are: (\d*), online: (\d*)$'
RE_ONT_SUMMARY_DATA1 = r'^(\d*)\s*(online|offline)\s*((?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})|-)\
\s*((?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})|-)\s*(.*?)(?:\s*)$'
RE_ONT_SUMMARY_DATA2 = r'^(\d*)\s*([A-Z0-9]+)\s*([A-Z0-9\-]+)\s*(-|\d*)\s*([0-9\-.]+)\/([0-9\-.]+)\
.*$'
RE_ONT_SEARCH_ONLINE = r'^(\d*) day\(s\), (\d*) hour\(s\), (\d*) minute\(s\), (\d*) second'

# sequence: fibre -> service -> port -> ont

def connect_ssh(host: str) -> tuple[Channel, SSHClient, str]:
    """Connect to SSH client using paramiko"""
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(host, username=SSH_USER, password=SSH_PASSWORD, timeout=CONNECT_TIMEOUT,
        auth_timeout=AUTH_TIMEOUT, banner_timeout=BANNER_TIMEOUT, look_for_keys=False,
        allow_agent=False)

    channel = ssh.invoke_shell()
    sleep(0.2)
    clear_buffer(channel)

    channel.send(b"enable\n")
    sleep(0.05)
    olt_name = read_output(channel).splitlines()[-1].strip().rstrip('#')
    clear_buffer(channel)

    channel.send(b"config\n")
    sleep(0.05)
    clear_buffer(channel)
    return channel, ssh, olt_name

def search_ont(sn: str, host: str) -> tuple[dict, str | None] | None:
    """Search ONT by serial number and return its basic, optical and catv data"""
    start_time = time()
    ont_info: dict = {}
    olt_name = None
    try:
        channel, ssh, olt_name = connect_ssh(host)

        channel.send(bytes(f"display ont info by-sn {sn}\n", 'utf-8'))
        sleep(2.3)
        parsed_ont_info = parse_basic_info(read_output(channel))

        if 'error' in parsed_ont_info:
            return {'status': 'offline', 'detail': parsed_ont_info['error']}, olt_name
        ont_info = parsed_ont_info

        channel.send(bytes(f"interface gpon {ont_info['interface']['fibre']}/{ont_info['interface']['service']}\n", 'utf-8'))
        sleep(0.1)
        clear_buffer(channel)

        channel.send(bytes(f"display ont optical-info {ont_info['interface']['port']} {ont_info['ont_id']}\n", 'utf-8'))
        sleep(0.1)
        if ont_info.get('online'):
            optical_info = parse_optical_info(read_output(channel))
            ont_info['optical'] = optical_info

        catv_results = []
        for port_num in range(1, (ont_info['_catv_ports'] or 2) + 1):
            channel.send(bytes(f"display ont port attribute {ont_info['interface']['port']} {ont_info['ont_id']} catv {port_num}\n", 'utf-8'))
            sleep(0.1)
            catv = parse_catv_status(read_output(channel))
            catv_results.append(catv)

        ont_info['catv'] = catv_results

        channel.close()
        ssh.close()

        ping_result = ping(ont_info['ip']) if 'ip' in ont_info else None

        ont_info['ping'] = float(ping_result.split(' ', maxsplit=1)[0]) if ping_result else None
        return ont_info, olt_name
    except Exception as e:
        print(f'error search ont: {e.__class__.__name__}: {e}')
        return {'online': False, 'detail': str(e)}, olt_name

def get_ont_summary(host: str, interface: dict) -> dict:
    """get all onts from port"""
    try:
        channel, ssh, _ = connect_ssh(host)

        channel.send(bytes(f"display ont info summary {interface['fibre']}/{interface['service']}/{interface['port']}\n", 'utf-8'))
        sleep(0.1)
        online, offline, onts = parse_onts_info(read_output((channel)))
        if isinstance(online, dict):
            return online # error

        channel.close()
        ssh.close()
        return {
            'status': 'success',
            'online': online,
            'offline': offline,
            'onts': onts
        }

    except Exception as e:
        print(f'error summary ont: {e.__class__.__name__}: {e}')
        return {'status': 'fail', 'detail': e}


def reset_ont(host: str, id: int, interface: dict) -> dict:
    """Restart/reset ONT"""
    try:
        channel, ssh, _ = connect_ssh(host)

        channel.send(bytes(f"interface gpon {interface['fibre']}/{interface['service']}\n", 'utf-8'))
        sleep(0.1)
        clear_buffer(channel)

        channel.send(bytes(f"ont reset {interface['port']} {id}\n", 'utf-8'))
        sleep(0.2)
        channel.send(b'y\n') # confirmation
        sleep(2)
        out = read_output(channel)
        if 'Failure:' in out:
            print(f'error reset ont: failure: {out.split("Failure:")[1]}')
            return {'status': 'fail', 'detail': out.split('Failure:')[1].split('\n')[0]}

        channel.close()
        ssh.close()
        return {'status': 'success', 'id': id}
    except Exception as e:
        print(f'error reset ont: {e.__class__.__name__}: {e}')
        return {'status': 'fail', 'detail': e}

def clear_buffer(channel: Channel):
    """Clear console buffer"""
    if channel.recv_ready():
        channel.recv(32768)

def read_output(channel: Channel):
    """Read console output"""
    output = ""
    last_data_time = time()

    while True:
        ready, _, _ = select([channel], [], [], 0.05)
        if ready:
            data = channel.recv(32768).decode('utf-8', errors='ignore')
            if data:
                output += data
                last_data_time = time()
                # pagination
                if PAGINATION in data:
                    channel.send(b" ")
                    continue

                # command completed ("user#" input in data)
                if data.strip().endswith('#'):
                    break
                sleep(0.05)
        else:
            # if no data more than 1 seconds
            if time() - last_data_time > 1:
                break
        sleep(0.01)

    return output

def _parse_output(raw: str) -> tuple[dict, list[list[dict]]]:
    def _parse_value(value: str) -> str | float | int | bool | None:
        value = value.strip()
        value = split(r"06:00|%|\(\w*\)$", value, maxsplit=1)[0] # remove "+06:00", "%", and units

        if value == '-':
            return None
        if fullmatch(r'[+-]?\d+[.,]\d+', value):
            return float(value.replace(',', '.'))
        if fullmatch(r'[+-]?\d+', value):
            return int(value)
        if value.lower() in ('online', 'enable', 'support', 'concern', 'on'):
            return True
        if value.lower() in ('offline', 'disable', 'not support', 'unconcern', 'off'):
            return False
        return value

    fields = {}
    tables = []
    is_table = False
    is_table_heading = False
    is_notes = False
    table_fields = []

    for line in raw.splitlines()[1:-1]: # cut promprt lines
        line = line.strip() # remove whitespaces

        if fullmatch(r'\-{5,}', line): # divider line
            is_notes = False
            if is_table_heading:
                is_table_heading = False
                continue
            if is_table and not is_table_heading:
                is_table = False
            continue

        if PAGINATION in line: # pagination line
            continue

        if line.startswith('Notes:') or is_notes: # notes line
            is_notes = True
            continue

        if ':' in line: # standalone field line
            is_table = False
            pair = list(map(lambda i: i.strip(), line.split(':', maxsplit=1)))
            fields[pair[0]] = _parse_value(pair[1])
            continue

        if is_table and not is_table_heading: # table field line
            assert tables
            tables[-1].append({key: _parse_value(value) for key, value in zip(table_fields, split(r'\s+', line))})
            continue

        if not is_table and len(split(r'\s{2,}', line)) > 1: # table heading line
            is_table = True
            is_table_heading = True
            table_fields = [c for c in split(r'\s+', line.strip()) if c]
            tables.append([])
            continue

    return fields, tables

def parse_basic_info(raw: str) -> dict:
    """Parse basic ONT info"""
    print(raw)
    if 'The required ONT does not exist' in raw:
        raise ValueError('ONT not found')
    data, tables = _parse_output(raw)
    if 'ONT online duration' in data:
        uptime = fullmatch(RE_ONT_SEARCH_ONLINE, data['ONT online duration'])
    else:
        uptime = None
    ports_table = [table for table in tables if table and ('Max-adaptive-number', 'Port-number', 'Port-type') in table[0].keys()]
    if ports_table:
        ports_table = ports_table[0]
    else:
        ports_table = None
    return {
        'interface': {
            'name': data['F/S/P'],
            'fibre': int(data['F/S/P'].split('/')[0]),
            'service': int(data['F/S/P'].split('/')[1]),
            'port': int(data['F/S/P'].split('/')[2])
        },
        'ont_id': data.get('ONT-ID'),
        'online': data.get('Run state', False),
        'mem_load': data.get('Memory occupation'),
        'cpu_load': data.get('CPU occupation'),
        'temp': data['Temperature'],
        'ip': data['ONT IP 0 address/mask'].split('/')[0] if data.get('ONT IP 0 address/mask') else None,
        'last_down_cause': data.get('Last down cause'),
        'last_down': data.get('Last down time'),
        'last_up': data.get('Last up time'),
        'uptime': {
            'data': uptime.group(0),
            'days': int(uptime.group(1)),
            'hours': int(uptime.group(2)),
            'minutes': int(uptime.group(3)),
            'seconds': int(uptime.group(4))
        } if uptime else None,
        '_catv_ports': [item for item in ports_table if item.get('Port-type') == 'CATV'][0] if ports_table else None,
        '_eth_ports': [item for item in ports_table if item.get('Port-type') == 'ETH'][0] if ports_table else None
    }

def parse_optical_info(raw: str) -> dict:
    """Parse ONT optical info"""
    print(raw)
    data, _ = _parse_output(raw)

    return {
        'rx': data.get('Rx optical power(dBm)'),
        'tx': data.get('Tx optical power(dBm)'),
        'temp': data.get('Temperature(C)'),
        'bias': data.get('Laser bias current(mA)'),
        'olt_rx': data.get('OLT Rx ONT optical power(dBm)'),
        'prec': data.get('Optical power precision(dBm)'),
        'catv_rx': data.get('CATV Rx optical power(dBm)'),
        'vendor': {
            'name': data.get('Vendor name'),
            'rev': data.get('Vendor rev'),
            'pn': data.get('Vendor PN'),
            'sn': data.get('Vendor SN')
        }
    }

def parse_catv_status(raw: str) -> bool:
    """Parse ONT CATV status"""
    _, tables = _parse_output(raw)
    print(tables[0][0])
    return tables[0][0].get('switch') or tables[0][0].get('Port') or False

def parse_onts_info(output: str) -> tuple[int, int, list[dict]] | tuple[dict, None, None]:
    out = [line.strip() for line in (output.replace(PAGINATION_WITH_SPACES, "").split(DIVIDER))]

    if len(out) < 2:
        return {"status": "fail", "detail": "not enough sections"}, None, None

    total = fullmatch(RE_ONT_SUMMARY_TOTAL, out[1])
    if total is None:
        print("error summary ont: total regexp fail")
        return {"status": "fail", "detail": "total regexp fail"}, None, None

    online = int(total.group(1))
    offline = int(total.group(2))

    onts: list[dict] = []

    for section in out[2:]:
        if not section or len(section) < 10:
            continue

        fields, _ = _parse_output(section)

        ont_id = fields.get("ONT-ID")
        if ont_id is None:
            continue

        ont = {
            "id": ont_id,
            "status": fields.get("Run state"),
            "uptime": fields.get("ONT online duration"),
            "downtime": fields.get("Last down time"),
            "cause": fields.get("Last down cause"),
            "sn": fields.get("SN"),
            "name": fields.get("Description"),
            "distance": fields.get("ONT distance(m)"),
            "rx": fields.get("Optical rx power") or fields.get("RX power") or fields.get("rx"),
            "tx": fields.get("Optical tx power") or fields.get("TX power") or fields.get("tx"),
        }

        onts.append(ont)

    return online, offline, onts

def ping(ip: str) -> None | str:
    """Ping ONT by IP"""
    try:
        result = run(['ping', '-c', '1', '-W', '300', ip], capture_output=True, text=True, timeout=1)

        if result.returncode == 0:
            time_match = search(r'time=([0-9.]+)', result.stdout)
            return f"{time_match.group(1)} ms" if time_match else "-"
        return None
    except Exception:
        return None
