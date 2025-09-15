from html import unescape

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from api import api_call
from utils import normalize_items, get_attach_url

router = APIRouter(prefix='/attachs/')

@router.get('/customer/{id}')
def api_get_attachs(id: int, include_task: bool = False):
    attachs = normalize_items(api_call('attach', 'get', f'object_id={id}&object_type=customer'))
    if include_task:
        tasks = api_call('task', 'get_list', f'customer_id={id}')['list'].split(',')
        for task in tasks:
            task_attachs = normalize_items(api_call('attach', 'get', f'object_id={task}&object_type=task'))
            if isinstance(task_attachs, dict):
                for attach in task_attachs: attach['source'] = 'task'
                attachs.extend(task_attachs)
    return {
        'status': 'success',
        'data': [{
            'id': attach['id'],
            # 'url': api_call('attach', 'get_file_temporary_link', f'uuid={attach["id"]}'),
            'url': get_attach_url(attach['id']),
            'name': attach['internal_filepath'],
            'extension': attach['internal_filepath'].split('.')[1].lower() if '.' in attach['internal_filepath'] else None,
            'date': attach['date_add'],
            'source': attach.get('source', 'customer')
        } for attach in attachs]
    }