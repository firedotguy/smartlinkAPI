from html import unescape

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api import api_call
from utils import normalize_items, list_to_str

router = APIRouter(prefix='/inventory')


@router.get('')
def api_get_inventory(
    customer_id: int | None = None,
    get_names: bool = True
):
    items = []
    if customer_id is not None:
        items = normalize_items(api_call('inventory', 'get_inventory_amount', f'location=customer&object_id={customer_id}'))
    else:
        return JSONResponse({'status': 'fail', 'detail': 'no filter provided'}, 422)

    named_items = []
    if get_names:
        names = api_call('inventory', 'get_inventory_catalog', f'id={list_to_str([str(item['inventory_type_id']) for item in items])}')['data'].values()

        for item in items:
            name = [name for name in names if name['id'] == item['inventory_type_id']][0]
            print(name)
            print(item)
            named_items.append({
                'id': item['id'],
                'type_id': item['inventory_type_id'], # mean model (e.g VSOLVA74) # equals item['catalog_id']
                'name': unescape(name['name']),
                'amount': item['amount'],
                'category_id': name['inventory_section_catalog_id'], # mean category (e.g modem, cable, patchcord)
                'sn': item['serial_number'],
                'location': item['location_type'],
                'location_id': item['object_id']
            })
    else:
        items = [
            {
                'id': item['id'],
                'type_id': item['inventory_type_id'],
                'amount': item['amount'],
                'sn': item['serial_number'],
                'location': item['location_type'],
                'location_id': item['object_id']
            } for item in items
        ]

    return {
        'status': 'success',
        'data': named_items or items
    }