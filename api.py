"""Module for connection to UserSide"""
from requests import get
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from config import API_URL as api

disable_warnings(InsecureRequestWarning)

def api_call(cat: str, action: str, data: str = '', timeout=15) -> dict:
    """Base UserSide API call

    Args:
        cat (str): category
        action (str): action
        data (str, optional): query parameters separated with &. Defaults to ''.

    Returns:
        dict: API result
    TODO: provide data using query params instead of one string
    """
    return get(f'{api}{cat}&action={action}&{data}', verify=False, timeout=timeout).json()

def set_additional_data(category, field, _id, value):
    """Set additional data value"""
    api_call('additional_data', 'change_value', f'cat_id={category}&field_id={field}&object_id=\
{_id}&value={value}')
