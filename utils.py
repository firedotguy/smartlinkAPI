"""Simple utils like parse agreement or build 2 gis link"""
from datetime import datetime as dt
from functools import reduce

from urllib.parse import urljoin

from config import ATTACH_URL


def parse_agreement(agreement: str | None) -> int | None:
    """
    Parse agreement string into an integer if it contains only digits.

    Args:
        agreement (str | None): Agreement value as a string.

    Returns:
        int|None: Parsed integer if valid, otherwise None.
    """
    if agreement:
        if agreement.isdigit():
            return int(agreement)
    return None

def remove_sn(data: str) -> str:
    """
    Extract the name part from a string formatted like 'name (sn)'.

    If parentheses are present, the substring before them is returned.
    Otherwise, the original string is returned.

    Args:
        data (str): Input string containing a name and an optional value in parentheses.

    Returns:
        str: Extracted name without the parentheses part.
    """
    if '(' in data:
        return data.rsplit('(', maxsplit=1)[0].strip()
    return data

def extract_sn(data: str) -> None | str:
    """
    Extract serial number from a string in the format 'name(sn)'.

    If the string ends with '()', it is treated as empty and None is returned.
    Otherwise, the substring inside parentheses is returned.

    Args:
        data (str): Input string containing a name and an optional serial number.

    Returns:
        str | None: Extracted serial number, or None if not found.
    """
    if data.endswith('()'):
        return # if sn is empty
    if '(' in data:
        return data.rsplit('(', maxsplit=1)[-1].rstrip().rstrip(')')

def status_to_str(status: int) -> str:
    """
    Convert numeric status code to human-readable text.

    Args:
        status (int): Status code (0 = off, 1 = pause, 2 = active).

    Returns:
        str: Text description of the status.
    """
    match status:
        case 0:
            return 'Отключен'
        case 1:
            return 'Пауза'
        case 2:
            return 'Активен'
        case _:
            return 'Неизвестен'

def list_to_str(data: list) -> str:
    """
    Join a list of strings into a single comma-separated string.

    Args:
        data (list): List of string elements.

    Returns:
        str: Comma-separated string.
    """
    return ','.join(map(str, data))

def str_to_list(data: str) -> list:
    """
    Convert a comma-separated string into a list of trimmed strings.

    Args:
        data (str): Input string with items separated by commas.

    Returns:
        list[str]: List of items without surrounding spaces.
    """
    return [item.strip() for item in data.split(",") if item.strip()]

def to_neo_link(lat: float, lon: float) -> str:
    """
    Build a NeoTelecom map link from latitude and longitude.

    Args:
        lat (float): Latitude coordinate.
        lon (float): Longitude coordinate.

    Returns:
        str: URL to the NeoTelecom map for the given coordinates.
    """
    return f'https://us.neotelecom.kg/map/show?lat={lat}&lon={lon}&zoom=18&is_show_center_marker=1\
@{lat},{lon},18z'

def to_2gis_link(lat: float, lon: float) -> str:
    """
    Build a 2GIS map link from latitude and longitude.

    Args:
        lat (float): Latitude coordinate.
        lon (float): Longitude coordinate.

    Returns:
        str: URL to the 2GIS map for the given coordinates.
    """
    return f'http://2gis.kg/geo/{lon},{lat}'

def normalize_items(raw: dict) -> list:
    """Convert 'data' field to a list.

    If 'data' is a dict with digit keys, return its values as a list.
    Otherwise, return ['data'] wrapped in a list.

    Args:
        raw (dict): Dictionary that may contain the 'data' field.

    Returns:
        list: Normalized list of data items.
    """
    data = raw.get('data')
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if all([isinstance(item, dict) for item in list(data.values())]):
        return data.values()
    return [data]

def get_attach_url(path: str) -> str:
    """
    Build full attachment URL by joining base and relative path.

    Args:
        path (str): Relative path to the attachment.

    Returns:
        str: Full URL to the attachment.
    """
    return urljoin(ATTACH_URL, path)

def get_current_time() -> str:
    """
    Get the current local time formatted as 'YYYY.MM.DD HH:MM:SS'.

    Returns:
        str: Current time string.
    """
    return dt.now().strftime("%Y.%m.%d %H:%M:%S")

def format_mac(mac: str | None) -> str | None:
    """
    Format MAC address (insert ":" between every 2 symbols)

    Args:
        mac (str | None): MAC address without ":"

    Returns:
        str | None: Formatted MAC with ":"
    """
    if mac is None:
        return
    return ':'.join(mac.replace('-', '')[i:i + 2] for i in range(0, len(mac.replace('-', '')), 2))

def get_coordinates(polygon: list[list[float]] | None) -> list[float] | None:
    if not polygon:
        return None
    points = polygon[:-1]
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return [sum(lats) / len(lats), sum(lons) / len(lons)]

def get_box_map_link(coords: list[float] | None, box_id: int) -> str | None:
    if coords is None:
        return None
    return f'https://us.neotelecom.kg/map/show?opt_wh=1&by_building={box_id}&is_show_center_marker=1@{coords[0]},{coords[1]},18z'