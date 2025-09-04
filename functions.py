from typing import Literal
from html import unescape

def convert(data: str) -> str:
    return unescape(data)

def parse_agreement(agreement: str) -> int | None:
    if agreement:
        if agreement.isdigit():
            return int(agreement)
    return None

def cut_sn(data: str) -> str:
    if data.find('(') != -1:
        return data[:data.find(' (')]
    return data

def get_sn(data: str) -> None | str:
    if data.endswith('()'): return # if sn is empty
    if '(' in data:
        return data.split('(')[1].rstrip(')')

def str_status(data: int) -> Literal['Отключен'] | Literal['Пауза'] | Literal['Активен'] | Literal['Неизвестен']:
    match data:
        case 0:
            return 'Отключен'
        case 1:
            return 'Пауза'
        case 2:
            return 'Активен'
        case _:
            return 'Неизвестен'

def neo_coord(lat: float, lon: float) -> str:
    return f'https://us.neotelecom.kg/map/show?lat={lat}&lon={lon}&zoom=18&is_show_center_marker=1@{lat},{lon},18z'

def twogis_coord(lat: float, lon: float) -> str:
    return f'http://2gis.kg/geo/{lon},{lat}'