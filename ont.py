from time import sleep, time
from select import select
from subprocess import run
from re import search, fullmatch

from paramiko import SSHClient, AutoAddPolicy, Channel
from config import ssh_user, ssh_password

CONNECT_TIMEOUT = 5
AUTH_TIMEOUT = 5
BANNER_TIMEOUT = 3
# sequence: fibre -> service -> port -> ont

def connect_ssh(host: str) -> tuple[Channel, SSHClient]:
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(host, username=ssh_user, password=ssh_password, timeout=CONNECT_TIMEOUT, auth_timeout=AUTH_TIMEOUT,
        banner_timeout=BANNER_TIMEOUT, look_for_keys=False, allow_agent=False)

    channel = ssh.invoke_shell()
    sleep(0.3)
    clear_buffer(channel)
    channel.send(bytes("enable\n", 'utf-8'))
    sleep(0.1)
    clear_buffer(channel)
    return channel, ssh

def search_ont(sn: str, host: str) -> None | dict:
    start_time = time()
    ont_info: dict = {}
    try:
        channel, ssh = connect_ssh(host)

        channel.send(bytes(f"display ont info by-sn {sn}\n", 'utf-8'))
        sleep(1)

        parsed_ont_info = parse_basic_info(read_output(channel))

        if not parsed_ont_info:
            return
        ont_info = parsed_ont_info

        channel.send(bytes("config\n", 'utf-8'))
        sleep(0.1)
        clear_buffer(channel)

        channel.send(bytes(f"interface gpon {ont_info['interface']['fibre']}/{ont_info['interface']['service']}\n", 'utf-8'))
        sleep(0.1)
        clear_buffer(channel)


        channel.send(bytes(f"display ont optical-info {ont_info['interface']['port']} {ont_info['ont_id']}\n", 'utf-8'))
        sleep(0.2)
        if ont_info['status'] != 'offline':
            optical_info = parse_optical_info(read_output(channel))
            ont_info['optical'] = optical_info

        catv_results = []
        for port_num in [1, 2]:
            channel.send(bytes(f"display ont port attribute {ont_info['interface']['port']} {ont_info['ont_id']} catv {port_num}\n", 'utf-8'))
            sleep(0.2)
            catv = parse_catv_status(read_output(channel))
            catv_results.append(catv)

        ont_info['catv'] = catv_results

        channel.close()
        ssh.close()

        ping_result = ping(ont_info['ip'].split('/')[0] if ont_info.get('ip') else None)

        ont_info['ping'] = float(ping_result.split(' ')[0]) if ping_result else None
    except Exception as e:
        print(f'error search ont: {e.__class__.__name__}: {e}')
        ont_info.update({'status': 'offline', 'error': str(e)})
    finally:
        if ont_info == {}: return
        ont_info['duration'] = time() - start_time
        return ont_info


def get_summary(host: str, interface: dict) -> dict:
    try:
        channel, ssh = connect_ssh(host)
        channel.send(bytes("config\n", 'utf-8'))
        sleep(0.1)
        clear_buffer(channel)

        channel.send(bytes(f"display ont info summary {interface['fibre']}/{interface['service']}/{interface['port']}\n", 'utf-8'))
        sleep(0.2)
        out = [line.strip() for line in (read_output(channel)
               .replace("---- More ( Press 'Q' to break ) ----\x1b[37D                                     \x1b[37D  ", '')
               .split('------------------------------------------------------------------------------'))]
        if len(out) < 6:
            return {'status': 'fail', 'detail': 'not enough sections'}
        total = fullmatch(r'^In port \d*/\d*/\d*, the total of ONTs are: (\d*), online: (\d*)$', out[1])
        if total is None:
            print('error summary ont: total regexp fail')
            return {'status': 'fail', 'detail': 'total regexp fail'}
        online = int(total.group(1))
        offline = int(total.group(2))
        onts = []
        for ont, ont2 in zip(out[3].splitlines(), out[5].splitlines()):
            match = fullmatch(r'^(\d*)\s*(online|offline)\s*((?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})|-)\s*((?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})|-)\s*(.*?)(?:\s*)$', ont.strip())
            match2 = fullmatch(r'^(\d*)\s*([A-Z0-9]+)\s*([A-Z0-9\-]+)\s*(-|\d*)\s*([0-9\-.]+)\/([0-9\-.]+).*$', ont2.strip())
            if match is not None and match2 is not None:
                onts.append({
                    'id': _parse_int(match.group(1)),
                    'status': match.group(2),
                    'uptime': match.group(3),
                    'downtime': match.group(4),
                    'cause': match.group(5),
                    'sn': match2.group(2),
                    'name': match2.group(3),
                    'distance': _parse_int(match2.group(4)),
                    'rx': _parse_float(match2.group(5)),
                    'tx': _parse_float(match2.group(6))
                })

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
    try:
        channel, ssh = connect_ssh(host)
        channel.send(bytes("config\n", 'utf-8'))
        sleep(0.1)
        clear_buffer(channel)

        channel.send(bytes(f"interface gpon {interface['fibre']}/{interface['service']}\n", 'utf-8'))
        sleep(0.1)
        clear_buffer(channel)

        channel.send(bytes(f"ont reset {interface['port']} {id}\n", 'utf-8'))
        sleep(0.2)
        channel.send(bytes('y\n', 'utf-8')) # confirmation
        sleep(3)
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
    if channel.recv_ready():
        channel.recv(32768)

