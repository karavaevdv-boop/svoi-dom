# -*- coding: utf-8 -*-
"""
coords_to_meters.py — перевод WGS84-координат границы участка в локальные метры,
площадь контура (формула Гаусса) и длины сторон.

Метод: equirectangular-проекция вокруг центроида. На размерах участка
(десятки-сотни метров) погрешность ничтожна.

Использование: впиши свои точки в POINTS (широта, долгота), запусти:
    python coords_to_meters.py
Точки можно в любом порядке — контур упорядочится сам.
"""
import math

M_LAT = 111132.0     # метров в градусе широты
M_LON_EQ = 111321.0  # метров в градусе долготы на экваторе

# ПРИМЕР (синтетический): "почти прямоугольник" ~40x30 м с GPS-шумом ~1 м.
# Замени на свои точки (лучше из выписки ЕГРН).
POINTS = [
    (56.4998650, 37.4996745),
    (56.4998560, 37.5003174),
    (56.5001332, 37.5003418),
    (56.5001304, 37.4996907),
]


def to_local(pts):
    """WGS84 (lat, lon) -> локальные метры (X на восток, Y на север), origin = центроид."""
    lat0 = sum(p[0] for p in pts) / len(pts)
    lon0 = sum(p[1] for p in pts) / len(pts)
    m_lon = M_LON_EQ * math.cos(math.radians(lat0))
    return [((lon - lon0) * m_lon, (lat - lat0) * M_LAT) for lat, lon in pts]


def order(pts):
    """Упорядочить точки контура по полярному углу вокруг центроида (замкнутый полигон)."""
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    return sorted(pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


def polygon_area(pts):
    """Площадь полигона (формула Гаусса), м2."""
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def side_lengths(pts):
    n = len(pts)
    return [math.dist(pts[i], pts[(i + 1) % n]) for i in range(n)]


def main():
    loc = order(to_local(POINTS))
    area = polygon_area(loc)
    sides = side_lengths(loc)
    print("Точки в локальных метрах (origin = центроид):")
    for i, (x, y) in enumerate(loc, 1):
        print("  T%d: x=%8.2f  y=%8.2f" % (i, x, y))
    print("Стороны: " + ", ".join("%.1f м" % s for s in sides))
    print("Площадь контура: %.1f м2" % area)
    print("Сверь с кадастровой площадью: расхождение до 1-2% — норма (допуск обмера).")
    # самопроверка на синтетическом примере: ожидаем ~1200 м2
    assert 1150 < area < 1250, "самопроверка примера не прошла: %.1f" % area
    print("Самопроверка примера: OK")


if __name__ == "__main__":
    main()
