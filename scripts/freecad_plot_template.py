# -*- coding: utf-8 -*-
"""
freecad_plot_template.py — шаблон параметрической сборки модели участка в FreeCAD.

Запуск: в FreeCAD (макрос или через MCP execute_code). Головной вариант проверен
на реальном проекте; здесь шаблон с СИНТЕТИЧЕСКИМИ точками — замени на свои
(координаты своего участка в публичные репозитории не выкладывай).

Структура сборки:
  1) WGS84 -> локальные метры (equirectangular, origin = центроид);
  2) упорядочивание точек контура по полярному углу;
  3) "выпрямленный" прямоугольник участка, прижатый к первой стороне;
  4) посадка дома в локальной системе координат go(угол, a, b);
  5) бытовка/ворота/колодец/септик + подписи + север;
  6) автопроверка в конце: площадь, отступы, попадание объектов.
"""
import FreeCAD as App
import Part
import math
import Draft

DOC = "Uchastok"

# ---------------- ДАННЫЕ (замени на свои; лучше из выписки ЕГРН) ----------------
PLOT_GEO = [  # точки границы (широта, долгота) — синтетический пример ~40x30 м
    (56.4998650, 37.4996745),
    (56.4998560, 37.5003174),
    (56.5001332, 37.5003418),
    (56.5001304, 37.4996907),
]
SIDE_LONG, SIDE_SHORT = 40.0, 30.0          # выпрямленные стороны участка, м
HOUSE_SETBACK_S, HOUSE_SETBACK_W = 5.0, 5.0  # отступы дома от юга/запада, м
HOUSE_L, HOUSE_D = 12.0, 9.0                 # длина вдоль юга / глубина внутрь, м
BYT_S, BYT_W, BYT_L, BYT_D = 2.0, 2.0, 6.0, 2.4  # бытовка: отступы и размеры
WELL_PT = (10.0, 3.0)   # колодец (локальные s,t относительно ЮЗ угла), м
LOS_PT = (-12.0, 8.0)   # септик/ЛОС, м
GATE = (3.5, 7.0)       # ворота: начало и ширина вдоль южной границы, м

M_LAT = 111132.0
TARGET_AREA = SIDE_LONG * SIDE_SHORT

try:
    App.closeDocument(DOC)
except Exception:
    pass
doc = App.newDocument(DOC)

# --- 1) проекция и упорядочивание ---
lat0 = sum(p[0] for p in PLOT_GEO) / len(PLOT_GEO)
lon0 = sum(p[1] for p in PLOT_GEO) / len(PLOT_GEO)
M_LON = 111321.0 * math.cos(math.radians(lat0))


def proj(pts):
    return [((lon - lon0) * M_LON, (lat - lat0) * M_LAT) for lat, lon in pts]


