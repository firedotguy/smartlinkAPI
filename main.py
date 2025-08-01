from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from functions import *
from api import *
from config import api_key as APIKEY

app = FastAPI(title='Smart Connect')

tariffs = get_tariffs()
customer_groups = get_customer_groups()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Или ["http://localhost:3000"] — для безопасности
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse('favicon.ico')

@app.get('/customer')
def customer(id: int, apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    user = get_userdata(id)
    items = get_inventory(id)
    item_names = get_inventory_data(items)
    inventory = []
    for item in items:
        item_name = item_names[item_names.index([i for i in item_names if i['id'] == str(item['inventory_type_id'])][0])]
        inventory.append({
            'id': item['id'],
            'catalog_id': item['inventory_type_id'],
            'name': item_name['name'],
            'amount': item['amount'],
            'category_id': item_name['catalog'],
            'sn': item['serial_number']
        })

    tariff_data = []
    for tariff in user['tariff']['current']:
        tariff_data.append({'id': int(tariff['id']), 'name': tariffs[tariff['id']]})

    geodata = {}
    if 'additional_data' in user:
        if '7' in user['additional_data'].keys():
            geodata['coord'] = list(map(float, user['additional_data']['7']['value'].split(',')))
        if '42' in user['additional_data'].keys():
            geodata['address'] = convert(user['additional_data']['42']['value'])
        if '6' in user['additional_data'].keys():
            geodata['2gis_link'] = convert(user['additional_data']['6']['value'])
        else:
            if 'coord' in geodata.keys():
                geodata['2gis_link'] = twogis_coord(geodata['coord'][0], geodata['coord'][1])
    if 'coord' in geodata.keys():
        geodata['neo_link'] = neo_coord(geodata['coord'][0], geodata['coord'][1])
    result = {
        'result': 'OK',
        'id': user['id'],
        'api_count': 3,
        'balance': user['balance'],
        'name': cut_agree(user['full_name']),
        'agreement': parse_agreement(user['agreement'][0]['number']),
        'status': str_status(user['state_id']),
        'sn': get_sn(user['full_name']),
        # 'onu_level': get_ont_data(get_sn(user['full_name'])),
        'tariffs': tariff_data,
        'phones': [phone['number'] for phone in user['phone']],
        'last_activity': user['date_activity'],
        'inventory': inventory,
        'house_id': user['address'][0]['house_id'],
    }
    if geodata:
        result['geodata'] = geodata
    if 'group' in user:
        result['group'] = {
            'id': list(user['group'].values())[0]['id'],
            'name': customer_groups[list(user['group'].values())[0]['id']]
        }
    return result

@app.get('/attachs')
def attachs(id: int, apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    c_attachs = get_customer_attachs(id)
    tasks = get_customer_tasks(id)
    t_attachs = {}
    for task in tasks:
        task_attachs = get_task_attachs(task)
        if isinstance(task_attachs, dict):
            t_attachs.update(task_attachs)
    return {
        'result': 'OK',
        'api_count': 2 + len(c_attachs) + len(tasks) + len(t_attachs),
        'customer': [{
            'id': attach['id'],
            'url': get_attach_data(attach['id']),
            'name': attach['internal_filepath'],
            'extension': attach['internal_filepath'].split('.')[1].lower() if '.' in attach['internal_filepath'] else None,
            'date': attach['date_add']
        } for attach in c_attachs.values()] if c_attachs else [],
        'task': [{
            'id': attach['id'],
            'url': get_attach_data(attach['id']),
            'name': attach['internal_filepath'],
            'extension': attach['internal_filepath'].split('.')[1].lower() if '.' in attach['internal_filepath'] else None,
            'date': attach['date_add']
        } for attach in t_attachs.values()],
    }

@app.get('/box')
def box(id: int, apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    house = get_house(id)
    neighbours = get_neighbours(house['building_id'])
    neighbours_data = get_usersdata(list(map(str, neighbours)))
    neighbours = [{
        'id': neighbour['id'],
        'name': cut_agree(neighbour['full_name']),
        'last_activity': neighbour.get('date_activity'),
        'status': str_status(neighbour['state_id']),
        'sn': get_sn(neighbour['full_name']),
        'onu_level': get_ont_data(get_sn(neighbour['full_name']))
    } for neighbour in neighbours_data]
    return {
        'result': 'OK',
        'api_count': 3 + len(neighbours),
        'id': id,
        'building_id': house['building_id'],
        'name': house['full_name'],
        'customers': neighbours
    }

@app.get('/find')
def find(query: str, apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    if query.isdigit():
        users = find_agreement(query)
    else:
        users = find_names(query)

    user_data = []

    if len(users) > 0:
        user_data = [{
            'id': user['id'],
            'name': user['full_name'][:user['full_name'].find(' (')],
            'agreement': parse_agreement(user['agreement'][0]['number'])
        } for user in get_usersdata(users)]

    return {
        'result': 'OK',
        'customers': user_data,
        'api_count': 2,
        'search_type': 'agreement' if query.isdigit() else 'name'
    }

@app.get('/login')
def login(login: str, password: str, apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    return {
        'result': 'OK',
        'api_count': 1,
        'correct': check_login(login, password)}