import cadquery as cq
from cadquery import exporters
from pathlib import Path

OUT = Path("generated")
OUT.mkdir(exist_ok=True)

BOARD_W = 20.32
BOARD_H = 20.32
HOLE_EDGE = 2.54
MOUNT_HOLE_D = 3.048
PCB_THICKNESS = 1.575

BASE_W = 38.0
BASE_H = 32.0
BASE_T = 2.4

BOARD_X0 = 3.0
BOARD_Y0 = (BASE_H - BOARD_H) / 2.0

POST_D = 5.5
POST_H = 2.5
M2_PILOT_D = 1.7
M2_CLEAR_D = 2.2

CABLE_CENTER_Y = BASE_H / 2.0
CABLE_GROOVE_W = 8.0
CABLE_GROOVE_DEPTH = 0.8
CABLE_GROOVE_X0 = BOARD_X0 + BOARD_W - 0.8
CABLE_GROOVE_LEN = BASE_W - CABLE_GROOVE_X0 + 0.5

CLAMP_CENTER_X = 31.5
CLAMP_W = 10.0
CLAMP_H = 14.0
CLAMP_T = 3.0
CLAMP_SCREW_SPACING = 10.0
CLAMP_BOSS_D = 4.8
CLAMP_BOSS_H = 2.0
CLAMP_GROOVE_W = 7.0
CLAMP_GROOVE_DEPTH = 1.5

hole_centers = [
    (BOARD_X0 + HOLE_EDGE, BOARD_Y0 + HOLE_EDGE),
    (BOARD_X0 + BOARD_W - HOLE_EDGE, BOARD_Y0 + HOLE_EDGE),
    (BOARD_X0 + HOLE_EDGE, BOARD_Y0 + BOARD_H - HOLE_EDGE),
    (BOARD_X0 + BOARD_W - HOLE_EDGE, BOARD_Y0 + BOARD_H - HOLE_EDGE),
]

base = cq.Workplane("XY").box(BASE_W, BASE_H, BASE_T, centered=(False, False, False))
base = base.edges("|Z").fillet(1.5)

for x, y in hole_centers:
    post = (
        cq.Workplane("XY").workplane(offset=BASE_T)
        .center(x, y).circle(POST_D / 2).extrude(POST_H)
    )
    base = base.union(post)
    cut = (
        cq.Workplane("XY").workplane(offset=BASE_T + POST_H)
        .center(x, y).circle(M2_PILOT_D / 2).extrude(-(POST_H + 1.4))
    )
    base = base.cut(cut)

groove = (
    cq.Workplane("XY").workplane(offset=BASE_T)
    .center(CABLE_GROOVE_X0 + CABLE_GROOVE_LEN / 2, CABLE_CENTER_Y)
    .rect(CABLE_GROOVE_LEN, CABLE_GROOVE_W)
    .extrude(-CABLE_GROOVE_DEPTH)
)
base = base.cut(groove)

clamp_screw_centers = [
    (CLAMP_CENTER_X, CABLE_CENTER_Y - CLAMP_SCREW_SPACING / 2),
    (CLAMP_CENTER_X, CABLE_CENTER_Y + CLAMP_SCREW_SPACING / 2),
]
for x, y in clamp_screw_centers:
    boss = (
        cq.Workplane("XY").workplane(offset=BASE_T)
        .center(x, y).circle(CLAMP_BOSS_D / 2).extrude(CLAMP_BOSS_H)
    )
    base = base.union(boss)
    cut = (
        cq.Workplane("XY").workplane(offset=BASE_T + CLAMP_BOSS_H)
        .center(x, y).circle(M2_PILOT_D / 2).extrude(-(CLAMP_BOSS_H + 1.4))
    )
    base = base.cut(cut)

clamp = cq.Workplane("XY").box(CLAMP_W, CLAMP_H, CLAMP_T, centered=(True, True, False))
clamp = clamp.edges("|Z").fillet(0.8)
for y in (-CLAMP_SCREW_SPACING / 2, CLAMP_SCREW_SPACING / 2):
    hole = (
        cq.Workplane("XY").workplane(offset=CLAMP_T)
        .center(0, y).circle(M2_CLEAR_D / 2).extrude(-(CLAMP_T + 0.2))
    )
    clamp = clamp.cut(hole)
clamp = clamp.cut(
    cq.Workplane("XY").rect(CLAMP_W + 0.4, CLAMP_GROOVE_W).extrude(CLAMP_GROOVE_DEPTH)
)

exporters.export(base, str(OUT / "WashGuard_ADXL355_Base_V0.1.step"))
exporters.export(base, str(OUT / "WashGuard_ADXL355_Base_V0.1.stl"))
exporters.export(clamp, str(OUT / "WashGuard_ADXL355_CableClamp_V0.1.step"))
exporters.export(clamp, str(OUT / "WashGuard_ADXL355_CableClamp_V0.1.stl"))
