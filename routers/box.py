from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api import api_call
from utils import extract_sn, normalize_items, remove_sn, status_to_str, list_to_str, str_to_list, get_coordinates, get_box_map_link

router = APIRouter(prefix='/box')

@router.get('/{id}')
def api_get_box(id: int, get_onu_level: bool = False, get_tasks: bool = False):
    def _get_onu_level(name) -> float | None:
        if extract_sn(name) is None: return
        res = api_call('device', 'get_ont_data', f'id={extract_sn(name)}')
        if not isinstance(res.get('data'), dict): return
        return res['data'].get('level_onu_rx')

    house = api_call('address', 'get_house', f'building_id={id}').get('data')
    if house:
        house = list(house.values())[0]
        customers_id = api_call('customer', 'get_customers_id', f'house_id={id}')['data']
        customers = [{
            'id': customer['id'],
            'name': remove_sn(customer['full_name']),
            'last_activity': customer.get('date_activity'),
            'status': status_to_str(customer['state_id']),
            'sn': extract_sn(customer['full_name']),
            'onu_level': _get_onu_level(customer['full_name']) if get_onu_level else None,
            'tasks': list(map(int, str_to_list(
                api_call('task', 'get_list', f'customer_id={customer["id"]}&state_id=18,3,17,11,1,16,19')['list']
            ))) if get_tasks else None
        } for customer in normalize_items(api_call('customer', 'get_data',
            f'id={list_to_str(customers_id)}')) if customer['full_name'] is not None]

        onu_levels = [
            customer['onu_level']
            for customer in customers
            if customer['onu_level']
        ]

        return {
            'status': 'success',
            'id': id,
            'address_id': house['id'],
            'name': house['full_name'],
            'average_onu_level': sum(onu_levels) / len(onu_levels) if onu_levels else None,
            'tasks': list(map(int, str_to_list(
                api_call('task', 'get_list', f'house_id={id}&state_id=18,3,17,11,1,16,19')['list']
            ))) if get_tasks else None,
            'manager_id': house.get('manage_employee_id'),
            'coords': get_coordinates(house['coordinates']),
            'active': not house.get('is_not_use', True),
            'map_link': get_box_map_link(get_coordinates(house['coordinates']), id),
            'customers': customers
        }
    return JSONResponse({
        'status': 'fail',
        'detail': 'box not found'
    }, 404)
