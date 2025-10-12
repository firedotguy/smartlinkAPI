from html import unescape

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from api import api_call, set_additional_data
from utils import get_current_time, normalize_items, str_to_list, list_to_str, remove_sn

router = APIRouter(prefix='/task')

@router.get('/{id}')
def api_get_task(id: int, get_employee_names: bool = True):
    task = api_call('task', 'show', f'id={id}').get('data')
    if task is None:
        return JSONResponse({'status': 'fail', 'detail': 'task not found'}, 404)

    customer = api_call('customer', 'get_data', f'id={task["customer"][0]}')['data'] if 'customer' in task else None


    return {
        'status': 'success',
        'data': {
            'id': id,
            'comments': [
                {
                    'id': comment['id'],
                    'created_at': comment['dateAdd'],
                    'author': {
                        'id': comment['employee_id'],
                        'name': (api_call('employee', 'get_data', f'id={comment["employee_id"]}')
                                .get('data', {}).get(str(comment['employee_id']), {}).get('name')
                                if get_employee_names else None)
                    } if comment.get('employee_id') else None,
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
            'author': {
                'id': task['author_employee_id'],
                'name': (api_call('employee', 'get_data', f'id={task["author_employee_id"]}')
                    .get('data', {}).get(str(task['author_employee_id']), {}).get('name')
                    if get_employee_names else None)
            },
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
            'customer': {
                'id': customer['id'],
                'name': remove_sn(customer['full_name'])
            } if customer else None,
            'employees': list(task.get('staff', {}).get('employee', {}).values()), # TODO: get employees names
            'divisions': list(task.get('staff', {}).get('division', {}).values()), # TODO: get divisions names
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
    type: int,

    customer_id: int | None = None,
    address_id: int | None = None,

    author_id: int | None = None,
    reason: str | None = None,
    appeal_phone: int | None = None,
    appeal_type: str | None = None,

    description: str | None = None,
    divisions: str = ''
):
    if (customer_id is None and address_id is None) or (customer_id is not None and address_id is not None):
        return JSONResponse({'status': 'fail', 'detail': 'one of address_id or customer_id must be provided'}, 422)
    if (reason is None or appeal_phone is None or appeal_type is None) and type in (37, 46, 53):
        return JSONResponse({'status': 'fail', 'detail': 'Reason, appeal_phone and appeal_type must be provided for task with type 37, 46 or 53'}, 422)
    if (appeal_phone is None) and type == 60:
        return JSONResponse({'status': 'fail', 'detail': 'Appeal_phone must be provided for task with type 60'}, 422)
    if (reason is None or appeal_type is None) and type == 38:
        return JSONResponse({'status': 'fail', 'detail': 'Reason and appeal_type must be provided for task with type 38'}, 422)
    if (reason is None or appeal_phone is None) and type == 48:
        return JSONResponse({'status': 'fail', 'detail': 'Reason and appeal_phone must be provided for task with type 48'}, 422)


    list_divisions = str_to_list(divisions)
    params = [
        f'work_typer={type}',
        f'work_datedo={get_current_time()}',
        f'deadline_hour=72',
        f'division_id={list_to_str(list_divisions)}'
    ]

    if author_id:
        params.append(f'author_employee_id={author_id}')
    if address_id:
        params.append(f'address_id={address_id}')
    if description:
        params.append(f'opis={description}')
    if customer_id:
        params.append(f'customer_id={customer_id}')

    query_string = '&'.join(params)
    print(query_string)

    id = api_call('task', 'add', query_string)['Id']

    if type in (37, 46, 53):
        set_additional_data(17, 30, id, reason)
        set_additional_data(17, 29, id, appeal_phone)
        set_additional_data(17, 28, id, appeal_type)
    elif type == 60:
        set_additional_data(17, 29, id, appeal_phone)
    elif type == 38:
        set_additional_data(17, 30, id, reason)
        set_additional_data(17, 28, id, appeal_type)
    elif type == 48:
        set_additional_data(17, 30, id, reason)
        set_additional_data(17, 29, id, appeal_phone)

    if description:
        api_call('task', 'comment_add', f'id={id}&comment={description}&employee_id={author_id}')
    return {
        'status': 'success',
        'id': id
    }

@router.get('')
def api_get_tasks(
    customer_id: int | None = None,
    get_data: bool = True,
    get_employee_names: bool = True,
):
    tasks = []
    if customer_id is not None:
        tasks = list(map(int, str_to_list(api_call('task', 'get_list', f'customer_id={customer_id}')['list'])))
    else:
        return JSONResponse({'status': 'fail', 'detail': 'no filters provided'}, 422)

    tasks_data = []
    if get_data:
        for task in normalize_items(api_call('task', 'show', f'id={list_to_str(tasks)}')):
            customer = api_call('customer', 'get_data', f'id={task["customer"][0]}')['data'] if 'customer' in task else None
            tasks_data.append({
                'id': task['id'],
                'comments': [
                    {
                        'id': comment['id'],
                        'created_at': comment['dateAdd'],
                        'author': {
                            'id': comment['employee_id'],
                            'name': (api_call('employee', 'get_data', f'id={comment["employee_id"]}')
                                    .get('data', {}).get(str(comment['employee_id']), {}).get('name')
                                    if get_employee_names else None)
                        } if comment.get('employee_id') else None,
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
                'author': {
                    'id': task['author_employee_id'],
                    'name': (api_call('employee', 'get_data', f'id={task["author_employee_id"]}')
                        .get('data', {}).get(str(task['author_employee_id']), {}).get('name')
                        if get_employee_names else None)
                },
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
                'customer': {
                    'id': customer['id'],
                    'name': remove_sn(customer['full_name'])
                } if customer else None,
                'employees': list(task.get('staff', {}).get('employee', {}).values()),
                'divisions': list(task.get('staff', {}).get('division', {}).values()),
            })

    return {
        'status': 'success',
        'data': tasks_data or tasks
    }