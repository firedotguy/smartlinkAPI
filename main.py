from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime as dt

from utils import *
from api import *
from ont import search_ont, reset_ont, get_summary
from config import api_key as APIKEY

app = FastAPI(title='Smart Connect')

tariffs = get_tariffs()
customer_groups = get_customer_groups()
additional_datas = get_additional_datas()
tmc_categories = get_tmc_categories()
olts = get_olts()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/favicon.ico', include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse('favicon.ico')

@app.get('/customer')
def customer(id: int, apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, 403)
    customer = api_call('customer', 'get_data', f'id={id}')['data']
    # if customer is None: return JSONResponse({'status': 'fail', 'detail': 'customer not found'}, 404)

    items = api_call('inventory', 'get_inventory_amount', f'location=customer&object_id={id}').get('data', []).values()
    item_names = [{
        'id': str(i['id']),
        'name': convert(i['name']),
        'catalog': i['inventory_section_catalog_id']
    } for i in api_call('inventory', 'get_inventory_catalog', f'id={','.join([str(i['inventory_type_id']) for i in items])}').values()]
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
    for tariff in customer['tariff']['current']:
        if tariff['id']:
            tariff_data.append({'id': int(tariff['id']), 'name': tariffs[tariff['id']]})

    geodata = {}
    if 'additional_data' in customer:
        if '7' in customer['additional_data'].keys():
            geodata['coord'] = list(map(float, customer['additional_data']['7']['value'].split(',')))
        if '42' in customer['additional_data'].keys():
            geodata['address'] = convert(customer['additional_data']['42']['value'])
        if '6' in customer['additional_data'].keys():
            geodata['2gis_link'] = convert(customer['additional_data']['6']['value'])
        else:
            if 'coord' in geodata.keys():
                geodata['2gis_link'] = twogis_coord(geodata['coord'][0], geodata['coord'][1])
    if 'coord' in geodata.keys():
        geodata['neo_link'] = neo_coord(geodata['coord'][0], geodata['coord'][1])

    tasks_id = api_call('task', 'get_list', f'customer_id={id}')['list'].split(',')
    if tasks_id:
        tasks_data = get_tasks_data(tasks_id)
        tasks = []
        for task in tasks_data:
            dates = {}
            if 'create' in task['date']:
                dates['create'] = task['date']['create']
            if 'update' in task['date']:
                dates['update'] = task['date']['update']
            if 'complete' in task['date']:
                dates['complete'] = task['date']['complete']
            if task['type']['name'] != 'Обращение абонента' and task['type']['name'] != 'Регистрация звонка':
                tasks.append({
                    'id': task['id'],
                    'customer_id': task['customer'][0],
                    'employee_id': list(task['staff']['employee'].values())[0] if 'staff' in task and 'employee' in task['staff'] else None,
                    'name': task['type']['name'],
                    'status': {'id': task['state']['id'], 'name': task['state']['name'], 'system_id': task['state']['system_role']},
                    'address': task['address']['text'],
                    'dates': dates
                })
    else:
        tasks = []

    olt = api_call('commutation', 'get_data', f'object_type=customer&object_id={id}&is_finish_data=1')['data']
    if 'finish' not in olt or olt['finish'].get('object_type') != 'switch' and get_sn(customer['full_name']) is not None:
        ont = api_call('device', 'get_ont_data', f'id={get_sn(customer["full_name"])}')['data']
        if isinstance(ont, dict):
            olt_id = ont.get('device_id')
        else:
            olt_id = None
    elif '(' not in customer['full_name']:
        olt_id = None
    else:
        olt_id = olt['finish']['object_id']

    return {
        'result': 'OK',
        'id': customer['id'],
        'olt_id': olt_id,
        'balance': customer['balance'],
        'name': cut_sn(customer['full_name']),
        'agreement': parse_agreement(customer['agreement'][0]['number']),
        'status': str_status(customer['state_id']),
        'sn': get_sn(customer['full_name']),
        'tasks': tasks,
        # 'onu_level': get_ont_data(get_sn(customer['full_name'])),
        'tariffs': tariff_data,
        'phones': [phone['number'] for phone in customer['phone']],
        'last_activity': customer['date_activity'],
        'inventory': inventory,
        'house_id': customer['address'][0]['house_id'],
        'geodata': geodata,
        'group': {
            'id': list(customer['group'].values())[0]['id'],
            'name': customer_groups[list(customer['group'].values())[0]['id']]
        } if 'group' in customer else None
    }


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

