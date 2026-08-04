def from_polygon(polygon: list[list[float]]) -> list[float]:
    points = polygon[:-1]
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return [sum(lats) / len(lats), sum(lons) / len(lons)]
