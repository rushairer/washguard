import cadquery as cq
from cadquery import exporters
from pathlib import Path

OUT = Path('/mnt/data/washguard_cad_v0.2')

BOARD_W = 20.32
BOARD_H = 20.32
HOLE_EDGE = 2.54
HOLE_SPACING = 15.24
MOUNT_HOLE_D = 3.048
PCB_THICKNESS = 1.575

BASE_W = 42.0
BASE_H = 32.0
BASE_T = 2.4
BASE_CORNER_R = 1.5

BOARD_X0 = 3.0
BOARD_Y0 = (BASE_H - BOARD_H) / 2.0

POST_D = 5.5
POST_H = 2.5
M2_PILOT_D = 1.7
M2_CLEAR_D = 2.3

CABLE_CENTER_Y = BASE_H / 2.0
SADDLE_X0 = 25.0
SADDLE_LEN = 16.2
SADDLE_W = 13.0
SADDLE_H = 1.8
SADDLE_EDGE_R = 1.0
SADDLE_GROOVE_OPENING = 11.0
SADDLE_GROOVE_DEPTH = 0.55

CLAMP_CENTER_X = 34.0
CLAMP_SCREW_SPACING = 18.0
CLAMP_BOSS_D = 5.8
CLAMP_BOSS_H = 2.0

CLAMP_W = 12.0
CLAMP_H = 23.0
CLAMP_T = 3.2
CLAMP_EDGE_CHAMFER = 0.8
CLAMP_GROOVE_OPENING = 11.0
CLAMP_GROOVE_DEPTH = 1.25

hole_centers = [
    (BOARD_X0 + HOLE_EDGE, BOARD_Y0 + HOLE_EDGE),
    (BOARD_X0 + BOARD_W - HOLE_EDGE, BOARD_Y0 + HOLE_EDGE),
    (BOARD_X0 + HOLE_EDGE, BOARD_Y0 + BOARD_H - HOLE_EDGE),
    (BOARD_X0 + BOARD_W - HOLE_EDGE, BOARD_Y0 + BOARD_H - HOLE_EDGE),
]

def triangular_prism_x(x0, length, center_y, z_open, opening_width, depth):
    wp = cq.Workplane('YZ', origin=(x0, 0, 0))
    return (
        wp.moveTo(center_y - opening_width / 2.0, z_open)
        .lineTo(center_y + opening_width / 2.0, z_open)
        .lineTo(center_y, z_open - depth)
        .close()
        .extrude(length)
    )

base = cq.Workplane('XY').box(BASE_W, BASE_H, BASE_T, centered=(False, False, False))
try:
    base = base.edges('|Z').fillet(BASE_CORNER_R)
except Exception:
    pass

for x, y in hole_centers:
    post = (
        cq.Workplane('XY').workplane(offset=BASE_T)
        .center(x, y).circle(POST_D / 2.0).extrude(POST_H)
    )
    base = base.union(post)
    pilot = (
        cq.Workplane('XY').workplane(offset=BASE_T + POST_H)
        .center(x, y).circle(M2_PILOT_D / 2.0)
        .extrude(-(POST_H + 1.3))
    )
    base = base.cut(pilot)

saddle = (
    cq.Workplane('XY').workplane(offset=BASE_T)
    .center(SADDLE_X0 + SADDLE_LEN / 2.0, CABLE_CENTER_Y)
    .box(SADDLE_LEN, SADDLE_W, SADDLE_H, centered=(True, True, False))
)
try:
    saddle = saddle.edges('|Z').fillet(SADDLE_EDGE_R)
except Exception:
    pass
base = base.union(saddle)

saddle_v = triangular_prism_x(
    SADDLE_X0 - 0.2,
    SADDLE_LEN + 0.4,
    CABLE_CENTER_Y,
    BASE_T + SADDLE_H + 0.01,
    SADDLE_GROOVE_OPENING,
    SADDLE_GROOVE_DEPTH,
)
base = base.cut(saddle_v)

clamp_screw_centers = [
    (CLAMP_CENTER_X, CABLE_CENTER_Y - CLAMP_SCREW_SPACING / 2.0),
    (CLAMP_CENTER_X, CABLE_CENTER_Y + CLAMP_SCREW_SPACING / 2.0),
]
for x, y in clamp_screw_centers:
    boss = (
        cq.Workplane('XY').workplane(offset=BASE_T)
        .center(x, y).circle(CLAMP_BOSS_D / 2.0).extrude(CLAMP_BOSS_H)
    )
    base = base.union(boss)
    pilot = (
        cq.Workplane('XY').workplane(offset=BASE_T + CLAMP_BOSS_H)
        .center(x, y).circle(M2_PILOT_D / 2.0)
        .extrude(-(CLAMP_BOSS_H + 1.2))
    )
    base = base.cut(pilot)

clamp = cq.Workplane('XY').box(CLAMP_W, CLAMP_H, CLAMP_T, centered=(True, True, False))
try:
    clamp = clamp.edges().chamfer(CLAMP_EDGE_CHAMFER)
except Exception:
    try:
        clamp = clamp.edges('|Z').chamfer(CLAMP_EDGE_CHAMFER)
        clamp = clamp.edges('>Z').chamfer(0.5)
    except Exception:
        pass

for y in (-CLAMP_SCREW_SPACING / 2.0, CLAMP_SCREW_SPACING / 2.0):
    hole = (
        cq.Workplane('XY').workplane(offset=CLAMP_T + 0.1)
        .center(0, y).circle(M2_CLEAR_D / 2.0)
        .extrude(-(CLAMP_T + 0.2))
    )
    clamp = clamp.cut(hole)

clamp_v = triangular_prism_x(
    -CLAMP_W / 2.0 - 0.2,
    CLAMP_W + 0.4,
    0.0,
    0.01,
    CLAMP_GROOVE_OPENING,
    -CLAMP_GROOVE_DEPTH,
)
clamp = clamp.cut(clamp_v)

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

exporters.export(base, str(OUT / 'WashGuard_ADXL355_Base_V0.2.step'))
exporters.export(base, str(OUT / 'WashGuard_ADXL355_Base_V0.2.stl'), tolerance=0.02, angularTolerance=0.1)
exporters.export(clamp, str(OUT / 'WashGuard_ADXL355_CableClamp_V0.2.step'))
exporters.export(clamp, str(OUT / 'WashGuard_ADXL355_CableClamp_V0.2.stl'), tolerance=0.02, angularTolerance=0.1)
