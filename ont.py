"""Module for actions with SSH OLT"""
from time import sleep, time
from select import select
from subprocess import run
from re import search, fullmatch, split

from paramiko import SSHClient, AutoAddPolicy, Channel

from config import SSH_USER, SSH_PASSWORD
from utils import format_mac

CONNECT_TIMEOUT = 5
AUTH_TIMEOUT = 5
BANNER_TIMEOUT = 3

PAGINATION = "---- More ( Press 'Q' to break ) ----"
PAGINATION_WITH_SPACES = "---- More ( Press 'Q' to break ) ----\x1b[37D                                   \x1b[37D  "
DIVIDER = '-' * 78
# RE_ONT_SUMMARY_DATA1 = r'^(\d*)\s*(online|offline)\s*((?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})|-)\s*((?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})|-)\s*(.*?)(?:\s*)$'
# RE_ONT_SUMMARY_DATA2 = r'^(\d*)\s*([A-Z0-9]+)\s*([A-Z0-9\-]+)\s*(-|\d*)\s*([0-9\-.]+)\/([0-9\-.]+).*$'

# sequence: fibre -> service -> port -> ont

def _connect_ssh(host: str) -> tuple[Channel, SSHClient, str]:
    """Connect to SSH client using paramiko"""
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(host, username=SSH_USER, password=SSH_PASSWORD, timeout=CONNECT_TIMEOUT,
        auth_timeout=AUTH_TIMEOUT, banner_timeout=BANNER_TIMEOUT, look_for_keys=False,
        allow_agent=False)

    channel = ssh.invoke_shell()
    sleep(0.2)
    _clear_buffer(channel)

    channel.send(b"enable\n")
    sleep(0.07)
    olt_name = _read_output(channel, False).splitlines()[-1].strip().rstrip('#')
    _clear_buffer(channel)

    channel.send(b"config\n")
    sleep(0.07)
    _clear_buffer(channel)
    return channel, ssh, olt_name

def search_ont(sn: str, host: str) -> tuple[dict, str | None] | None:
    """Search ONT by serial number and return its basic, optical and catv data"""
    ont_info: dict = {}
    olt_name = None
    try:
        channel, ssh, olt_name = _connect_ssh(host)

        channel.send(bytes(f"display ont info by-sn {sn}\n\n", 'utf-8'))
        parsed_ont_info = _parse_basic_info(_read_output(channel))

        if 'error' in parsed_ont_info:
            return {'status': 'offline', 'detail': parsed_ont_info['error']}, olt_name
        ont_info = parsed_ont_info

        channel.send(bytes(f"interface gpon {ont_info['interface']['fibre']}/{ont_info['interface']['service']}\n", 'utf-8'))
        sleep(0.07)
        _clear_buffer(channel)

        if ont_info.get('online'):
            channel.send(bytes(f"display ont optical-info {ont_info['interface']['port']} {ont_info['ont_id']}\n", 'utf-8'))
            optical_info = _parse_optical_info(_read_output(channel))
            ont_info['optical'] = optical_info

        catv_results = []
        for port_num in range(1, (ont_info['_catv_ports'] or 2) + 1):
            sleep(0.07)
            channel.send(bytes(f"display ont port attribute {ont_info['interface']['port']} {ont_info['ont_id']} catv {port_num}\n\n", 'utf-8'))
            catv = _parse_port_status(_read_output(channel))
            catv_results.append(catv)

        channel.send(bytes(f"display ont port state {ont_info['interface']['port']} {ont_info['ont_id']} eth-port all\n\n", 'utf-8'))
        eth_results = _parse_eth_ports_status(_read_output(channel))

        ont_info['catv'] = catv_results
        ont_info['eth'] = eth_results
        del ont_info['_catv_ports']

        channel.send(b'quit\n') # quit from interface
        sleep(0.07)
        _clear_buffer(channel)

        channel.send(bytes(
            f"display service-port port "
            f"{ont_info['interface']['fibre']}/{ont_info['interface']['service']}/{ont_info['interface']['port']} "
            f"ont {ont_info['ont_id']}\n\n", 'utf-8' # extra \n for pass command ("{ <cr>|autosense<K>|e2e<K>|ont<K>|sort-by<K> }:")
        ))
        ont_info['service_port'] = _parse_service_port(_read_output(channel), ont_info['interface'])
        if ont_info['service_port']:
            sleep(0.07)
            channel.send(bytes(f'display mac-address service-port {ont_info["service_port"]}\n', 'utf-8'))
            ont_info['mac'] = _parse_mac(_read_output(channel))

        channel.close()
        ssh.close()

        ping_result = _ping(ont_info['ip']) if 'ip' in ont_info else None
        ont_info['ping'] = float(ping_result.split(' ', maxsplit=1)[0]) if ping_result else None
        return ont_info, olt_name
    except Exception as e:
        print(f'error search ont: {e.__class__.__name__}: {e}')
        return {'online': False, 'detail': str(e)}, olt_name


