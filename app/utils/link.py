def make_tgis_link(lat: float, lon: float):
    return f"http://2gis.kg/geo/{lon},{lat}"


def make_neo_link(lat: float, lon: float):
    f"https://us.neotelecom.kg/map/show?lat={lat}&lon={lon}&zoom=18&is_show_center_marker=1@{lat},{lon},18z"
