# -*- coding: utf-8 -*-
"""
check_setbacks.py — проверка посадки дома на участке:
  1) площадь и корректность контура участка;
  2) дом внутри контура;
  3) минимальное расстояние от дома до границы >= нормативного отступа.

Правь данные в секции ДАННЫЕ и запускай на любом этапе проектирования:
    python check_setbacks.py
Код возврата 1 при нарушениях — удобно вешать в CI или на pre-commit.
"""
import math
import sys

# ---------------- ДАННЫЕ (локальные метры, X на восток, Y на север) ----------------
# Контур участка — синтетический пример ("почти прямоугольник" ~40x30 с GPS-шумом).
PLOT = [(-20.0, -15.0), (19.5, -16.0), (21.0, 14.8), (-19.0, 14.5)]
# Дом: прямоугольник 12x9, отступы 5 м от юга и запада (стены параллельны осям).
HOUSE = [(-15.0, -10.0), (-3.0, -10.0), (-3.0, -1.0), (-15.0, -1.0)]
# Прочие объекты (колодец, септик, бытовка) — добавь по аналогии.
OBJECTS = {"колодец": (5.0, 2.0), "септик": (-12.0, 8.0)}
MIN_SETBACK = 3.0   # нормативный отступ дома от границ, м (сверь с ПЗЗ!)
TARGET_AREA = 1200  # кадастровая площадь участка, м2 (для сверки)
TOL_AREA = 0.02     # допуск расхождения площади, доля


# ---------------- ГЕОМЕТРИЯ ----------------
def polygon_area(pts):
    s, n = 0.0, len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def point_in_poly(pt, poly):
    """Луч-тест: точка внутри полигона."""
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xin > x:
                inside = not inside
    return inside


def dist_point_segment(pt, a, b):
    """Расстояние от точки до отрезка AB."""
    px, py = pt
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0.0:
        return math.dist(pt, a)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.dist(pt, (ax + t * dx, ay + t * dy))


def min_dist_to_boundary(poly_obj, poly_border):
    """Минимальное расстояние от всех рёбер объекта до всех рёбер границы + найденное ребро."""
    best = (float("inf"), None, None)
    n, m = len(poly_obj), len(poly_border)
    for i in range(n):
        a1, a2 = poly_obj[i], poly_obj[(i + 1) % n]
        for j in range(m):
            b1, b2 = poly_border[j], poly_border[(j + 1) % m]
            for pt in (a1, a2):
                d = dist_point_segment(pt, b1, b2)
                if d < best[0]:
                    best = (d, pt, (b1, b2))
    return best


# ---------------- ПРОВЕРКИ ----------------
def main():
    failures = 0

    area = polygon_area(PLOT)
    dev = abs(area - TARGET_AREA) / TARGET_AREA
    ok = dev <= TOL_AREA
    failures += not ok
    print("[%s] Площадь участка: %.1f м2 (кадастровая %.0f, отклонение %.1f%%, допуск %.0f%%)"
          % ("OK" if ok else "!!!", area, TARGET_AREA, dev * 100, TOL_AREA * 100))

    ok = point_in_poly(HOUSE[0], PLOT) and point_in_poly(HOUSE[2], PLOT)
    failures += not ok
    print("[%s] Дом внутри контура участка" % ("OK" if ok else "!!!"))

    d, pt, edge = min_dist_to_boundary(HOUSE, PLOT)
    ok = d >= MIN_SETBACK
    failures += not ok
    print("[%s] Мин. отступ дома до границы: %.2f м (норматив %.1f м); ближайшая точка дома %s"
          % ("OK" if ok else "!!!", d, MIN_SETBACK, pt))

    for name, obj_pt in OBJECTS.items():
        ok = point_in_poly(obj_pt, PLOT)
        failures += not ok
        print("[%s] Объект '%s' внутри контура" % ("OK" if ok else "!!!", name))

    print("---")
    if failures:
        print("ИТОГ: %d нарушений — посадку доработать." % failures)
        sys.exit(1)
    print("ИТОГ: все проверки пройдены.")


if __name__ == "__main__":
    main()
