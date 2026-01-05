from json import loads
from json.decoder import JSONDecodeError

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.requests import Request

from api import api_call
from routers.customer import _process_customer
from utils import normalize_items, list_to_str, str_to_list, get_coordinates, get_box_map_link

router = APIRouter(prefix='/box')

@router.get('/{id}')
def api_get_box(
    request: Request,
    id: int,
    get_olt_data: bool = False,
    get_tasks: bool = False,
    limit: int | None = None,
    exclude_customer_ids: str = '[]'
):
    def _get_tasks(entity: str, entity_id: int) -> list[int]:
        res = api_call('task', 'get_list', f'{entity}_id={entity_id}&state_id=18,3,17,11,1,16,19')
        return list(map(int, str_to_list(res.get('list', ''))))

    def _build_customer(customer: dict) -> dict | None:
        name = customer.get('full_name')
        if name is None:
            return None
        return _process_customer(request.app.state.tariffs, request.app.state.customer_groups, customer, get_olt_data)
        # {
        #     'id': customer['id'],
        #     'name': remove_sn(name),
        #     'last_activity': customer.get('date_activity'),
        #     'status': status_to_str(customer['state_id']),
        #     'sn': extract_sn(name),
        #     'onu_level': _get_onu_level(name) if get_onu_level else None,
        #     'tasks': _get_tasks('customer', customer['id']) if get_tasks else None
        # }

    exclude_ids = []
    if exclude_customer_ids:
        try:
            exclude_ids: list[int] = loads(exclude_customer_ids)
            if not (isinstance(exclude_ids, list) and all(isinstance(customer, int) for customer in exclude_ids)):
                return JSONResponse({'status': 'fail', 'detail': 'incorrect type of exclude_customer_ids param'}, 422)
        except JSONDecodeError:
            return JSONResponse({'status': 'fail', 'detail': 'unable to parse exclude_customer_ids param'}, 422)

    house_data = api_call('address', 'get_house', f'building_id={id}').get('data')
    if not house_data:
        return JSONResponse({'status': 'fail', 'detail': 'box not found'}, 404)

    house = list(house_data.values())[0]
    customer_ids: list = api_call('customer', 'get_customers_id', f'house_id={id}').get('data', [])
    for customer in exclude_ids:
        if customer in customer_ids:
            customer_ids.remove(customer)
    customers_count = len(customer_ids)

    customers = []
    fetch_customer_ids = []
    if customer_ids:
        fetch_customer_ids = customer_ids
        if limit:
            fetch_customer_ids = customer_ids[:limit]

        raw_customers = normalize_items(
            api_call('customer', 'get_data', f'id={list_to_str(fetch_customer_ids)}')
        )
        customers = [c for c in map(_build_customer, raw_customers) if c is not None]

    onu_levels = [c['onu_level'] for c in customers if c['onu_level']]
    avg_onu_level = sum(onu_levels) / len(onu_levels) if onu_levels else None

    coords = get_coordinates(house.get('coordinates'))
    map_link = get_box_map_link(coords, id)

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
        'map_link': map_link,
        'customers': customers,
        'remaining_customer_ids': [customer_id for customer_id in customer_ids if customer_id not in fetch_customer_ids], # all ids exclude fetched
        'customers_count': customers_count
    }
