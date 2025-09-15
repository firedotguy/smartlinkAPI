from html import unescape

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from api import api_call, set_additional_data
from utils import get_current_time, str_to_list, list_to_str, normalize_items

router = APIRouter(prefix='/task')

@router.get('/{id}')
def api_get_task(id: int):
    # print(api_call('task', 'show', f'id={id}'))
    task = api_call('task', 'show', f'id={id}').get('data')
    if task is None:
        return JSONResponse({'status': 'fail', 'detail': 'task not found'})
    return {
        'status': 'success',
        'data': {
            'comments': [
                {
                    'id': comment['id'],
                    'created_at': comment['dateAdd'],
                    'author_id': comment['employee_id'],
                    'content': comment['comment']
                } for comment in task['comments'].values()
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
                'solve': task['additional_data'].get('36', {}).get('value')
            },
            'type': task['type'],
            'author_id': task.get('author_employee_id'),
            'status': {
                'id': task['state']['id'],
                'name': task['state']['name'],
                'system_id': task['state']['system_role']
            } if task.get('state') else None,
            'address': task['address']['text'] if task.get('address', {}).get('text') else None,
            'customer': task['customer'][0],
            'employees': list(task['staff']['employee'].values())
        }
    }

@router.get('/{id}/comments', deprecated=True)
def api_get_task_comments(id: int):
    comments = api_call('task', 'get_comment', f'id={id}')['data']
    return {
        'status': 'OK',
        'id': id,
        'comments': [{
            'id': comment['comment_id'],
            'date': comment['date_add'],
            'content': unescape(comment['text']),
            'author': comment['employee_id']
        } for comment in comments]
    }


@router.post('/task')
def api_post_task(customer_id: int, author_id: int, reason: str, phone: int, type: str,
        box: bool = False, box_id: int | None = None, description: str = '', divisions: str = ''):
    list_divisions = str_to_list(divisions)
    if box:
        id = api_call('task', 'add', f'work_typer=38&work_datedo={get_current_time()}&customer_id={customer_id}&author_employee_id={author_id}&address_id={box_id}&opis={description}{"&division=" + list_to_str(list_divisions) if list_to_str(list_divisions) else ""}&deadline_hour=72')['Id']
    else:
        id = api_call('task', 'add', f'work_typer=37&work_datedo={get_current_time()}&customer_id={customer_id}&author_employee_id={author_id}&opis={description}{"&division=" + list_to_str(list_divisions) if list_to_str(list_divisions) else ""}&deadline_hour=72')['Id']

    set_additional_data(17, 33 if box else 30, id, reason)
    set_additional_data(17, 29, id, phone)
    set_additional_data(17, 28, id, type)
    if description:
        api_call('task', 'comment_add', f'id={id}&comment={description}')
    return {
        'status': 'OK',
        'id': id,
        'customer_id': customer_id,
        'author_id': author_id,
        'reason': reason,
        'phone': phone,
        'type': type,
        'description': description,
        'divisions': list_divisions,
        'is_magistral': box,
        'box_id': box_id
    }