def reset_ont(host: str, id: int, interface: dict) -> dict:
    """Restart/reset ONT"""
    try:
        channel, ssh, _ = _connect_ssh(host)

        channel.send(bytes(f"interface gpon {interface['fibre']}/{interface['service']}\n", 'utf-8'))
        sleep(0.1)
        _clear_buffer(channel)

        channel.send(bytes(f"ont reset {interface['port']} {id}\n", 'utf-8'))
        sleep(0.2)
        channel.send(b'y\n') # confirmation
        sleep(2)
        out = _read_output(channel)
        if 'Failure:' in out:
            print(f'error reset ont: failure: {out.split("Failure:")[1]}')
            return {'status': 'fail', 'detail': out.split('Failure:')[1].split('\n')[0]}

        channel.close()
        ssh.close()
        return {'status': 'success', 'id': id}
    except Exception as e:
        print(f'error reset ont: {e.__class__.__name__}: {e}')
        return {'status': 'fail', 'detail': e}


def toggle_catv(host: str, id: int, catv_id: int, state: bool, interface: dict) -> tuple[dict, int]:
    """Toggle CATV port state"""
    try:
        channel, ssh, _ = _connect_ssh(host)

        channel.send(bytes(f"interface gpon {interface['fibre']}/{interface['service']}\n", 'utf-8'))
        sleep(0.1)
        _clear_buffer(channel)

        channel.send(bytes(f'ont port attribute {interface["port"]} {id} catv {catv_id} operational-state {"on" if state else "off"}\n', 'utf-8'))
        output = _read_output(channel, False)
        if 'Failure: Make configuration repeatedly' in output:
            return {'status': 'fail', 'detail': 'CATV port is already in the requested state'}, 409

        channel.close()
        ssh.close()
        return {'status': 'success'}, 200
    except Exception as e:
        print(f'error toggle catv: {e.__class__.__name__}: {e}')
        return {'status': 'fail', 'detail': e}, 500

def get_ont_summary(host: str, interface: dict) -> dict:
    """get all onts from port"""
    try:
        channel, ssh, _ = _connect_ssh(host)

        channel.send(bytes(f"display ont info summary {interface['fibre']}/{interface['service']}/{interface['port']}\n", 'utf-8'))
        online, offline, onts = _parse_onts_info(_read_output((channel)))
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

def _clear_buffer(channel: Channel):
    """Clear console buffer"""
    if channel.recv_ready():
        channel.recv(32768)

def _read_output(channel: Channel, force: bool = True):
    """Read console output"""
    output = ""
    last_data_time = time()
    start_time = time()

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
                if output.strip().endswith('#') and (len(output.strip().strip('\n').splitlines()) > 5 or not force):
                    print('command completed')
                    break
                sleep(0.05)

        if time() - last_data_time > 2 and len(output.strip().strip('\n').splitlines()) > 5:
            print('no new data more than 2 seconds')
            break
        if time() - last_data_time > 10 and len(output.strip().strip('\n').splitlines()) <= 5:
            print('no new data more than 10 seconds')
            print(output)
            break
        if time() - start_time > 5 and not force:
            print('read output takes more than 5 seconds')
            break
        if time() - start_time > 20:
            print('read output takes more than 20 seconds')
            print(output)
            break
        sleep(0.01)
    return '\n'.join(output.splitlines()[1:]) if output.count('\n') > 1 else output

