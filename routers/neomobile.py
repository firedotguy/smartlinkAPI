from html import unescape

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from api import api_call, set_additional_data
from utils import remove_sn, get_current_time, status_to_str

router = APIRouter(prefix='/neomobile')


@router.get('/login')
def neomobile_api_get_login(request: Request, phone: str, agreement: str):
    id = api_call('customer', 'get_customer_id',
        f'data_typer=agreement_number&data_value={agreement}')
    if 'Id' not in id:
        return JSONResponse({'status': 'fail', 'detail': 'customer not found'}, 404)
    data = api_call('customer', 'get_data', f'id={id["Id"]}')
    if 'data' not in data:
        return JSONResponse({'status': 'fail', 'detail': 'customer not exists'}, 404)
    data = data['data']
    if len(data['phone']) > 0:
        if data['phone'][0]['number'] != phone:
            return JSONResponse({'status': 'fail', 'detail': 'invalid phone number'}, 404)

    tariff_data = []
    for tariff in data['tariff']['current']:
        if tariff['id']:
            tariff_data.append({
                'id': int(tariff['id']),
                'name': request.app.state.tariffs[tariff['id']]
            })
    return {
        'status': 'success',
        'id': id['Id'],
        'name': remove_sn(data['full_name']),
        'phone': phone,
        'agreement': agreement,
        'balance': data['balance'],
        'last_activity': data['date_activity'],
        'tariffs': tariff_data
    }

@router.get('/customer')
def neomobile_api_get_customer(request: Request, id: int):
    data = api_call('customer', 'get_data', f'id={id}')
    if 'data' not in data:
        return JSONResponse({'status': 'fail', 'detail': 'customer not found'}, 404)
    data = data['data']

    tariff_data = []
    for tariff in data['tariff']['current']:
        if tariff['id']:
            tariff_data.append({
                'id': int(tariff['id']),
                'name': request.app.state.tariffs[tariff['id']]
            })

    tasks = api_call('task', 'get_list',
        f'customer_id={id}&type_id=37&state_id=18,3,15,17,11,1,10,16,19')['list'].split(',')
    if tasks == ['']: tasks.clear()
    return {
        # 'status': 'success',
        'id': data['id'],
        'name': remove_sn(data['full_name']),
        'phones': [phone['number'] for phone in data['phone']],
        'agreement': data['agreement'][0]['number'],
        'balance': data['balance'],
        'last_activity': data['date_activity'],
        'connected_at': data['date_connect'],
        'created_at': data['date_create'],
        'tariffs': tariff_data,
        'status': status_to_str(data['state_id']),
        'task': None if len(tasks) == 0 else int(tasks[0])
    }


@router.post('/task')
def neomobile_api_post_task(customer_id: int, phone: str, reason: str, comment: str):
    id = api_call('task', 'add',
        f'work_typer=37&work_datedo={get_current_time()}&customer_id={customer_id}&author_employee_id=184&'
        f'opis={comment}&deadline_hour=72&employee_id=184&division_id=81'
    )['Id']
    set_additional_data(17, 28, id, 'Приложение') #TODO: make own appeal type
    set_additional_data(17, 29, id, phone)
    set_additional_data(17, 30, id, reason)
    api_call('task', 'comment_add', f'id={id}&comment={comment}&employee_id=184')

    return {
        'status': 'success',
        'id': id,
        'customer_id': customer_id,
        'phone': phone,
        'reason': reason,
        'comment': comment
    }

@router.post('/task/cancel')
def neomobile_api_post_task_cancel(id: int):
    api_call('task', 'change_state', f'id={id}&state_id=10')
    return {
        'status': 'success',
        'id': id
    }

@router.get('/task')
def neomobile_api_get_task(id: int):
    data = api_call('task', 'show', f'id={id}')
    if 'data' not in data:
        return JSONResponse({'status': 'fail', 'detail': 'task not found'}, 404)
    comments = api_call('task', 'get_comment', f'task_id={id}')['data']
    data = data['data']
    return {
        'status': 'success',
        'id': id,
        'type': data['type'],
        'created_at': data['date']['create'],
        'completed_at': data['date']['complete'] if 'complete' in data['date'] else None,
        'status': {'id': data['state']['id'], 'name': data['state']['name']},
        'address': {'id': data['address']['addressId'], 'text': data['address']['text']},
        'customer': data['customer'][0],
        'reason': data['additional_data']['30']['value'] if '30' in data['additional_data'] else None,
        'phone': data['additional_data']['29']['value'] if '29' in data['additional_data'] else None,
        'comments': [{
            'id': comment['comment_id'],
            'content': comment['text'],
            'author_id': comment['employee_id'],
            'created_at': comment['date_add']
        } for comment in comments]
    }

@router.post('/task/comment')
def neomobile_api_get_task_comment(id: int, content: str):
    data = api_call('task', 'comment_add', f'id={id}&comment={content}&employee_id=184')
    return {
        'status': 'success',
        'id': data['Id'],
        'task_id': id,
        'content': content
    }

@router.get('/inventory')
def neomobile_api_get_inventory(request: Request, id: int):
    data = api_call('inventory', 'get_inventory_amount',
        f'location=customer&object_id={id}')['data'].values()
    names = api_call('inventory', 'get_inventory_catalog',
        f"id={','.join([str(i['inventory_type_id']) for i in data])}")['data'].values()
    return {
        'status': 'success',
        'id': id,
        'data': [
            {
                'id': inventory['id'],
                'name': unescape([name for name in names if name['id'] == inventory['catalog_id']][0]['name']),
                'type': {
                    'id': [name for name in names if name['id'] == inventory['catalog_id']][0]['inventory_section_catalog_id'],
                    'name': [
                        category['name'] for category in request.app.state.tmc_categories
                        if category['id'] == [
                            name for name in names
                            if name['id'] == inventory['catalog_id']
                        ][0]['inventory_section_catalog_id']
                    ][0]
                },
                'category_id': inventory['catalog_id'],
                'amount': inventory['amount'],
                'sn': inventory['serial_number']
            } for inventory in data
        ]
    }

@router.get('/documents')
def neomobile_api_get_documents(id: int):
    attachs = list(api_call('attach', 'get', f'object_id={id}&object_type=customer')['data'].values())
    tasks = api_call('task', 'get_list', f'customer_id={id}')['list'].split(',')
    for task in tasks:
        try:
            attachs.extend(api_call('attach', 'get', f'object_id={task}&object_type=task')['data'].values())
        except AttributeError:
            continue
    return {
        'status': 'success',
        'id': id,
        'task_ids': [int(task) for task in tasks],
        'attachs': [
            {
                'id': attach['id'],
                'url': api_call('attach', 'get_file_temporary_link', f'uuid={attach["id"]}')['data'],
                'name': attach['internal_filepath'] if '.' in attach['internal_filepath'] else attach['internal_filepath'] + '.png',
                'extension': attach['internal_filepath'].split('.')[1].lower() if '.' in attach['internal_filepath'] else 'png',
                'created_at': attach['date_add']
            } for attach in attachs
        ]
    }
