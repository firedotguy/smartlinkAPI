from fastapi import APIRouter
from fastapi.requests import Request

router = APIRouter(prefix='/addata')

@router.get('/options')
def api_get_options_list(request: Request):
    return {
        'status': 'success',
        'data': request.app.state.addatas
    }
