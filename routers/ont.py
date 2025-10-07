from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from api import api_call
from ont import search_ont, reset_ont, get_ont_summary, toggle_catv

router = APIRouter(prefix='/ont')

@router.get('')
def api_get_ont(request: Request, olt_id: int, sn: str):
    olt = [olt for olt in request.app.state.olts if olt['id'] == olt_id]
    if not olt:
        return JSONResponse({'status': 'fail', 'detail': 'olt not found'}, 404)
    olt = olt[0]
    res = search_ont(sn, olt['host'])
    if res is None:
        return {'status': 'fail', 'detail': 'ont not found'}
    if res[1] is not None:
        olt['name'] = res[1]
    return {
        'status': 'success',
        'sn': sn,
        'olt': olt,
        'data': res[0]
    }

@router.post('/{fibre}/{service}/{port}/{id}/restart')
def api_post_ont_restart(fibre: int, service: int, port: int, id: int, host: str):
    return reset_ont(host, id, {'fibre': fibre, 'service': service, 'port': port})

@router.post('/{fibre}/{service}/{port}/{id}/catv/{catv_id}/toggle')
def api_post_ont_catv_toggle(fibre: int, service: int, port: int, id: int, catv_id: int, state: bool, host: str):
    result = toggle_catv(host, id, catv_id, state, {'fibre': fibre, 'service': service, 'port': port})
    return JSONResponse(result[0], result[1])

@router.get('/summary')
def api_get_ont_summary(host: str, fibre: int, service: int, port: int):
    return get_ont_summary(host, {'fibre': fibre, 'service': service, 'port': port})

@router.post('/rewrite_sn')
def api_post_ont_rewrite_sn(customer_id: int, ls: int, sn: str):
    res = api_call(
        'customer', 'mark_add',
        f'nogi=bogi&mark_id=1&customer_id={customer_id}&_command=attach_onu&_onu_serial={sn}&'
        f'_contract_number={ls}',
        timeout=360
    )
    if int(res['result']):
        return {'status': 'fail', 'detail': res.get('msg')}
    return {'status': 'success', 'message': res.get('msg')}