def _parse_output(raw: str) -> tuple[dict, list[list[dict]]]:
    def _parse_value(value: str) -> str | float | int | bool | None:
        value = value.strip().rstrip('/')
        value = split(r"\+06:00|%|\(\w*\)$", value, maxsplit=1)[0] # remove "+06:00", "%", and units

        if value == '-':
            return None
        if fullmatch(r'[+-]?\d+[.,]\d+', value):
            return float(value.replace(',', '.'))
        if fullmatch(r'[+-]?\d+', value):
            return int(value)
        if value.lower() in ('online', 'enable', 'support', 'concern', 'on', 'up'):
            return True
        if value.lower() in ('offline', 'disable', 'not support', 'unconcern', 'off', 'down'):
            return False
        return value

    def _find_all(string: str, finding: str) -> list[int]:
        result = []
        for i, _ in enumerate(string):
            if string[i:i + len(finding)] == finding:
                if len(string) > i + len(finding):
                    if string[i + len(finding)] == ' ':
                        result.append(i)
                else:
                    result.append(i)
        return result

    fields = {}
    tables = []
    is_table = False
    is_table_heading = False
    table_heading_raw = ''
    is_notes = False
    table_fields = []

    raw = raw.replace(PAGINATION, '').replace('\x1b[37D', '').replace('x1b[37D', '') # remove stupid pagination
    if "Command:" in raw:
        raw = raw.split("Command:", 1)[1]
        raw = "\n".join(raw.splitlines()[2:])
    for line in raw.splitlines():
        if '#' in line: # prompt lines
            continue

        if fullmatch(r'\s*\-{5,}\s*', line.strip()): # divider line
            is_notes = False
            if is_table_heading:
                is_table_heading = False
                continue
            if is_table and not is_table_heading:
                is_table = False
            continue

        # if line == PAGINATION: # pagination line
        #     continue

        # if PAGINATION in line: # partially-pagination line
        #     line = line.strip(PAGINATION).strip('\x1b[37D').strip('x1b[37D')

        if line.strip().startswith('Note') or is_notes: # notes line
            is_notes = True
            continue

        if ':' in line: # standalone field line
            is_table = False
            pair = list(map(lambda i: i.strip(), line.strip().split(':', maxsplit=1)))
            fields[pair[0]] = _parse_value(pair[-1])
            continue

        if is_table and not is_table_heading: # table field line
            tables[-1].append({key: _parse_value(value.strip()) for key, value in zip(table_fields, split(r'\s+', line.strip()))})
            continue

        if not is_table and len(split(r'\s+', line)) > 1: # table start heading line
            is_table = True
            is_table_heading = True
            table_heading_raw = line
            table_fields = [c for c in split(r'\s+', line.strip()) if c]
            tables.append([])
            continue

        if is_table_heading: # table next heading line
            line = line[len(table_heading_raw) - len(table_heading_raw.lstrip()):]
            full_line = line
            # print('begin table parse; fields:', table_fields, 'appendixes line:', line)

            for i, field in enumerate(table_fields):
                raw_index = _find_all(table_heading_raw.lstrip(), field)[table_fields[:i].count(field)]
                # print('found fields:', _find_all(table_heading_raw.lstrip(), field))

                if search(r'\w', full_line[raw_index:raw_index + len(field)]):
                    # print('found non space appendix:', full_line[raw_index:raw_index + len(field)] + '... for', field)
                    appendix = line.lstrip().split(' ', maxsplit=1)[0]
                    # print('cleaned appendix:', appendix)
                    table_fields[i] += '-' + appendix
                    # print('invoked to field:', table_fields[i])
                    line = line[line.index(appendix) + len(appendix):]
                    # print('line truncated:', line)

                else:
                    # print('found space appendix for', field)
                    # spaces += len(table_heading_raw[:raw_index]) - len(table_heading_raw[:raw_index].rstrip()) - 1
                    line = line[len(field):]
                    # print('line truncated:', line)

    return fields, [table for table in tables if table]