def read_output(channel: Channel):
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
                if "---- More ( Press 'Q' to break ) ----" in data:
                    channel.send(bytes(" ", 'utf-8'))
                    continue

                # command completed ("user#" input in data)
                if data.strip().endswith('#'):
                    break
                sleep(0.05)
        else:
            # if no data more than 5 seconds
            if time() - last_data_time > 5:
                break

    return output

def _parse_int(data: str | None) -> int | None:
    if data is None: return None
    if data == '-': return None
    data = data.replace('(C)', '').replace('%', '').strip()
    if data.isdigit(): return int(data)

def _parse_float(data: str | None) -> float | None:
    if data is None: return None
    if data == '-': return None
    data = data.replace('(C)', '').replace('%', '').strip()
    return float(data)

def _parse_str(data: str | None, filter = lambda e: e) -> str | None:
    if data is None: return None
    if data == '-': return None
    data = filter(data)
    return data

def parse_basic_info(output: str) -> dict | None:
    if 'The required ONT does not exist' in output:
        return {'error': 'ONT не найден'}
    data = {}
    for line in output.replace("---- More ( Press 'Q' to break ) ----\x1b[37D                                     \x1b[37D  ", '').splitlines():
        if ':' in line:
            data[line.split(':', 1)[0].strip()] = line.split(':', 1)[1].strip()
    if 'ONT online duration' in data:
        uptime = fullmatch(r'^(\d*) day\(s\), (\d*) hour\(s\), (\d*) minute\(s\), (\d*) second\(s\)$', data['ONT online duration'])
    else:
        uptime = None
    if 'ONT-ID' not in data: return None
    return {
        'interface': {
            'name': data['F/S/P'],
            'fibre': int(data['F/S/P'].split('/')[0]),
            'service': int(data['F/S/P'].split('/')[1]),
            'port': int(data['F/S/P'].split('/')[2])
        },
        'ont_id': _parse_int(data.get('ONT-ID')),
        'status': data.get('Run state', 'unknown'),
        'mem_load': _parse_int(data.get('Memory occupation')),
        'cpu_load': _parse_int(data.get('CPU occupation')),
        'temp': _parse_int(data['Temperature']),
        'ip': _parse_str(data.get('ONT IP 0 address/mask'), lambda e: e.split('/')[0]),
        'last_down_cause': _parse_str(data.get('Last down cause')),
        'last_down': _parse_str(data.get('Last down time'), lambda e: e.rstrip('+06:00')),
        'last_up': _parse_str(data.get('Last up time'), lambda e: e.rstrip('+06:00')),
        'uptime': {
            'data': uptime.group(0),
            'days': int(uptime.group(1)),
            'hours': int(uptime.group(2)),
            'minutes': int(uptime.group(3)),
            'seconds': int(uptime.group(4))
        } if uptime else None
    }

def parse_optical_info(output) -> dict:
    data = {}
    for line in output.splitlines():
        if ':' in line:
            data[line.split(':', 1)[0].strip()] = line.split(':', 1)[1].strip()

    return {
        'rx': _parse_float(data.get('Rx optical power(dBm)')),
        'tx': _parse_float(data.get('Tx optical power(dBm)')),
        'temp': _parse_int(data.get('Temperature(C)'))
    }

def parse_catv_status(output: str) -> bool:
    lines = [line.strip() for line in output.splitlines()]
    if 'port-ID  port-type  switch' not in lines: return False
    line = lines[lines.index('port-ID  port-type  switch') + 2]
    data = line.replace('  ', ' ').replace('  ', ' ').replace('  ', ' ').replace('  ', ' ').split(' ')
    return data[3] == 'on'

def ping(ip: None | str) -> None | str:
    if not ip or ip in ['-', 'N/A', '']:
        return None

    try:
        result = run(['ping', '-c', '1', '-W', '300', ip], capture_output=True,
            text=True, timeout=1)

        if result.returncode == 0:
            time_match = search(r'time=([0-9.]+)', result.stdout)
            return f"{time_match.group(1)} ms" if time_match else "-"
        return None
    except:
        return None