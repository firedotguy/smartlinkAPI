from html import unescape

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from api import api_call
from utils import list_to_str, to_2gis_link, to_neo_link, normalize_items, extract_sn, remove_sn,\
    parse_agreement, status_to_str

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
        'result': 'OK',
        'customers': customer_data,
        'search_type': 'agreement' if query.isdigit() else 'name'
    }


# TODO: divide api calls
@router.get('/{id}')
def api_get_customer(request: Request, id: int):
    customer = api_call('customer', 'get_data', f'id={id}')['data']
    if customer is None: return JSONResponse({'status': 'fail', 'detail': 'customer not found'},
        404)

    tariffs = [
        {'id': int(tariff['id']), 'name': request.app.state.tariffs[tariff['id']]}
        for tariff in customer['tariff']['current']
    ]

    geodata = {}
    if 'additional_data' in customer:
        if '7' in customer['additional_data']:
            geodata['coord'] = list(map(float, customer['additional_data']['7']['value']
                .split(',')))
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
    if 'finish' not in olt or olt['finish'].get('object_type') != 'switch' \
        and extract_sn(customer['full_name']) is not None:
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
    items = api_call('inventory', 'get_inventory_amount', f'location=customer&object_id={id}')\
        .get('data', []).values()
    item_names = [
        {
            'id': str(item['id']),
            'name': unescape(item['name']),
            'catalog': item['inventory_section_catalog_id']
        }
        for item in api_call('inventory', 'get_inventory_catalog',
            f'id={list_to_str([str(i['inventory_type_id']) for i in items])}')['data'].values()
    ]
    inventory = []
    for item in items:
        item_name = item_names[item_names.index([
            i for i in item_names if i['id'] == str(item['inventory_type_id'])
        ][0])]
        inventory.append({
            'id': item['id'],
            'catalog_id': item['inventory_type_id'],
            'name': item_name['name'],
            'amount': item['amount'],
            'category_id': item_name['catalog'],
            'sn': item['serial_number']
        })


    # TASK
    tasks_id = api_call('task', 'get_list', f'customer_id={id}')['list'].split(',')
    if tasks_id:
        tasks_data = normalize_items(api_call('task', 'show', f'id={list_to_str(tasks_id)}'))
        tasks = []
        for task in tasks_data:
            dates = {}
            if 'create' in task['date']:
                dates['create'] = task['date']['create']
            if 'update' in task['date']:
                dates['update'] = task['date']['update']
            if 'complete' in task['date']:
                dates['complete'] = task['date']['complete']
            if task['type']['name'] != 'Обращение абонента' and \
                task['type']['name'] != 'Регистрация звонка':
                tasks.append({
                    'id': task['id'],
                    'customer_id': task['customer'][0],
                    'employee_id': list(task['staff']['employee'].values())[0]
                        if 'staff' in task and 'employee' in task['staff'] else None,
                    'name': task['type']['name'],
                    'status': {
                        'id': task['state']['id'],
                        'name': task['state']['name'],
                        'system_id': task['state']['system_role']
                    },
                    'address': task['address']['text'],
                    'dates': dates
                })
    else:
        tasks = []

    return {
        'result': 'OK',
        'id': customer['id'],
        'olt_id': olt_id,
        'balance': customer['balance'],
        'name': remove_sn(customer['full_name']),
        'agreement': parse_agreement(customer['agreement'][0]['number']),
        'status': status_to_str(customer['state_id']),
        'sn': extract_sn(customer['full_name']),
        'tasks': tasks,
        # 'onu_level': get_ont_data(extract_sn(customer['full_name'])),
        'tariffs': tariffs,
        'phones': [phone['number'] for phone in customer['phone']],
        'last_activity': customer['date_activity'],
        'inventory': inventory,
        'box_id': customer['address'][0]['house_id'],
        'geodata': geodata,
        'group': {
            'id': list(customer['group'].values())[0]['id'],
            'name': request.app.state.customer_groups[list(customer['group'].values())[0]['id']]
        } if 'group' in customer else None
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
