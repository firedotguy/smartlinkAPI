from html import unescape
from ipaddress import IPv4Address
from json import loads
from json.decoder import JSONDecodeError

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from api import api_call
from utils import list_to_str, to_2gis_link, to_neo_link, normalize_items, extract_sn, remove_sn,\
    parse_agreement, status_to_str, format_mac

router = APIRouter(prefix='/customer')
PHONE_LENGTH = 9

@router.get('/search')
def api_get_customer_search(query: str):
    customer = {}
    customers = []
    search_type = 'default'

    if query.isdigit() and len(query) >= PHONE_LENGTH:
        customer = api_call('customer', 'get_customer_id', f'data_typer=phone&data_value={query}')
        search_type ='phone'
    elif query.isdigit():
        customer = api_call('customer', 'get_customer_id', f'data_typer=agreement_number&data_value={query}')
        search_type = 'agreement'
    else:
        customers = list(map(str, api_call('customer', 'get_customers_id', f'name={query}&is_like=1&limit=10')['data']))
        search_type = 'name'

    if 'Id' in customer:
        customers = [str(customer['Id'])]

    if customers:
        customers = [
            {
                'id': customer['id'],
                'name': remove_sn(customer['full_name']),
                'agreement': parse_agreement(customer['agreement'][0]['number']),
                'status': status_to_str(customer['state_id'])
            }
            for customer in normalize_items(api_call('customer', 'get_data', f'id={list_to_str(customers)}'))
        ]
        return {
            'status': 'success',
            'customers': customers,
            'search_type': search_type
        }

    return JSONResponse({
        'status': 'fail',
        'detail': 'not found',
        'search_type': search_type
    }, 404)


def _process_customer(request_tariffs: list, request_groups: list, customer: dict):
    tariffs = [
        {'id': int(tariff['id']), 'name': request_tariffs[tariff['id']]}
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


    olt = api_call('commutation', 'get_data', f'object_type=customer&object_id={customer["id"]}&is_finish_data=1')['data']

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

    return {
        # main data
        'id': customer['id'],
        'name': remove_sn(customer['full_name']),
        'agreement': parse_agreement(customer['agreement'][0]['number']),
        'status': status_to_str(customer['state_id']),
        'group': {
            'id': list(customer['group'].values())[0]['id'],
            'name': request_groups[list(customer['group'].values())[0]['id']]
        } if 'group' in customer else None,
        'phones': [phone['number'] for phone in customer['phone'] if phone['number']],
        'tariffs': tariffs,
        'manager_id': customer.get('manager_id'),

        'is_corporate': bool(customer.get('flag_corporate', False)),
        'is_disabled': bool(customer.get('is_disable', False)),
        'is_potential': bool(customer.get('is_potential', False)),

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


@router.get('/{id}')
def api_get_customer(request: Request, id: int):
    customer = api_call('customer', 'get_data', f'id={id}').get('data')
    if customer is None:
        return JSONResponse({'status': 'fail', 'detail': 'customer not found'}, 404)

    return {
        'status': 'success',
        'data': _process_customer(request.app.state.tariffs, request.app.state.customer_groups, customer)
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


@router.get('')
def api_get_customers(
    request: Request,
    ids: str | None = None,
    get_data: bool = True,
    limit: int | None = None,
    skip: int | None = None
):
    customers = []
    if ids is not None:
        try:
            customers: list[int] = loads(ids)
            if not (isinstance(customers, list) and all(isinstance(customer, int) for customer in customers)):
                return JSONResponse({'status': 'fail', 'detail': 'incorrect type of ids param'}, 422)
        except JSONDecodeError:
            return JSONResponse({'status': 'fail', 'detail': 'unable to parse ids param'}, 422)
    else:
        return JSONResponse({'status': 'fail', 'detail': 'no filters provided'}, 422)

    count = len(customers)
    if skip:
        customers = customers[skip:]
    if limit:
        customers = customers[:limit]

    customers_data = []
    if get_data:
        for customer_id in customers:
            customer = api_call('customer', 'get_data', f'id={customer_id}').get('data')
            if customer is None:
                return JSONResponse({'status': 'fail', 'detail': f'customer {customer_id} not found'}, 404)

            customers_data.append(_process_customer(request.app.state.tariffs, request.app.state.customer_groups, customer))

    return {
        'status': 'success',
        'data': customers_data or customers,
        'count': count # total count without limit/skip
    }