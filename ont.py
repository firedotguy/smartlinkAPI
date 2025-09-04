from time import sleep, time
from select import select
from subprocess import run
from re import search, sub, fullmatch, IGNORECASE

from paramiko import SSHClient, AutoAddPolicy, Channel
from config import ssh_user, ssh_password

__version__ = 'v.13.0'

def search_ont(sn: str, host: str) -> None | dict:
    start_time = time()
    ont_info: dict = {}
    try:
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(host, username=ssh_user, password=ssh_password, timeout=5, auth_timeout=5,
            banner_timeout=2, look_for_keys=False, allow_agent=False)

        channel = ssh.invoke_shell()
        sleep(0.2)
        clear_buffer(channel)
        channel.send(bytes("enable\n", 'utf-8'))
        sleep(0.1)
        clear_buffer(channel)

        channel.send(bytes(f"display ont info by-sn {sn}\n", 'utf-8'))
        sleep(1.5)

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
        sleep(1.2)
        optical_info = parse_optical_info(read_output(channel))
        ont_info['optical'] = optical_info

        catv_results = []
        for port_num in [1, 2]:
            channel.send(bytes(f"display ont port attribute {ont_info['interface']['port']} {ont_info['ont_id']} catv {port_num}\n", 'utf-8'))
            sleep(1.2)
            catv = parse_catv_status(read_output(channel))
            catv_results.append(catv)

        ont_info['catv'] = catv_results

        channel.close()
        ssh.close()

        ping_result = ping(ont_info['ip'].split('/')[0] if 'ip' in ont_info else None)

        ont_info['ping'] = float(ping_result.split(' ')[0]) if ping_result else None
    except Exception as e:
        ont_info.update({'status': 'offline', 'error': str(e)})
    finally:
        ont_info['duration'] = time() - start_time
        return ont_info

def clear_buffer(channel: Channel):
    if channel.recv_ready():
        channel.recv(32768)

def read_output(channel: Channel, timeout: int = 15):
    output = ""
    end_time = time() + timeout * 60

    while time() < end_time:
        ready, _, _ = select([channel], [], [], 0.05)
        if ready:
            data = channel.recv(32768).decode('utf-8', errors='ignore')
            if data:
                output += data

                if "---- More ( Press 'Q' to break ) ----" in data:
                    channel.send(bytes(" ", 'utf-8'))
                if '#' in data:
                    break
                sleep(0.01)

    return output

def parse_basic_info(output: str) -> dict | None:
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
        'ont_id': int(data['ONT-ID']),
        'status': data.get('Run state'),
        'mem_load': int(data['Memory occupation'].rstrip('%')) if 'Memory occupation' in data else None,
        'cpu_load': int(data['CPU occupation'].rstrip('%')) if 'CPU occupation' in data else None,
        'temp': int(data['Temperature'].split('(')[0]) if 'Temperature' in data else 0,
        'ip': data['ONT IP 0 address/mask'].split('/')[0] if 'ONT IP 0 address/mask' in data else None,
        'last_down_cause': data.get('Last down cause'),
        'last_down': data['Last down time'].rstrip('+06:00') if 'Last down time' in data else None,
        'last_up': data['Last up time'].rstrip('+06:00') if 'Last up time' in data else None,
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
        'rx': float(data['Rx optical power(dBm)']),
        'tx': float(data['Tx optical power(dBm)']),
        'temp': int(data['Temperature(C)']) if 'Temperature(C)' in data else None
    }

def parse_catv_status(output) -> bool:
    output = [line.strip() for line in output.splitlines()]
    line = output[output.index('port-ID  port-type  switch') + 2]
    data = line.replace('  ', ' ').replace('  ', ' ').replace('  ', ' ').replace('  ', ' ').split(' ')
    return data[3] == 'on'

def ping(ip: None | str) -> None | str:
    if not ip or ip in ['-', 'N/A', '']:
        return None

    try:
        result = run(['ping', '-c', '1', '-W', '300', ip], capture_output=True,
            text=True, timeout=1.5)

        if result.returncode == 0:
            time_match = search(r'time=([0-9.]+)', result.stdout)
            return f"{time_match.group(1)} ms" if time_match else "OK"
        return None
    except:
        return None