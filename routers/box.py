from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api import api_call
from utils import extract_sn, normalize_items, remove_sn, status_to_str, list_to_str

router = APIRouter(prefix='/box')

@router.get('/{id}')
def api_get_box(id: int):
    def _get_onu_level(name):
        if extract_sn(name) is None: return
        res = api_call('device', 'get_ont_data', f'id={extract_sn(name)}')
        if not isinstance(res.get('data'), dict): return
        return res['data'].get('level_onu_rx')

    house = api_call('address', 'get_house', f'building_id={id}')['data']
    if house:
        house = list(house.values())[0]
        customers_id = api_call('customer', 'get_customers_id',
            f'house_id={house["building_id"]}')['data']
        customers = [{
            'id': customer['id'],
            'name': remove_sn(customer['full_name']),
            'last_activity': customer.get('date_activity'),
            'status': status_to_str(customer['state_id']),
            'sn': extract_sn(customer['full_name']),
            'onu_level': _get_onu_level(customer['full_name'])
        } for customer in normalize_items(api_call('customer', 'get_data',
            f'id={list_to_str(customers_id)}')) if customer['full_name'] is not None]

        return {
            'status': 'success',
            'id': id,
            'building_id': house['building_id'],
            'name': house['full_name'],
            'customers': customers
        }
    return JSONResponse({
        'status': 'fail',
        'detail': 'box not found'
    }, status_code=404)
