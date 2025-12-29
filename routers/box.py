from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api import api_call
from utils import extract_sn, normalize_items, remove_sn, status_to_str, list_to_str, str_to_list, get_coordinates, get_box_map_link

router = APIRouter(prefix='/box')

@router.get('/{id}')
def api_get_box(
    id: int,
    get_onu_level: bool = False,
    get_tasks: bool = False,
    limit: int | None = None,
    skip: int | None = None
):
    def _get_onu_level(name) -> float | None:
        if extract_sn(name) is None:
            return
        data = api_call('device', 'get_ont_data', f'id={extract_sn(name)}').get('data')
        if not isinstance(data, dict):
            return
        return data.get('level_onu_rx')

    def _get_tasks(entity: str, entity_id: int) -> list[int]:
        res = api_call('task', 'get_list', f'{entity}_id={entity_id}&state_id=18,3,17,11,1,16,19')
        return list(map(int, str_to_list(res.get('list', ''))))

    def _build_customer(customer: dict) -> dict | None:
        name = customer.get('full_name')
        if name is None:
            return None
        return {
            'id': customer['id'],
            'name': remove_sn(name),
            'last_activity': customer.get('date_activity'),
            'status': status_to_str(customer['state_id']),
            'sn': extract_sn(name),
            'onu_level': _get_onu_level(name) if get_onu_level else None,
            'tasks': _get_tasks('customer', customer['id']) if get_tasks else None
        }

    house_data = api_call('address', 'get_house', f'building_id={id}').get('data')
    if not house_data:
        return JSONResponse({'status': 'fail', 'detail': 'box not found'}, 404)

    house = list(house_data.values())[0]
    customer_ids = api_call('customer', 'get_customers_id', f'house_id={id}').get('data', [])
    customers_count = len(customer_ids)

    customers = []
    if customer_ids:
        if skip:
            customer_ids = customer_ids[skip:]
        if limit:
            customer_ids = customer_ids[:limit]
        raw_customers = normalize_items(
            api_call('customer', 'get_data', f'id={list_to_str(customer_ids)}')
        )
        customers = [c for c in map(_build_customer, raw_customers) if c is not None]

    onu_levels = [c['onu_level'] for c in customers if c['onu_level']]
    avg_onu_level = sum(onu_levels) / len(onu_levels) if onu_levels else None

    coords = get_coordinates(house['coordinates']) if house.get('coordinates') else None

    return {
        'status': 'success',
        'id': id,
        'address_id': house['id'],
        'name': house['full_name'],
        'average_onu_level': avg_onu_level,
        'tasks': _get_tasks('house', id) if get_tasks else None,
        'manager_id': house.get('manage_employee_id'),
        'coords': coords,
        'active': not house.get('is_not_use', True),
        'map_link': get_box_map_link(coords, id) if coords else None,
        'customers': customers,
        'customers_count': customers_count,
        'customers_limit': customers_count > limit + (skip or 0) if limit else False
    }
