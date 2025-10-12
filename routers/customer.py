from html import unescape
from ipaddress import IPv4Address

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from api import api_call
from utils import list_to_str, to_2gis_link, to_neo_link, normalize_items, extract_sn, remove_sn,\
    parse_agreement, status_to_str, format_mac

router = APIRouter(prefix='/customer')

@router.get('/search')
def api_get_customer_search(query: str):
    customers = []
    if query.isdigit():
        customer = api_call('customer', 'get_customer_id',
            f'data_typer=agreement_number&data_value={query}')
        if 'Id' in customer:
            customers = [str(customer['Id'])]
    else:
        customers = list(map(str, api_call('customer', 'get_customers_id',
            f'name={query}&is_like=1&limit=10')['data']))

    customer_data = []
    if len(customers) > 0:
        customer_data = [{
            'id': customer['id'],
            'name': remove_sn(customer['full_name']),
            'agreement': parse_agreement(customer['agreement'][0]['number']),
            'status': status_to_str(customer['state_id'])
        } for customer in normalize_items(api_call('customer', 'get_data',
            f'id={list_to_str(customers)}'))]

    return {
        'status': 'success',
        'customers': customer_data,
        'search_type': 'agreement' if query.isdigit() else 'name'
    }


# TODO: divide api calls
@router.get('/{id}')
def api_get_customer(request: Request, id: int):
    customer = api_call('customer', 'get_data', f'id={id}').get('data')
    if customer is None:
        return JSONResponse({'status': 'fail', 'detail': 'customer not found'}, 404)

    tariffs = [
        {'id': int(tariff['id']), 'name': request.app.state.tariffs[tariff['id']]}
        for tariff in customer['tariff']['current'] if tariff['id']
    ]

    geodata = {}
    if 'additional_data' in customer:
        if '7' in customer['additional_data']:
            geodata['coord'] = list(map(float, customer['additional_data']['7']['value'].split(',')))
        if '42' in customer['additional_data']:
            geodata['address'] = unescape(customer['additional_data']['42']['value'])
        if '6' in customer['additional_data']:
            geodata['2gis_link'] = unescape(customer['additional_data']['6']['value'])

    if 'coord' in geodata:
        geodata['neo_link'] = to_neo_link(geodata['coord'][0], geodata['coord'][1])
        if '2gis_link' in geodata:
            geodata['2gis_link'] = to_2gis_link(geodata['coord'][0], geodata['coord'][1])


    olt = api_call('commutation', 'get_data',
        f'object_type=customer&object_id={id}&is_finish_data=1')['data']

    if 'finish' not in olt or olt['finish'].get('object_type') != 'switch' and extract_sn(customer['full_name']) is not None:
        ont = api_call('device', 'get_ont_data', f'id={extract_sn(customer["full_name"])}')['data']
        if isinstance(ont, dict):
            olt_id = ont.get('device_id')
        else:
            olt_id = None
    elif extract_sn(customer['full_name']) is None:
        olt_id = None
    else:
        olt_id = olt['finish']['object_id']


    # INVENTORY
    # items = api_call('inventory', 'get_inventory_amount', f'location=customer&object_id={id}')\
    #     .get('data', {})
    # if isinstance(items, dict):
    #     items = items.values()

    # item_names = [
    #     {
    #         'id': str(item['id']),
    #         'name': unescape(item['name']),
    #         'catalog': item['inventory_section_catalog_id']
    #     }
    #     for item in api_call('inventory', 'get_inventory_catalog',
    #         f'id={list_to_str([str(i["inventory_type_id"]) for i in items])}')['data'].values()
    # ]
    # inventory = []
    # for item in items:
    #     item_name = [i for i in item_names if i['id'] == str(item['inventory_type_id'])][0]
    #     inventory.append({
    #         'id': item['id'],
    #         'catalog_id': item['inventory_type_id'],
    #         'name': item_name['name'],
    #         'amount': item['amount'],
    #         'category_id': item_name['catalog'],
    #         'sn': item['serial_number']
    #     })


    # TASK
    # tasks_id = str_to_list(api_call('task', 'get_list', f'customer_id={id}')['list'])
    # if tasks_id:
    #     tasks_data = normalize_items(api_call('task', 'show', f'id={list_to_str(tasks_id)}'))
    #     tasks = []
    #     for task in tasks_data:
    #         dates = {}
    #         if 'create' in task['date']:
    #             dates['create'] = task['date']['create']
    #         if 'update' in task['date']:
    #             dates['update'] = task['date']['update']
    #         if 'complete' in task['date']:
    #             dates['complete'] = task['date']['complete']
    #         if task['type']['name'] != 'Обращение абонента' and \
    #             task['type']['name'] != 'Регистрация звонка':
    #             tasks.append({
    #                 'id': task['id'],
    #                 'customer_id': task['customer'][0],
    #                 'employee_id': list(task['staff']['employee'].values())[0]
    #                     if 'staff' in task and 'employee' in task['staff'] else None,
    #                 'name': task['type']['name'],
    #                 'status': {
    #                     'id': task['state']['id'],
    #                     'name': task['state']['name'],
    #                     'system_id': task['state']['system_role']
    #                 },
    #                 'address': task['address']['text'],
    #                 'dates': dates
    #             })
    # else:
    #     tasks = []
    return {
        'status': 'success',
        'data': {
            # main data
            'id': customer['id'],
            'name': remove_sn(customer['full_name']),
            'agreement': parse_agreement(customer['agreement'][0]['number']),
            'status': status_to_str(customer['state_id']),
            'group': {
                'id': list(customer['group'].values())[0]['id'],
                'name': request.app.state.customer_groups[list(customer['group'].values())[0]['id']]
            } if 'group' in customer else None,
            'phones': [phone['number'] for phone in customer['phone'] if phone['number']],
            'tariffs': tariffs,
            'manager_id': customer.get('manager_id'),

            'is_corporate': bool(customer.get('flag_corporate', False)),
            'is_disabled': bool(customer.get('is_disable', False)),
            'is_potential': bool(customer.get('is_potential', False)),

            # 'inventory': inventory,
            # 'tasks': tasks,

            # ONT
            'olt_id': olt_id,
            'sn': extract_sn(customer['full_name']),
            'ip': str(IPv4Address(int(list(customer['ip_mac'].values())[0]['ip']))) if list(customer.get('ip_mac', {'': {}}).values())[0].get('ip') else None,
            'mac': format_mac(list(customer.get('ip_mac', {'': {}}).values())[0].get('mac')),
            # 'onu_level': get_ont_data(extract_sn(customer['full_name'])),

            # billing
            'has_billing': bool(customer.get('is_in_billing', False)),
            'billing': {
                'id': int(customer['billing_id']) if 'billing_id' in customer and customer['billing_id'] else None,
                'crc': customer.get('crc_billing')
            },
            'balance': customer['balance'],

            # geodata
            'address': {
                'house_id': customer['address'][0].get('house_id') if customer.get('address', [{}])[0].get('house_id') else None,
                'entrance': customer['address'][0].get('entrance') if customer.get('address', [{}])[0].get('entrance') else None,
                'floor': int(customer['address'][0]['floor']) if customer.get('address', [{}])[0].get('floor') else None,
                'apartment': unescape(customer['address'][0]['apartment']['number'])
                    if customer.get('address', [{}])[0].get('apartment', {}).get('number') else None
            },
            'box_id': customer['address'][0]['house_id'] if customer['address'][0]['house_id'] != 0 else None,
            'geodata': geodata,

            # timestamps
            'timestamps': {
                'created_at': customer.get('date_create'),
                'connected_at': customer.get('date_connect'),
                'positive_balance_at': customer.get('date_positive_balance'),
                'last_active_at': customer.get('date_activity'),
                'last_inet_active_at': customer.get('date_activity_inet')
            }
        }
    }



@router.get('/{id}/name')
def api_get_customer_name(id: int):
    customer = api_call('customer', 'get_data', f'id={id}')
    if 'data' not in customer:
        return JSONResponse({'status': 'fail', 'detail': 'customer not found'}, 404)
    customer = customer['data']
    return {
        'status': 'success',
        'id': id,
        'name': remove_sn(customer['full_name'])
    }
