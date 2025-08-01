from requests import get
from functions import *
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from config import api_url as api

disable_warnings(InsecureRequestWarning)

def find_names(name: str):
    names = get(f'{api}customer&action=get_customers_id&name={name}&is_like=1&limit=10', verify=False).json()
    if 'data' in names.keys():
        return list(map(str, names['data']))
    return []

def find_agreement(ls: str):
    names = get(f'{api}customer&action=get_customer_id&data_typer=agreement_number&data_value={ls}', verify=False).json()
    if names['result'] == 'ERROR':
        return []
    return [str(names['Id'])]

def get_usersdata(ids: list):
    users = get(f'{api}customer&action=get_data&id={','.join(ids)}', verify=False).json()
    if 'data' not in users:
        return []
    users = users['data']
    data = []
    if list(users.keys())[0].isdigit():
        for user in users.values():
            data.append(user)
    else:
        data = [users]
    return data

def get_userdata(id: int):
    return get(f'{api}customer&action=get_data&id={id}', verify=False).json()['data']

def get_inventory(id: int):
    inventory = get(f'{api}inventory&action=get_inventory_amount&location=customer&object_id={id}', verify=False).json()['data']
    if inventory != []:
        return list(inventory.values())
    return []

def get_inventory_data(ids: list):
    inventory = get(f'{api}inventory&action=get_inventory_catalog&location=customer&id={','.join([str(i['inventory_type_id']) for i in ids])}', verify=False).json()['data']
    return [{'id': str(i['id']), 'name': convert(i['name']), 'catalog': i['inventory_section_catalog_id']} for i in inventory.values()]

def get_tariffs():
    data = get(f'{api}tariff&action=get', verify=False).json()['data']
    tariffs = {}
    for tariff in data.values():
        tariffs[tariff['billing_uuid']] = convert(tariff['name'])
    return tariffs

def get_house(id: int):
    data = get(f'{api}address&action=get_house&building_id={id}', verify=False).json()['data']
    return list(data.values())[0]

def get_neighbours(house_id: int):
    return get(f'{api}customer&action=get_customers_id&house_id={house_id}', verify=False).json()['data']

def get_customer_groups():
    data = get(f'{api}customer&action=get_customer_group', verify=False).json()['data']
    groups = {}
    for group in data.values():
        groups[group['id']] = group['name']
    return groups

def check_login(login, password):
    return 'result' in get(f'{api}employee&action=check_pass&login={login}&pass={password}', verify=False).json()

def get_ont_data(sn):
    if not sn:
        return None
    res = get(f'{api}device&action=get_ont_data&id={sn}', verify=False).json()['data']
    if res:
        return res['level_onu_rx']
    return None

def get_customer_attachs(id):
    return get(f'{api}attach&action=get&object_id={id}&object_type=customer', verify=False).json()['data']

def get_task_attachs(id):
    return get(f'{api}attach&action=get&object_id={id}&object_type=task', verify=False).json()['data']

def get_attach_data(id):
    return get(f'{api}attach&action=get_file_temporary_link&uuid={id}', verify=False).json()['data']

def get_customer_tasks(id):
    return get(f'{api}task&action=get_list&customer_id={id}', verify=False).json()['list'].split(',')