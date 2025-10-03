from html import unescape

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api import api_call, set_additional_data
from utils import get_current_time, str_to_list, list_to_str

router = APIRouter(prefix='/task')

@router.get('/{id}')
def api_get_task(id: int):
    task = api_call('task', 'show', f'id={id}').get('data')
    if task is None:
        return JSONResponse({'status': 'fail', 'detail': 'task not found'})
    return {
        'status': 'success',
        'data': {
            'id': id,
            'comments': [
                {
                    'id': comment['id'],
                    'created_at': comment['dateAdd'],
                    'author_id': comment['employee_id'],
                    'content': comment['comment']
                } for comment in task.get('comments', {}).values()
            ],
            'timestamps': {
                'created_at': task['date'].get('create'),
                'planned_at': task['date'].get('todo'),
                'updated_at': task['date'].get('update'),
                'completed_at': task['date'].get('complete'),
                'deadline': task['date'].get('runtime_individual_hour')
            },
            'addata': {
                'reason': task['additional_data'].get('30', {}).get('value'),
                'solve': task['additional_data'].get('36', {}).get('value'),
                'appeal': {
                    'phone': task['additional_data'].get('29', {}).get('value'),
                    'type': task['additional_data'].get('28', {}).get('value')
                },
                'cost': float(task['additional_data'].get('26', {}).get('value'))
                    if task['additional_data'].get('26', {}).get('value') else None
            } if task['type']['id'] == 37 else {
                'reason': task['additional_data'].get('33', {}).get('value'),
                'info': task['additional_data'].get('34', {}).get('value'),
                'appeal': {
                    'phone': task['additional_data'].get('29', {}).get('value'),
                    'type': task['additional_data'].get('28', {}).get('value')
                },
            } if task['type']['id'] == 38 else {
                'coord': list(map(float, task['additional_data']['7']['value'].split(',')))
                    if '7' in task['additional_data'] else None,
                'tariff': task['additional_data'].get('25', {}).get('value'),
                'connect_type': task['additional_data'].get('27', {}).get('value')
            } if task['type']['id'] == 28 else None,
            'type': {
                'id': task['type']['id'],
                'name': task['type']['name']
            },
            'author_id': task.get('author_employee_id'),
            'status': {
                'id': task['state']['id'],
                'name': task['state']['name'],
                'system_id': task['state']['system_role']
            } if task.get('state') else None,
            'address': {
                'id': task['address'].get('addressId'),
                'name': task['address'].get('text'),
                'apartment': unescape(task['address']['apartment'])
                    if task['address'].get('apartment') else None
            },
            'customer': task['customer'][0] if 'customer' in task else None,
            'employees': list(task.get('staff', {}).get('employee', {}).values()),
            'divisions': list(task.get('staff', {}).get('division', {}).values()),
        }
    }

@router.get('/{id}/comments', deprecated=True)
def api_get_task_comments(id: int):
    comments = api_call('task', 'get_comment', f'id={id}')['data']
    return {
        'status': 'success',
        'id': id,
        'comments': [{
            'id': comment['comment_id'],
            'date': comment['date_add'],
            'content': unescape(comment['text']),
            'author': comment['employee_id']
        } for comment in comments]
    }

@router.post('/{id}/comment')
def api_post_task_comment(id: int, content: str, author: int | None = None):
    comment_id = api_call('task', 'comment_add', f'id={id}&comment={content}{f"&employee_id={author}" if author else ""}')['Id']
    return {
        'status': 'success',
        'id': comment_id
    }


@router.post('')
def api_post_task(
    customer_id: int | None = None, author_id: int | None = None,
    reason: str | None = None, phone: int | None = None, type: str | None = None,
    box: bool = False, address_id: int | None = None, description: str | None = None,
    divisions: str = ''
):
    if box and address_id is None:
        return JSONResponse({'status': 'fail', 'detail': 'address_id is required for box'}, 422)
    if not box and customer_id is None:
        return JSONResponse({'status': 'fail', 'detail': 'customer_id is required for customer'}, 422)

    list_divisions = str_to_list(divisions)
    if box:
        id = api_call(
            'task', 'add',
            f'work_typer=38&work_datedo={get_current_time()}&author_employee_id={author_id}'
            f'&address_id={address_id}&opis={description}&division={list_to_str(list_divisions)}'
            f'&deadline_hour=72&customer_id={customer_id}'
        )['Id']
    else:
        id = api_call(
            'task', 'add',
            f'work_typer=37&work_datedo={get_current_time()}&author_employee_id={author_id}'
            f'&opis={description}&division={list_to_str(list_divisions)}&customer_id={customer_id}'
            f'&deadline_hour=72'
        )['Id']

    if reason:
        set_additional_data(17, 33 if box else 30, id, reason)
    if phone:
        set_additional_data(17, 29, id, phone)
    if type:
        set_additional_data(17, 28, id, type)
    if description:
        api_call('task', 'comment_add', f'id={id}&comment={description}&employee_id={author_id}')
    return {
        'status': 'success',
        'id': id
    }
