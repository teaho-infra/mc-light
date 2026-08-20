"""生成 mc-light 的显示器侧贴 3D 打印模型。

输出 STL(写到本脚本同目录):
  mc_light_monitor_back.stl              -- 后壳:贴屏平背 + XIAO 腔 + 底部 USB-C 开口
  mc_light_monitor_front_red.stl         -- 多色前盖红色半透明区域
  mc_light_monitor_front_M.stl           -- 多色前盖黄色半透明 M 区域
  mc_light_monitor_front_assembled.stl   -- 前盖红黄区域装配预览
  mc_light_monitor_assembled.stl         -- 整体装配预览

所有尺寸单位 mm,集中在参数区,按需修改后重跑即可。
运行:python3 hardware/generate_m_shell.py
"""
import os

import numpy as np
import trimesh
from shapely.affinity import translate as shp_translate
from shapely.geometry import LineString, MultiPolygon, box as shp_box
from shapely.ops import unary_union

# ----------------------------- 参数区 -----------------------------
BOX_W = 38.0
BOX_H = 38.0
BOX_D = 14.0
FRONT_T = 1.2
BACK_D = BOX_D - FRONT_T
WALL_T = 2.0
PRESS_CLEAR = 0.35
LIP_T = 1.0
LIP_D = 1.2

XIAO_W = 17.8
XIAO_H = 21.0
BOARD_POCKET_W = XIAO_W + 1.4
BOARD_POCKET_H = XIAO_H + 1.4
BOARD_RAIL_T = 1.0
BOARD_RAIL_H = 1.2

USB_OPEN_W = 13.5
USB_OPEN_H = 8.5
USB_OPEN_D = BACK_D + 0.6

M_WIDTH = 24.0
ARCH_R = M_WIDTH / 4.0
LEG_H = 12.0
M_HEIGHT = LEG_H + ARCH_R
CURVE_STEPS = 120

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE = "manifold"


def largest(poly):
    """buffer 后若变成 MultiPolygon,取面积最大的那块。"""
    if isinstance(poly, MultiPolygon):
        return max(poly.geoms, key=lambda g: g.area)
    return poly


def make_box(extents, center):
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    return mesh


def m_polygon(width=M_WIDTH):
    """返回居中的麦当劳风格镂空 M 多边形,位于 XY 平面。"""
    scale = width / M_WIDTH
    stroke_w = 3.0 * scale
    left_x = stroke_w / 2.0
    mid_x = width / 2.0
    right_x = width - stroke_w / 2.0
    peak_y = 20.0 * scale
    outer_join_y = 4.8 * scale
    center_join_y = 7.2 * scale
    center_foot_y = 2.9 * scale
    left_peak_x = width * 0.285
    right_peak_x = width * 0.715

    def cubic_points(p0, p1, p2, p3, steps):
        ts = np.linspace(0.0, 1.0, steps)
        pts = []
        for t in ts:
            omt = 1.0 - t
            x = (
                omt**3 * p0[0]
                + 3 * omt**2 * t * p1[0]
                + 3 * omt * t**2 * p2[0]
                + t**3 * p3[0]
            )
            y = (
                omt**3 * p0[1]
                + 3 * omt**2 * t * p1[1]
                + 3 * omt * t**2 * p2[1]
                + t**3 * p3[1]
            )
            pts.append((float(x), float(y)))
        return pts

    def arch_path(start_x, peak_x, end_x):
        if start_x < end_x:
            up = cubic_points(
                (start_x, outer_join_y),
                (start_x + width * 0.035, outer_join_y + 3.0 * scale),
                (peak_x - width * 0.095, peak_y),
                (peak_x, peak_y),
                CURVE_STEPS // 4,
            )
            down = cubic_points(
                (peak_x, peak_y),
                (peak_x + width * 0.115, peak_y),
                (end_x - width * 0.075, center_join_y),
                (end_x, center_join_y),
                CURVE_STEPS // 4,
            )[1:]
        else:
            up = cubic_points(
                (start_x, center_join_y),
                (start_x + width * 0.075, center_join_y),
                (peak_x - width * 0.115, peak_y),
                (peak_x, peak_y),
                CURVE_STEPS // 4,
            )
            down = cubic_points(
                (peak_x, peak_y),
                (peak_x + width * 0.095, peak_y),
                (end_x - width * 0.035, outer_join_y + 3.0 * scale),
                (end_x, outer_join_y),
                CURVE_STEPS // 4,
            )[1:]
        return up + down

    strokes = unary_union([
        LineString(
            [(left_x, 0.0), (left_x, outer_join_y)]
            + arch_path(left_x, left_peak_x, mid_x)
        ),
        LineString([(mid_x, center_foot_y), (mid_x, center_join_y)]),
        LineString(
            arch_path(mid_x, right_peak_x, right_x)
            + [(right_x, outer_join_y), (right_x, 0.0)]
        ),
    ])
    poly = largest(strokes.buffer(stroke_w / 2.0, cap_style=2, join_style=1, quad_segs=24))
    min_x, min_y, max_x, max_y = poly.bounds
    return shp_translate(
        poly,
        xoff=-(min_x + max_x) / 2.0,
        yoff=-(min_y + max_y) / 2.0,
    )


