"""生成 mc-light 的 3D 打印模型:金拱门 M 光盒 + 桌面底座。

输出三个 STL(写到本脚本同目录):
  mc_light_M.stl         —— M 光盒(前面板 + 侧壁,背面开口),平躺打印(前面朝下)
  mc_light_base.stl      —— 桌面底座(顶部插槽 + 内腔 + 背面 USB 出线口)
  mc_light_assembled.stl —— 组装预览(仅供查看,不用于打印)

所有尺寸单位 mm,集中在下面的参数区,按需修改后重跑即可。
运行:python hardware/generate_m_shell.py
"""
import os

import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon
from shapely.affinity import translate as shp_translate

# ----------------------------- 参数区 -----------------------------
# M 轮廓
M_WIDTH = 60.0        # M 总宽
ARCH_R = M_WIDTH / 4  # 驼峰半径(=15,由两峰相接决定:W=4R)
LEG_H = 30.0          # 立腿高度(峰顶 = LEG_H + ARCH_R)
M_HEIGHT = LEG_H + ARCH_R  # M 总高(=45)
CURVE_STEPS = 120     # 顶部曲线采样点数(越大越圆滑)

# M 光盒
FACE_T = 2.0          # 前面板厚度(半透明,越薄越透光)
WALL_T = 2.5          # 侧壁厚度
BOX_DEPTH = 14.0      # 光盒总进深(容纳灯珠/走线)

# 底座
BASE_W = 74.0         # 底座宽(略大于 M 宽)
BASE_D = 40.0         # 底座进深
BASE_H = 24.0         # 底座高
BASE_WALL = 2.5       # 底座壁厚
SLOT_DEPTH = 8.0      # 顶部插槽深度(M 底边插入量)
SLOT_CLEAR = 0.4      # 插槽单边间隙(方便插拔)
USB_W = 12.0          # 背面 USB 出线口宽
USB_H = 7.0           # 背面 USB 出线口高

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE = "manifold"   # 布尔引擎


# ----------------------------- M 轮廓 -----------------------------
def m_polygon():
    """返回金拱门 M 的填充多边形(shapely Polygon),位于 XY 平面。

    顶部 = 两个半圆驼峰取上包络,中间自然形成 V 形凹谷;两侧为竖直立腿,底边平直。
    """
    cx1 = ARCH_R                 # 左峰中心 x
    cx2 = M_WIDTH - ARCH_R       # 右峰中心 x
    xs = np.linspace(0.0, M_WIDTH, CURVE_STEPS)
    h1 = np.sqrt(np.clip(ARCH_R**2 - (xs - cx1) ** 2, 0, None))
    h2 = np.sqrt(np.clip(ARCH_R**2 - (xs - cx2) ** 2, 0, None))
    top = LEG_H + np.maximum(h1, h2)

    pts = [(0.0, 0.0)]                       # 左下角
    pts += [(float(x), float(y)) for x, y in zip(xs, top)]  # 沿顶部曲线
    pts += [(M_WIDTH, 0.0)]                  # 右下角
    return Polygon(pts)


def largest(poly):
    """buffer 后若变成 MultiPolygon,取面积最大的那块。"""
    if isinstance(poly, MultiPolygon):
        return max(poly.geoms, key=lambda g: g.area)
    return poly


# ----------------------------- M 光盒 -----------------------------
def build_m_box():
    outer = m_polygon()
    inner = largest(outer.buffer(-WALL_T))  # 内腔轮廓(四周内缩壁厚)

    solid = trimesh.creation.extrude_polygon(outer, height=BOX_DEPTH)      # z: 0..DEPTH
    cavity = trimesh.creation.extrude_polygon(inner, height=BOX_DEPTH - FACE_T)
    cavity.apply_translation([0, 0, FACE_T])   # 前面留 FACE_T 实心面板,背面开口

    shell = trimesh.boolean.difference([solid, cavity], engine=ENGINE)
    return shell


# ----------------------------- 底座 -----------------------------
def build_base():
    # 外形盒
    base = trimesh.creation.box(extents=[BASE_W, BASE_D, BASE_H])
    base.apply_translation([0, 0, BASE_H / 2.0])  # 底面贴 z=0

    # 内腔(容纳 XIAO 板;底面开口便于放板/走线)
    cav = trimesh.creation.box(
        extents=[BASE_W - 2 * BASE_WALL, BASE_D - 2 * BASE_WALL, BASE_H - BASE_WALL]
    )
    cav.apply_translation([0, 0, (BASE_H - BASE_WALL) / 2.0])  # 顶部留 BASE_WALL 顶板

    # 顶部插槽:接纳 M 底边(宽 M_WIDTH,厚 BOX_DEPTH)
    slot = trimesh.creation.box(
        extents=[M_WIDTH + 2 * SLOT_CLEAR, BOX_DEPTH + 2 * SLOT_CLEAR, SLOT_DEPTH + 1]
    )
    slot.apply_translation([0, 0, BASE_H - SLOT_DEPTH / 2.0])  # 从顶部往下切 SLOT_DEPTH

    # 背面 USB 出线口
    usb = trimesh.creation.box(extents=[USB_W, 4 * BASE_WALL, USB_H])
    usb.apply_translation([0, -BASE_D / 2.0, BASE_H / 2.0])

    return trimesh.boolean.difference([base, cav, slot, usb], engine=ENGINE)


# ----------------------------- 组装预览 -----------------------------
def assembled(m_box, base):
    """把 M 竖起来插进底座插槽,仅供预览。"""
    m = m_box.copy()
    # M 原始:X=[0,60] Y=[0,45](高) Z=[0,14](进深)
    m.apply_translation([-M_WIDTH / 2.0, 0, -BOX_DEPTH / 2.0])  # X 居中,Z 居中
    # 绕 X 轴 +90°:高度(Y)→竖直(Z),进深(Z)→ -Y
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    # 底边(原 y=0)现在在 z=0;抬到底座顶并插入 SLOT_DEPTH
    m.apply_translation([0, 0, BASE_H - SLOT_DEPTH])
    return trimesh.util.concatenate([base, m])


def main():
    m_box = build_m_box()
    base = build_base()

    for name, mesh in [
        ("mc_light_M.stl", m_box),
        ("mc_light_base.stl", base),
        ("mc_light_assembled.stl", assembled(m_box, base)),
    ]:
        path = os.path.join(OUT_DIR, name)
        mesh.export(path)
        wt = getattr(mesh, "is_watertight", None)
        print(f"{name}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces, "
              f"watertight={wt}")

    print("完成。M 光盒平躺打印(前面朝下);底座单独打印。")


if __name__ == "__main__":
    main()
