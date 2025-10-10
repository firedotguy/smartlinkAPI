from html import unescape

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request

from routers import addata
from routers import box
from routers import customer
from routers import employee
from routers import neomobile
from routers import ont
from routers import task
from routers import attach
from routers import inventory
from api import api_call
from config import API_KEY as APIKEY

app = FastAPI(title='SmartLinkAPI')

app.state.tariffs = {
    tariff['billing_uuid']: unescape(tariff['name'])
    for tariff in api_call('tariff', 'get')['data'].values()
}
app.state.customer_groups = {
    group['id']: group['name']
    for group in api_call('customer', 'get_customer_group')['data'].values()
}
app.state.addatas = {
    str(data['id']): unescape(data['available_value'][0]).split('\n')
    for data in api_call('additional_data', 'get_list', 'section=17')['data'].values()
    if 'available_value' in data
}
app.state.tmc_categories = [
    {
        'id': section['id'],
        'name': section['name'],
        'type_id': section['type_id'],
        'parent_id': section['parent_id'] if section['parent_id'] != 0 else None
    } for section in api_call('inventory', 'get_inventory_section_catalog')['data'].values()
]
app.state.olts = [
    {
        'id': olt['id'],
        'device': olt['name'],
        'host': olt['host'],
        'online': bool(olt['is_online']),
        'location': unescape(olt['location'])
    } for olt in api_call('device', 'get_data', 'object_type=olt&is_hide_ifaces_data=1')['data']
        .values()
]
app.state.divisions = [
    {
        'id': division['id'],
        'parent_id': division['parent_id'],
        'name': unescape(division['name'])
    } for division in api_call('employee', 'get_division_list')['data'].values()
]
app.state.cached_employees = []
app.state.cached_customers = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(addata.router)
app.include_router(attach.router)
app.include_router(box.router)
app.include_router(customer.router)
app.include_router(employee.router)
app.include_router(neomobile.router)
app.include_router(ont.router)
app.include_router(task.router)
app.include_router(inventory.router)


@app.middleware('http')
async def check_api_key(request: Request, call_next):
    """API middleware for validate APIKEY"""
    url = request.url.path.rstrip('/')
    if 'apikey' not in request.query_params:
        return JSONResponse({'status': 'fail', 'detail': 'no api key'}, 403)
    if url in ('/favicon.ico', '') and request.query_params.get('apikey') != APIKEY:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, 401)
    return await call_next(request)

@app.get('/favicon.ico', include_in_schema=False)
def favicon() -> FileResponse:
    """Get favicon"""
    return FileResponse('favicon.ico')