@app.get('/comments')
def comments(id: int, apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    comments = api_call('task', 'get_comment', f'id={id}')['data']
    return {
        'status': 'OK',
        'id': id,
        'comments': [{
            'id': comment['comment_id'],
            'date': comment['date_add'],
            'content': comment['text'],
            'author': comment['employee_id']
        } for comment in comments]
    }

@app.get('/box')
def box(id: int, apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    house = api_call('address', 'get_house', f'building_id={id}')
    if house:
        neighbours = api_call('customer', 'get_customers_id', f'house_id={house["building_id"]}')
        neighbours_data = get_customers_data(list(map(str, neighbours)))
        neighbours = [{
            'id': neighbour['id'],
            'name': cut_sn(neighbour['full_name']),
            'last_activity': neighbour.get('date_activity'),
            'status': str_status(neighbour['state_id']),
            'sn': get_sn(neighbour['full_name']),
            'onu_level': get_ont_data(get_sn(neighbour['full_name']))
        } for neighbour in neighbours_data]
        return {
            'result': 'OK',
            'id': id,
            'building_id': house['building_id'],
            'name': house['full_name'],
            'customers': neighbours
        }
    return JSONResponse({
        'status': 'fail',
        'detail': 'house not found'
    }, status_code=404)

@app.get('/find')
def find(query: str, apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    customers = []
    if query.isdigit():
        customer = api_call('customer', 'get_customer_id', f'data_typer=agreement_number&data_value={query}')
        if 'Id' in customer:
            customers = [str(customer['Id'])]
    else:
        customers = [str(customer) for customer in api_call('customer', 'get_customers_id', f'name={query}&is_like=1&limit=10')['data']]

    customer_data = []

    if len(customers) > 0:
        customer_data = [{
            'id': customer['id'],
            'name': customer['full_name'][:customer['full_name'].find(' (')],
            'agreement': parse_agreement(customer['agreement'][0]['number']),
            'status': str_status(customer['state_id'])
        } for customer in parse_customers_list(api_call('customer', 'get_data', f'id={",".join(customers)}'))]

    return {
        'result': 'OK',
        'customers': customer_data,
        'search_type': 'agreement' if query.isdigit() else 'name'
    }

@app.get('/login')
def login(login: str, password: str, apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    result = 'result' in api_call('employee', 'check_pass', f'login={login}&pass={password}')
    return {
        'result': 'OK',
        'correct': result,
        'id': api_call('employee', 'get_employee_id', f'data_typer=login&data_value={login}') if result else None
    }

@app.get('/additional_data')
def additional_data(apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    return {
        'result': 'OK',
        'data': additional_datas
    }

@app.get('/divisions')
def divisions(apikey: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    return {
        'result': 'OK',
        'data': [{
            'id': i['id'],
            'parent': i['parent_id'],
            'name': convert(i['name'])
        } for i in get_divisions()]
    }

@app.post('/task')
def create_task(customer_id: int, author_id: int, reason: str, apikey: str, phone: int, type: str,
        box: bool = False, box_id: int | None = None, description: str = '', divisions: str = '[]'):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    if box:
        id = api_call('task', 'add', f'work_typer=38&work_datedo={dt.now().strftime('%Y.%m.%d %H:%M:%S')}&customer_id={customer_id}&author_employee_id={author_id}&address_id={box_id}&opis={description}{"&division=" + ','.join(eval(divisions)) if ','.join(eval(divisions)) else ""}&deadline_hour=72')['Id']
    else:
        id = api_call('task', 'add', f'work_typer=37&work_datedo={dt.now().strftime('%Y.%m.%d %H:%M:%S')}&customer_id={customer_id}&author_employee_id={author_id}&opis={description}{"&division=" + ','.join(eval(divisions)) if ','.join(eval(divisions)) else ""}&deadline_hour=72')['Id']

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
        'divisions': eval(divisions),
        'is_magistral': box,
        'box_id': box_id
    }

@app.get('/ont')
def get_ont(apikey: str, olt_id: int, sn: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    olt = [olt for olt in olts if olt['id'] == olt_id]
    if not olt:
        return JSONResponse({'status': 'fail', 'detail': 'wrong olt id'}, status_code=404)
    olt = olt[0]
    return {
        'status': 'OK',
        'sn': sn,
        'olt': olt,
        'data': search_ont(sn, olt['host'])
    }

@app.get('/ont/restart')

def restart_ont(apikey: str, id: int, host: str, fibre: int, service: int, port: int):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)

    return reset_ont(host, id, {'fibre': fibre, 'service': service, 'port': port})

@app.get('/ont/summary')
def summary_ont(apikey: str, host: str, fibre: int, service: int, port: int):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)

    return get_summary(host, {'fibre': fibre, 'service': service, 'port': port})

@app.get('/customer/name')
def customer_name(apikey: str, id: int):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    data = api_call('customer', 'get_data', f'id={id}')
    if 'data' not in data:
        return JSONResponse({'status': 'fail', 'detail': 'customer not found'}, status_code=404)
    return {
        'status': 'success',
        'id': id,
        'name': cut_sn(data['data']['full_name'])
    }

@app.get('/employee/name')
def employee_name(apikey: str, id: int):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    data = api_call('employee', 'get_data', f'id={id}')
    if 'data' not in data:
        return JSONResponse({'status': 'fail', 'detail': 'employee not found'}, status_code=404)
    return {
        'status': 'success',
        'id': id,
        'name': data['data'][str(id)]['name']
    }


@app.get('/neomobile/login')
def neomobile_login(apikey: str, phone: str, agreement: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    id = api_call('customer', 'get_customer_id', f'data_typer=agreement_number&data_value={agreement}')
    if 'Id' not in id:
        return JSONResponse({'status': 'fail', 'detail': 'customer not found'}, status_code=404)

    data = api_call('customer', 'get_data', f'id={id}')
    if 'data' not in data:
        if len(data['data']['phone']) > 0:
            if data['data']['phone'][0]['number'] != phone:
                return JSONResponse({'status': 'fail', 'detail': 'invalid phone number'}, status_code=404)
    data = data['data']

    tariff_data = []
    for tariff in data['tariff']['current']:
        if tariff['id']:
            tariff_data.append({'id': int(tariff['id']), 'name': tariffs[tariff['id']]})
    return {
        'status': 'success',
        'id': id,
        'name': cut_sn(data['full_name']),
        'phone': phone,
        'agreement': agreement,
        'balance': data['balance'],
        'last_activity': data['date_activity'],
        'tariffs': tariff_data
    }

@app.get('/neomobile/customer')
def neomobile_customer(apikey: str, id: int):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    data = api_call('customer', 'get_data', f'id={id}')
    if 'data' not in data:
        return JSONResponse({'status': 'fail', 'detail': 'customer not found'}, status_code=404)
    data = data['data']

    tariff_data = []
    for tariff in data['tariff']['current']:
        if tariff['id']:
            tariff_data.append({'id': int(tariff['id']), 'name': tariffs[tariff['id']]})

    tasks = api_call('task', 'get_list', f'customer_id={id}&type_id=37&state_id=18,3,15,17,11,1,10,16,19')['list'].split(',')
    if tasks == ['']: tasks.clear()
    return {
        'status': 'success',
        'id': data['id'],
        'name': cut_sn(data['full_name']),
        'phones': [phone['number'] for phone in data['phone']],
        'agreement': data['agreement'][0]['number'],
        'balance': data['balance'],
        'last_activity': data['date_activity'],
        'connected_at': data['date_connect'],
        'created_at': data['date_create'],
        'tariffs': tariff_data,
        'status': str_status(data['state_id']),
        'task': None if len(tasks) == 0 else int(tasks[0])
    }


@app.post('/neomobile/task')
def neomobile_create_task(apikey: str, customer_id: int, phone: str, reason: str, comment: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    id = api_call('task', 'add', f'work_typer=37&work_datedo={dt.now().strftime("%Y.%m.%d %H:%M:%S")}&customer_id={customer_id}&author_employee_id=184&opis={comment}&deadline_hour=72&employee_id=184&division_id=81')['Id']
    set_additional_data(17, 28, id, 'Приложение') #TODO: make own appeal type
    set_additional_data(17, 29, id, phone)
    set_additional_data(17, 30, id, reason)
    api_call('task', 'comment_add', f'id={id}&comment={comment}&employee_id=184')

    return {
        'status': 'success',
        'id': id,
        'customer_id': customer_id,
        'phone': phone,
        'reason': reason,
        'comment': comment
    }

@app.post('/neomobile/task/cancel')
def neomobile_task_cancel(apikey: str, id: int):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    api_call('task', 'change_state', f'id={id}&state_id=10')
    return {
        'status': 'success',
        'id': id
    }

@app.get('/neomobile/task')
def neomobile_task(apikey: str, id: int):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    data = api_call('task', 'show', f'id={id}')
    if 'data' not in data:
        return JSONResponse({'status': 'fail', 'detail': 'task not found'}, status_code=404)
    comments = api_call('task', 'get_comment', f'task_id={id}')['data']
    data = data['data']
    return {
        'status': 'success',
        'id': id,
        'type': data['type'],
        'created_at': data['date']['create'],
        'completed_at': data['date']['complete'] if 'complete' in data['date'] else None,
        'status': {'id': data['state']['id'], 'name': data['state']['name']},
        'address': {'id': data['address']['addressId'], 'text': data['address']['text']},
        'customer': data['customer'][0],
        'reason': data['additional_data']['30']['value'] if '30' in data['additional_data'] else None,
        'phone': data['additional_data']['29']['value'] if '29' in data['additional_data'] else None,
        'comments': [{
            'id': comment['comment_id'],
            'content': comment['text'],
            'author_id': comment['employee_id'],
            'created_at': comment['date_add']
        } for comment in comments]
    }

@app.post('/neomobile/task/comment')
def neomobile_comment(apikey: str, id: int, content: str):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    data = api_call('task', 'comment_add', f'id={id}&comment={content}&employee_id=184')
    return {
        'status': 'success',
        'id': data['Id'],
        'task_id': id,
        'content': content
    }

@app.get('/neomobile/inventory')
def neomobile_inventory(apikey: str, id: int):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    data = api_call('inventory', 'get_inventory_amount', f'location=customer&object_id={id}')['data'].values()
    names = api_call('inventory', 'get_inventory_catalog', f"id={','.join([str(i['inventory_type_id']) for i in data])}")['data'].values()
    return {
        'status': 'success',
        'id': id,
        'data': [
            {
                'id': inventory['id'],
                'name': convert([name for name in names if name['id'] == inventory['catalog_id']][0]['name']),
                'type': {
                    'id': [name for name in names if name['id'] == inventory['catalog_id']][0]['inventory_section_catalog_id'],
                    'name': [category['name'] for category in tmc_categories if category['id'] == [name for name in names if name['id'] == inventory['catalog_id']][0]['inventory_section_catalog_id']][0]
                },
                'category_id': inventory['catalog_id'],
                'amount': inventory['amount'],
                'sn': inventory['serial_number']
            } for inventory in data
        ]
    }

@app.get('/neomobile/documents')
def neomobile_documents(apikey: str, id: int):
    if APIKEY != apikey:
        return JSONResponse({'status': 'fail', 'detail': 'invalid api key'}, status_code=403)
    attachs = list(api_call('attach', 'get', f'object_id={id}&object_type=customer')['data'].values())
    tasks = api_call('task', 'get_list', f'customer_id={id}')['list'].split(',')
    for task in tasks:
        try:
            attachs.extend(api_call('attach', 'get', f'object_id={task}&object_type=task')['data'].values())
        except AttributeError:
            continue
    return {
        'status': 'success',
        'id': id,
        'task_ids': [int(task) for task in tasks],
        'attachs': [
            {
                'id': attach['id'],
                'url': api_call('attach', 'get_file_temporary_link', f'uuid={attach["id"]}')['data'],
                'name': attach['internal_filepath'] if '.' in attach['internal_filepath'] else attach['internal_filepath'] + '.png',
                'extension': attach['internal_filepath'].split('.')[1].lower() if '.' in attach['internal_filepath'] else 'png',
                'created_at': attach['date_add']
            } for attach in attachs
        ]
    }