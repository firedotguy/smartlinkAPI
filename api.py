from requests import get
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from config import api_url as api

disable_warnings(InsecureRequestWarning)

def api_call(cat: str, action: str, data: str = '') -> dict:
    return get(f'{api}{cat}&action={action}&{data}', verify=False).json()

def set_additional_data(category, field, id, value):
    api_call('additional_data', 'change_value', f'cat_id={category}&field_id={field}&object_id={id}&value={value}')