def _parse_basic_info(raw: str) -> dict:
    """Parse basic ONT info"""
    if 'The required ONT does not exist' in raw:
        raise ValueError('ONT not found')
    if '% Parameter error' in raw:
        raise ValueError('ONT not found')
    data, tables = _parse_output(raw)
    if data.get('ONT online duration'):
        uptime = fullmatch(r'^(\d*) day\(s\), (\d*) hour\(s\), (\d*) minute\(s\), (\d*) second', data['ONT online duration'])
    else:
        uptime = None
    ports_table = [table for table in tables if {'Port-number', 'Max-adaptive-number', 'Port-type'} == set(table[0].keys())]
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
        'temp': data.get('Temperature'),
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
        '_catv_ports': next((item.get('Port-number') for item in ports_table or [] if item.get('Port-type') == 'CATV'), None),
        # '_eth_ports': next((item.get('Port-number') for item in ports_table or [] if item.get('Port-type') == 'ETH'), None)
    }

def _parse_optical_info(raw: str) -> dict:
    """Parse ONT optical info"""
    if 'The ONT is not online' in raw:
        return {'status': 'fail', 'detail': 'ONT is not online'}
    data, _ = _parse_output(raw)

    return {
        'rx': data.get('Rx optical power(dBm)'),
        'tx': data.get('Tx optical power(dBm)'),
        'temp': data.get('Temperature(C)'),
        'bias': data.get('Laser bias current(mA)'),
        'olt_rx': data.get('OLT Rx ONT optical power(dBm)'),
        'prec': data.get('Optical power precision(dBm)'),
        'catv_rx': data.get('CATV Rx optical power(dBm)'),
        'voltage': data.get('Voltage(V)'),
        'vendor': {
            'name': data.get('Vendor name'),
            'rev': data.get('Vendor rev'),
            'pn': data.get('Vendor PN'),
            'sn': data.get('Vendor SN')
        }
    }

def _parse_port_status(raw: str) -> bool:
    """Parse ONT port status"""
    _, tables = _parse_output(raw)
    return tables[0][0].get('Port-switch') or tables[0][0].get('switch') or tables[0][0].get('Port') or False

def _parse_eth_ports_status(raw: str) -> list[dict]:
    """Parse ONT eth ports status"""
    _, tables = _parse_output(raw)
    return [{'id': table.get('ONT-port-ID'), 'status': table.get('LinkState') or False, 'speed': table.get('Speed-(Mbps)')} for table in tables[0]]

def _parse_service_port(raw: str, interface: dict) -> int | None:
    raw = raw.replace(
        f"{interface['fibre']}/{interface['service']} /{interface['port']}",
        f"{interface['fibre']}/ {interface['service']}/ {interface['port']}"
    ) # change F/S /P -> F/ S/ P/
    raw = raw.replace(' Switch-Oriented Flow List\n', '') # remove extra text
    if 'Failure: No service virtual port can be operated' in raw:
        return
    return _parse_output(raw)[1][0][0].get('INDEX')

def _parse_mac(raw: str) -> str | None:
    if 'Failure: There is not any MAC address record' in raw:
        return
    raw = raw.replace('MAC TYPE', 'MAC-TYPE') # avoid extra spaces for better parsing (prefer "-")
    return format_mac(_parse_output(raw)[1][0][0].get('MAC'))

def _parse_onts_info(output: str) -> tuple[int, int, list[dict]] | tuple[dict, None, None]:
    out = [line.strip() for line in (output.replace(PAGINATION_WITH_SPACES, "").split(DIVIDER))]

    if len(out) < 2:
        return {"status": "fail", "detail": "not enough sections"}, None, None

    total = fullmatch(r'^In port \d*/\d*/\d*, the total of ONTs are: (\d*), online: (\d*)$', out[1])
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

def _ping(ip: str) -> None | str:
    """Ping ONT by IP"""
    try:
        result = run(['ping', '-c', '1', '-W', '300', ip], capture_output=True, text=True, timeout=1)

        if result.returncode == 0:
            time_match = search(r'time=([0-9.]+)', result.stdout)
            return f"{time_match.group(1)} ms" if time_match else "-"
        return None
    except Exception:
        return None