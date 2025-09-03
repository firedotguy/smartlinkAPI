def convert(data: str):
    return data.replace('&#047;', '/').replace('&#037;', '%').replace('&#035;', '#')

def parse_agreement(agreement):
    if agreement:
        if agreement.isdigit():
            return int(agreement)
    return None

def cut_sn(data: str):
    if data.find('(') != -1:
        return data[:data.find(' (')]
    return data

def get_sn(data: str):
    if '(' in data:
        return data[data.find(' (') + 2:].rstrip(')')

def str_status(data: int):
    status = 'Неизвестен'
    if data == 2:
        status = 'Активен'
    elif data == 1:
        status = 'Пауза'
    elif data == 0:
        status = 'Отключен'
    return status

def neo_coord(lat: float, lon: float):
    return f'https://us.neotelecom.kg/map/show?lat={lat}&lon={lon}&zoom=18&is_show_center_marker=1@{lat},{lon},18z'

def twogis_coord(lat: float, lon: float):
    return f'http://2gis.kg/geo/{lon},{lat}'