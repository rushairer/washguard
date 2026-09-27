import cadquery as cq
from cadquery import exporters, importers
from pathlib import Path
import json

OUT = Path('/mnt/data/washguard_cad_v0.7')
OUT.mkdir(parents=True, exist_ok=True)

BOARD_W = 20.32
BOARD_H = 20.32
HOLE_EDGE = 2.54
MOUNT_HOLE_D = 3.048
PCB_THICKNESS = 1.575

BASE_W = 44.0
BASE_H = 32.0
BASE_T = 2.4
BASE_CORNER_R = 1.5
ROOT_FILLET_R = 0.8

BOARD_X0 = 3.0
BOARD_Y0 = (BASE_H - BOARD_H) / 2.0

POST_D = 5.5
POST_H = 2.5
POST_ROOT_BLEND_R = 0.8
POST_ROOT_BLEND_H = 1.05
M2_PILOT_D = 1.7
M2_CLEAR_D = 2.3

CABLE_CENTER_Y = BASE_H / 2.0
SADDLE_X0 = 25.0
SADDLE_LEN = 16.2
SADDLE_W = 13.0
SADDLE_H = 2.0
SADDLE_CORNER_R = 1.0
SADDLE_GROOVE_OPENING = 11.0
SADDLE_GROOVE_DEPTH = 0.8
SADDLE_GROOVE_BOTTOM = SADDLE_GROOVE_OPENING - 2 * SADDLE_GROOVE_DEPTH

CLAMP_CENTER_X = 34.0
CLAMP_SCREW_SPACING = 18.0
CLAMP_BOSS_D = 5.8
CLAMP_BOSS_H = 2.0
JUNCTION_FILLET_R = 0.8

CLAMP_W = 12.0
CLAMP_H = 23.0
CLAMP_T = 3.2
CLAMP_EDGE_CHAMFER = 0.8
CLAMP_GROOVE_OPENING = 11.0
CLAMP_GROOVE_DEPTH = 1.25
CLAMP_GROOVE_BOTTOM = CLAMP_GROOVE_OPENING - 2 * CLAMP_GROOVE_DEPTH
CLAMP_CUT_OVERSHOOT = 0.20

hole_centers = [
    (BOARD_X0 + HOLE_EDGE, BOARD_Y0 + HOLE_EDGE),
    (BOARD_X0 + BOARD_W - HOLE_EDGE, BOARD_Y0 + HOLE_EDGE),
    (BOARD_X0 + HOLE_EDGE, BOARD_Y0 + BOARD_H - HOLE_EDGE),
    (BOARD_X0 + BOARD_W - HOLE_EDGE, BOARD_Y0 + BOARD_H - HOLE_EDGE),
]

def trapezoid_prism_x(x0, length, center_y, z_open, opening_width, bottom_width, depth):
    wp = cq.Workplane('YZ', origin=(x0, 0, 0))
    return (
        wp.moveTo(center_y - opening_width / 2.0, z_open)
        .lineTo(center_y + opening_width / 2.0, z_open)
        .lineTo(center_y + bottom_width / 2.0, z_open - depth)
        .lineTo(center_y - bottom_width / 2.0, z_open - depth)
        .close()
        .extrude(length)
    )

def underside_trapezoid_cut_x(
    x0, length, center_y, opening_width_at_surface, bottom_width, depth, overshoot
):
    z_outer = -overshoot
    outer_width = opening_width_at_surface + 2.0 * overshoot
    z_inner = depth
    wp = cq.Workplane('YZ', origin=(x0, 0, 0))
    return (
        wp.moveTo(center_y - outer_width / 2.0, z_outer)
        .lineTo(center_y + outer_width / 2.0, z_outer)
        .lineTo(center_y + bottom_width / 2.0, z_inner)
        .lineTo(center_y - bottom_width / 2.0, z_inner)
        .close()
        .extrude(length)
    )

def wp_from_shape(shape):
    return cq.Workplane('XY').newObject([shape])

def smooth_support_post(cx, cy):
    r = POST_D / 2.0
    R = POST_ROOT_BLEND_R
    z0 = BASE_T
    z_blend_top = z0 + POST_ROOT_BLEND_H
    z_top = z0 + POST_H

    # 单调、切线连续的扩根轮廓：
    # - 在底板处沿水平方向切入；
    # - 半径只会逐渐减小，不会先鼓起再收回；
    # - 在柱身处以竖直切线接入圆柱。
    root_points = [
        (r + 0.62, z0 + 0.03),
        (r + 0.38, z0 + 0.18),
        (r + 0.18, z0 + 0.45),
        (r + 0.05, z0 + 0.76),
        (r, z_blend_top),
    ]

    return (
        cq.Workplane('XZ')
        .moveTo(0.0, z0)
        .lineTo(r + R, z0)
        .spline(
            root_points,
            tangents=[(-1.0, 0.0), (0.0, 1.0)],
            includeCurrent=True,
        )
        .lineTo(r, z_top)
        .lineTo(0.0, z_top)
        .close()
        .revolve(360.0, (0.0, 0.0), (0.0, 1.0))
        .translate((cx, cy, 0.0))
    )

base = cq.Workplane('XY').box(BASE_W, BASE_H, BASE_T, centered=(False, False, False))
base = base.edges('|Z').fillet(BASE_CORNER_R)