def order(pts):
    cx = sum(x for x, _ in pts) / len(pts)
    cy = sum(y for _, y in pts) / len(pts)
    return sorted(pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


loc = order(proj(PLOT_GEO))
T1, T2 = loc[0], loc[1]  # первая сторона = "южная"

# --- 2) локальная система координат: go(угол, a, b) ---
side = math.dist(T1, T2)
ex, ey = (T2[0] - T1[0]) / side, (T2[1] - T1[1]) / side
nx, ny = -ey, ex  # нормаль внутрь


def go(p, a, b):
    """a метров вдоль южной стороны, b метров внутрь участка."""
    return (p[0] + a * ex + b * nx, p[1] + a * ey + b * ny)


A = T1
rect = [A, go(A, SIDE_LONG, 0), go(A, SIDE_LONG, SIDE_SHORT), go(A, 0, SIDE_SHORT)]


def st(p):
    return ((p[0] - A[0]) * ex + (p[1] - A[1]) * ey,
            (p[0] - A[0]) * nx + (p[1] - A[1]) * ny)


def inside(p):
    s, t = st(p)
    return 0 <= s <= SIDE_LONG and 0 <= t <= SIDE_SHORT


# --- стиль: безопасно и в GUI, и в headless (MCP) ---
def vstyle(obj, color=None, line=None, width=None):
    v = getattr(obj, "ViewObject", None)
    if v is None:
        return
    try:
        if color:
            v.ShapeColor = color
        if line:
            v.LineColor = line
        if width:
            v.LineWidth = width
    except Exception:
        pass


def add_poly(name, pts, z=0.0, closed=True, color=None, width=None):
    vecs = [App.Vector(x, y, z) for x, y in pts]
    shape = Part.makePolygon(vecs + [vecs[0]] if closed else vecs)
    o = doc.addObject("Part::Feature", name)
    o.Shape = shape
    vstyle(o, line=color, width=width)
    return o, shape


def add_prism(name, pts, h, color):
    vecs = [App.Vector(x, y, 0.0) for x, y in pts]
    face = Part.Face(Part.makePolygon(vecs + [vecs[0]]))
    o = doc.addObject("Part::Feature", name)
    o.Shape = face.extrude(App.Vector(0, 0, h))
    vstyle(o, color=color)
    return o


def add_point_marker(name, x, y, r=0.4, h=1.2, color=(0.85, 0.15, 0.10)):
    c = doc.addObject("Part::Cylinder", name)
    c.Radius, c.Height = r, h
    c.Placement.Base = App.Vector(x, y, 0)
    vstyle(c, color=color)
    return c


# --- 3) участок ---
_, plot_shape = add_poly("UCH_Boundary", rect, color=(0.55, 0.15, 0.10), width=3)
face = Part.Face(plot_shape)
fo = doc.addObject("Part::Feature", "UCH_Plot")
fo.Shape = face
vstyle(fo, color=(0.82, 0.88, 0.70))
for i, (x, y) in enumerate(rect):
    add_point_marker("UCH_Point%d" % (i + 1), x, y)

# --- 4) дом ---
house = [go(A, HOUSE_SETBACK_W, HOUSE_SETBACK_S),
         go(A, HOUSE_SETBACK_W + HOUSE_L, HOUSE_SETBACK_S),
         go(A, HOUSE_SETBACK_W + HOUSE_L, HOUSE_SETBACK_S + HOUSE_D),
         go(A, HOUSE_SETBACK_W, HOUSE_SETBACK_S + HOUSE_D)]
add_prism("DOM_House", house, 3.0, (0.62, 0.62, 0.66))

# --- 5) бытовка, ворота, колодец, септик ---
byt = [go(A, BYT_W, SIDE_SHORT - BYT_S - BYT_L),
       go(A, BYT_W + BYT_D, SIDE_SHORT - BYT_S - BYT_L),
       go(A, BYT_W + BYT_D, SIDE_SHORT - BYT_S),
       go(A, BYT_W, SIDE_SHORT - BYT_S)]
add_prism("BORN_Bytovka", byt, 2.5, (0.78, 0.62, 0.35))

v1, v2 = go(A, GATE[0], 0.0), go(A, GATE[0] + GATE[1], 0.0)
add_poly("VOROTA_Gate", [v1, v2], z=0.2, closed=False, color=(0.85, 0.45, 0.05), width=4)

wx, wy = go(A, WELL_PT[0], WELL_PT[1])
add_point_marker("WELL_Kolodec", wx, wy, 0.45, 1.0, (0.30, 0.55, 0.85))
lx, ly = go(A, LOS_PT[0], LOS_PT[1])
add_point_marker("LOS_Septic", lx, ly, 0.6, 1.3, (0.45, 0.50, 0.30))

# --- подписи и север ---
def txt(s, x, y, z, size=1.2):
    try:
        t = Draft.make_text(s, App.Vector(x, y, z))
        v = getattr(t, "ViewObject", None)
        if v:
            v.FontSize = size
        return t
    except Exception:
        pass


dcx = (house[0][0] + house[2][0]) / 2
dcy = (house[0][1] + house[2][1]) / 2
txt("DOM %gx%g (%gx%g ot YuZ)" % (HOUSE_L, HOUSE_D, HOUSE_SETBACK_W, HOUSE_SETBACK_S),
    dcx, dcy, 3.4)
txt("N", 0, SIDE_SHORT * 0.85, 0.4, 2.0)
add_poly("N_Arrow", [(0, SIDE_SHORT * 0.75), (0, SIDE_SHORT * 0.85)],
         z=0, closed=False, color=(0.1, 0.1, 0.1), width=2)

doc.recompute()
doc.saveAs("uchastok.FCStd")  # относительный путь, чтобы скрипт работал в любой папке

# --- 6) автопроверка: "готово" только после контрольного вывода ---
print("BUILD OK | objects:", len(doc.Objects))
print("Plot area: %.1f m2 (target %.0f)" % (face.Area, TARGET_AREA))
print("House setbacks: S %.1f m, W %.1f m | inside: %s"
      % (HOUSE_SETBACK_S, HOUSE_SETBACK_W, all(inside(p) for p in house)))
bst = [st(p) for p in byt]
print("Bytovka setbacks: W %.2f m, N %.2f m | inside: %s"
      % (min(s for s, _ in bst), SIDE_SHORT - max(t for _, t in bst),
         all(inside(p) for p in byt)))
print("Well inside:", inside(go(A, *WELL_PT)), "| Septic inside:", inside(go(A, *LOS_PT)))
