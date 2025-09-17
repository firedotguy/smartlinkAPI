from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from api import api_call

router = APIRouter(prefix='/employee')

@router.get('/login')
def api_get_employee_login(login: str, password: str):
    result = 'result' in api_call('employee', 'check_pass', f'login={login}&pass={password}')
    return {
        'result': 'OK',
        'correct': result,
        'id': api_call('employee', 'get_employee_id', f'data_typer=login&data_value={login}').get('id')
            if result else None
    }

@router.get('/name/{id}')
def api_get_employee_name(id: int):
    data = api_call('employee', 'get_data', f'id={id}')
    if 'data' not in data:
        return JSONResponse({'status': 'fail', 'detail': 'employee not found'}, 404)
    return {
        'status': 'success',
        'id': id,
        'name': data['data'][str(id)]['name']
    }


@router.get('/divisions')
def api_get_employee_divisions(request: Request):
    return {
        'result': 'OK',
        'data': request.app.state.divisions
    }