saddle = (
    cq.Workplane('XY').workplane(offset=BASE_T)
    .center(SADDLE_X0 + SADDLE_LEN / 2.0, CABLE_CENTER_Y)
    .box(SADDLE_LEN, SADDLE_W, SADDLE_H, centered=(True, True, False))
)
saddle = saddle.edges('|Z').fillet(SADDLE_CORNER_R)

strain_relief = saddle
for y in (
    CABLE_CENTER_Y - CLAMP_SCREW_SPACING / 2.0,
    CABLE_CENTER_Y + CLAMP_SCREW_SPACING / 2.0,
):
    boss = (
        cq.Workplane('XY').workplane(offset=BASE_T)
        .center(CLAMP_CENTER_X, y).circle(CLAMP_BOSS_D / 2.0).extrude(CLAMP_BOSS_H)
    )
    strain_relief = strain_relief.union(boss)

strain_relief = strain_relief.edges('|Z').fillet(JUNCTION_FILLET_R)
base = base.union(strain_relief)

shape = base.val()
root_edges = []
for e in shape.Edges():
    bb = e.BoundingBox()
    if (
        abs(bb.zmin - BASE_T) < 1e-6
        and abs(bb.zmax - BASE_T) < 1e-6
        and bb.xmin > 0.5
        and bb.xmax < BASE_W - 0.5
        and bb.ymin > 0.5
        and bb.ymax < BASE_H - 0.5
    ):
        root_edges.append(e)
if root_edges:
    shape = shape.fillet(ROOT_FILLET_R, root_edges)
base = wp_from_shape(shape)

for x, y in hole_centers:
    base = base.union(smooth_support_post(x, y))

for x, y in hole_centers:
    pilot = (
        cq.Workplane('XY').workplane(offset=BASE_T + POST_H + 0.2)
        .center(x, y).circle(M2_PILOT_D / 2.0)
        .extrude(-(POST_H + 1.5))
    )
    base = base.cut(pilot)

saddle_groove = trapezoid_prism_x(
    SADDLE_X0 - 0.2,
    SADDLE_LEN + 0.4,
    CABLE_CENTER_Y,
    BASE_T + SADDLE_H + 0.01,
    SADDLE_GROOVE_OPENING,
    SADDLE_GROOVE_BOTTOM,
    SADDLE_GROOVE_DEPTH,
)
base = base.cut(saddle_groove)

for x, y in [
    (CLAMP_CENTER_X, CABLE_CENTER_Y - CLAMP_SCREW_SPACING / 2.0),
    (CLAMP_CENTER_X, CABLE_CENTER_Y + CLAMP_SCREW_SPACING / 2.0),
]:
    pilot = (
        cq.Workplane('XY').workplane(offset=BASE_T + CLAMP_BOSS_H + 0.2)
        .center(x, y).circle(M2_PILOT_D / 2.0)
        .extrude(-(CLAMP_BOSS_H + 1.5))
    )
    base = base.cut(pilot)

clamp_blank = cq.Workplane('XY').box(CLAMP_W, CLAMP_H, CLAMP_T, centered=(True, True, False))
try:
    clamp_blank = clamp_blank.edges().chamfer(CLAMP_EDGE_CHAMFER)
except Exception:
    clamp_blank = clamp_blank.edges('|Z').chamfer(CLAMP_EDGE_CHAMFER)
    clamp_blank = clamp_blank.edges('>Z').chamfer(0.5)

clamp_groove = underside_trapezoid_cut_x(
    -CLAMP_W / 2.0 - 0.2,
    CLAMP_W + 0.4,
    0.0,
    CLAMP_GROOVE_OPENING,
    CLAMP_GROOVE_BOTTOM,
    CLAMP_GROOVE_DEPTH,
    CLAMP_CUT_OVERSHOOT,
)
clamp = clamp_blank.cut(clamp_groove)

for y in (-CLAMP_SCREW_SPACING / 2.0, CLAMP_SCREW_SPACING / 2.0):
    hole = (
        cq.Workplane('XY').workplane(offset=CLAMP_T + 0.2)
        .center(0, y).circle(M2_CLEAR_D / 2.0)
        .extrude(-(CLAMP_T + 0.4))
    )
    clamp = clamp.cut(hole)

pcb = (
    cq.Workplane('XY').workplane(offset=BASE_T + POST_H)
    .center(BOARD_X0 + BOARD_W / 2.0, BOARD_Y0 + BOARD_H / 2.0)
    .box(BOARD_W, BOARD_H, PCB_THICKNESS, centered=(True, True, False))
)
for x, y in hole_centers:
    h = (
        cq.Workplane('XY').workplane(offset=BASE_T + POST_H + PCB_THICKNESS)
        .center(x, y).circle(MOUNT_HOLE_D / 2.0)
        .extrude(-(PCB_THICKNESS + 0.1))
    )
    pcb = pcb.cut(h)

base_step = OUT / 'WashGuard_ADXL355_Base_V0.7.step'
base_stl = OUT / 'WashGuard_ADXL355_Base_V0.7.stl'
clamp_step = OUT / 'WashGuard_ADXL355_CableClamp_V0.7.step'
clamp_stl = OUT / 'WashGuard_ADXL355_CableClamp_V0.7.stl'

exporters.export(base, str(base_step))
exporters.export(base, str(base_stl), tolerance=0.02, angularTolerance=0.1)
exporters.export(clamp, str(clamp_step))
exporters.export(clamp, str(clamp_stl), tolerance=0.02, angularTolerance=0.1)
