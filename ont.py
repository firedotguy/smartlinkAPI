from time import sleep, time
from select import select
from subprocess import run
from re import search, sub, IGNORECASE

from paramiko import SSHClient, AutoAddPolicy, Channel
from config import ssh_user, ssh_password

__version__ = 'v.13.0'

def search_ont(sn: str, host: str) -> None | dict[str, str]:
    start_time = time()

    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(host, username=ssh_user, password=ssh_password, timeout=5, auth_timeout=5,
        banner_timeout=2, look_for_keys=False, allow_agent=False)

    channel = ssh.invoke_shell()
    sleep(0.3)
    clear_buffer(channel)
    channel.send(bytes("enable\n", 'utf-8'))
    sleep(0.2)
    clear_buffer(channel)

    channel.send(bytes(f"display ont info by-sn {sn}\n", 'utf-8'))
    sleep(1.8)

    ont_info = parse_basic_info(read_output(channel), sn)

    if not ont_info:
        return None

    channel.send(bytes("config\n", 'utf-8'))
    sleep(0.15)
    clear_buffer(channel)

    interface_parts = ont_info['interface'].split('/')
    gpon_interface = f"{interface_parts[0]}/{interface_parts[1]}"
    port_id = interface_parts[2]

    channel.send(bytes(f"interface gpon {gpon_interface}\n", 'utf-8'))
    sleep(0.15)
    clear_buffer(channel)


    channel.send(bytes(f"display ont optical-info {port_id} {ont_info['ont_id']}\n", 'utf-8'))
    sleep(1.2)
    optical_output = read_output(channel)
    optical_info = parse_optical_info(optical_output)

    if optical_info:
        ont_info.update(optical_info)

    catv_results = []
    for port_num in [1, 2]:
        channel.send(bytes(f"display ont port attribute {port_id} {ont_info['ont_id']} catv {port_num}\n", 'utf-8'))
        sleep(1.3)
        catv_output = read_output(channel)
        catv_status = parse_catv_status(catv_output, port_num)

        if catv_status:
            catv_results.append(catv_status)

    if catv_results:
        ont_info['catv_ports'] = catv_results

    channel.close()
    ssh.close()

    ip = ont_info.get('ip', '').split('/')[0] if ont_info.get('ip') else None
    ping_result = ping_fast(ip)

    ont_info['ping'] = ping_result
    ont_info['duration'] = time() - start_time
    return ont_info

def clear_buffer(channel: Channel):
    if channel.recv_ready():
        channel.recv(32768)

def read_output(channel: Channel, timeout: int = 30):
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
        if end_time < time():
            break

    return output

def parse_basic_info(output: str, sn: str) -> dict | None:
    info = {'sn': sn}
    clean_output = sub(r'\x1b\[[0-9;]*[A-Za-z]|\r', '', output)

    patterns = {
        'interface': r'F/S/P\s*:\s*([^\n]+)',
        'ont_id': r'ONT-ID\s*:\s*([^\n]+)',
        'status': r'Run\s+state\s*:\s*([^\n]+)',
        'online_duration': r'ONT\s+online\s+duration\s*:\s*([^\n]+)',
        'ip': r'ont\s+ip.*?:\s*([0-9./]+)'
    }

    for key, pattern in patterns.items():
        match = search(pattern, clean_output, IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value not in ['-', '']:
                if key == 'ip' and search(r'\d+\.\d+\.\d+\.\d+', value):
                    info[key] = value
                elif key != 'ip':
                    info[key] = value
    return info if 'ont_id' in info else None

def parse_optical_info(output) -> dict:
    optical = {}
    clean_output = sub(r'\x1b\[[0-9;]*[A-Za-z]|\r', '', output)

    patterns = {
        'rx_power': r'Rx\s+optical\s+power\(dBm\)\s*:\s*([^\n]+)',
        'olt_rx_power': r'OLT\s+Rx\s+ONT\s+optical\s+power\(dBm\)\s*:\s*([^\n]+)',
        'temperature': r'Temperature\(C\)\s*:\s*([^\n]+)',
        'voltage': r'Voltage\(V\)\s*:\s*([^\n]+)'
    }

    for key, pattern in patterns.items():
        match = search(pattern, clean_output, IGNORECASE)
        if match and match.group(1).strip() not in ['-', '']:
            optical[key] = match.group(1).strip()

    return optical

def parse_catv_status(output, port_num) -> dict | None:
    clean_output = sub(r'\x1b\[[0-9;]*[A-Za-z]|\r', '', output)

    lines = clean_output.split('\n')
    for line in lines:
        if 'CATV' in line and ('on' in line or 'off' in line):
            parts = line.split()
            if len(parts) >= 4:
                for i, part in enumerate(parts):
                    if part.upper() == 'CATV' and i + 1 < len(parts):
                        switch = parts[i + 1]
                        frequency = parts[i + 2] if i + 2 < len(parts) else 'all-pass'
                        return {
                            'port': port_num,
                            'switch': switch,
                            'frequency': frequency
                        }
    return None

def ping_fast(ip: None | str) -> None | str:
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