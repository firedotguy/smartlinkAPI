from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from ont import search_ont, reset_ont, get_ont_summary

router = APIRouter(prefix='/ont')

@router.get('')
def api_get_ont(request: Request, olt_id: int, sn: str):
    olt = [olt for olt in request.app.state.olts if olt['id'] == olt_id]
    if not olt:
        return JSONResponse({'status': 'fail', 'detail': 'olt not found'}, status_code=404)
    olt = olt[0]
    res = search_ont(sn, olt['host'])
    if res is None:
        return {'status': 'fail', 'detail': 'ont not found'}
    if res[0] is not None:
        olt['name'] = res[0]
    return {
        'status': 'success',
        'sn': sn,
        'olt': olt,
        'data': res[1]
    }

@router.post('/restart')
def api_post_ont_restart(id: int, host: str, fibre: int, service: int, port: int):
    return reset_ont(host, id, {'fibre': fibre, 'service': service, 'port': port})

@router.get('/summary')
def api_get_ont_summary(host: str, fibre: int, service: int, port: int):
    return get_ont_summary(host, {'fibre': fibre, 'service': service, 'port': port})