def build_front_parts():
    """返回红色背景区域和黄色 M 区域;两者 z 范围完全一致,正面齐平。"""
    face = shp_box(-BOX_W / 2.0, -BOX_H / 2.0, BOX_W / 2.0, BOX_H / 2.0)
    m_mark = m_polygon()
    red_area = face.difference(m_mark)

    red = trimesh.creation.extrude_polygon(red_area, height=FRONT_T)
    yellow = trimesh.creation.extrude_polygon(m_mark, height=FRONT_T)
    return red, yellow


def build_front_assembled():
    red, yellow = build_front_parts()
    return trimesh.util.concatenate([red, yellow])


def build_back_shell():
    """后壳:背面平整,正面开口,底部 USB-C 开口,内部有 XIAO 限位结构。"""
    outer = make_box([BOX_W, BOX_H, BACK_D], [0, 0, BACK_D / 2.0])
    inner = make_box(
        [BOX_W - 2 * WALL_T, BOX_H - 2 * WALL_T, BACK_D - WALL_T],
        [0, 0, WALL_T + (BACK_D - WALL_T) / 2.0],
    )
    usb_cut = make_box(
        [USB_OPEN_W, WALL_T * 3.0, USB_OPEN_H],
        [0, -BOX_H / 2.0, USB_OPEN_H / 2.0],
    )
    shell = trimesh.boolean.difference([outer, inner, usb_cut], engine=ENGINE)

    # 限位筋:贴在内腔后壁上,板子长边沿 Y(竖直),USB-C 端朝 -Y(下)。
    # rail_z 取 WALL_T + BOARD_RAIL_H/2,使筋落在盒内 z∈[WALL_T, WALL_T+BOARD_RAIL_H],
    # 不凸出后壳前口( BACK_D )。
    rail_y_gap = BOARD_POCKET_W / 2.0 + BOARD_RAIL_T / 2.0
    rail_z = WALL_T + BOARD_RAIL_H / 2.0
    left_rail = make_box(
        [BOARD_RAIL_T, BOARD_POCKET_H, BOARD_RAIL_H],
        [-rail_y_gap, 0, rail_z],
    )
    right_rail = make_box(
        [BOARD_RAIL_T, BOARD_POCKET_H, BOARD_RAIL_H],
        [rail_y_gap, 0, rail_z],
    )
    bottom_stop = make_box(
        [BOARD_POCKET_W + 2 * BOARD_RAIL_T, BOARD_RAIL_T, BOARD_RAIL_H],
        [0, -BOARD_POCKET_H / 2.0, rail_z],
    )
    return trimesh.util.concatenate([shell, left_rail, right_rail, bottom_stop])


def build_monitor_assembled():
    back = build_back_shell()
    front = build_front_assembled()
    front.apply_translation([0, 0, BACK_D])
    return trimesh.util.concatenate([back, front])


OUTPUTS = [
    ("mc_light_monitor_back.stl", build_back_shell),
    ("mc_light_monitor_front_red.stl", lambda: build_front_parts()[0]),
    ("mc_light_monitor_front_M.stl", lambda: build_front_parts()[1]),
    ("mc_light_monitor_front_assembled.stl", build_front_assembled),
    ("mc_light_monitor_assembled.stl", build_monitor_assembled),
]


def main():
    for name, builder in OUTPUTS:
        mesh = builder()
        path = os.path.join(OUT_DIR, name)
        mesh.export(path)
        wt = getattr(mesh, "is_watertight", None)
        print(
            f"{name}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces, "
            f"watertight={wt}"
        )

    print("完成。后壳单独打印;前盖红色区域和黄色 M 区域作为多色同层前盖合并打印。")


if __name__ == "__main__":
    main()
