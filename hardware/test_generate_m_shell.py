import importlib.util
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point


MODULE_PATH = Path(__file__).with_name("generate_m_shell.py")


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_m_shell", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bounds_size(mesh):
    bounds = mesh.bounds
    return bounds[1] - bounds[0]


def vertical_span(poly, x):
    min_x, min_y, max_x, max_y = poly.bounds
    segment = LineString([(x, min_y - 1.0), (x, max_y + 1.0)])
    hit = poly.intersection(segment)
    if hit.is_empty:
        return None
    return hit.bounds[1], hit.bounds[3]


def test_front_parts_are_flush_and_thin():
    gen = load_generator()

    red, yellow = gen.build_front_parts()

    assert red.is_volume
    assert yellow.is_volume
    assert pytest.approx(red.bounds[:, 2].tolist(), abs=0.01) == [0.0, gen.FRONT_T]
    assert pytest.approx(yellow.bounds[:, 2].tolist(), abs=0.01) == [0.0, gen.FRONT_T]
    assert 1.0 <= gen.FRONT_T <= 1.5


def test_front_assembled_matches_square_face_size():
    gen = load_generator()

    front = gen.build_front_assembled()
    sx, sy, sz = bounds_size(front)

    assert pytest.approx(sx, abs=0.05) == gen.BOX_W
    assert pytest.approx(sy, abs=0.05) == gen.BOX_H
    assert pytest.approx(sz, abs=0.01) == gen.FRONT_T


def test_m_mark_has_reference_logo_feet():
    gen = load_generator()

    mark = gen.m_polygon()
    min_x, min_y, max_x, max_y = mark.bounds
    width = max_x - min_x
    height = max_y - min_y

    baseline_y = min_y + height * 0.04
    center_foot_y = min_y + height * 0.16

    assert mark.contains(Point(min_x + width * 0.04, baseline_y))
    assert mark.contains(Point(max_x - width * 0.04, baseline_y))
    assert not mark.contains(Point(min_x + width * 0.50, baseline_y))
    assert mark.contains(Point(min_x + width * 0.50, center_foot_y))
    assert not mark.contains(Point(min_x + width * 0.25, baseline_y))
    assert not mark.contains(Point(min_x + width * 0.75, baseline_y))


def test_m_mark_matches_reference_proportions():
    gen = load_generator()

    mark = gen.m_polygon()
    min_x, min_y, max_x, max_y = mark.bounds
    width = max_x - min_x
    height = max_y - min_y

    assert mark.is_valid
    assert mark.geom_type == "Polygon"
    assert width / height == pytest.approx(1.145, abs=0.025)

    left_outer = vertical_span(mark, min_x + width * 0.04)
    left_leg = vertical_span(mark, min_x + width * 0.125)
    left_crown = vertical_span(mark, min_x + width * 0.25)
    center_foot = vertical_span(mark, min_x + width * 0.50)

    assert left_outer == pytest.approx(
        (min_y, min_y + height * 0.512),
        abs=height * 0.04,
    )
    assert left_leg == pytest.approx(
        (min_y, min_y + height * 0.830),
        abs=height * 0.04,
    )
    assert left_crown == pytest.approx(
        (min_y + height * 0.910, min_y + height * 0.994),
        abs=height * 0.035,
    )
    assert center_foot == pytest.approx(
        (min_y + height * 0.071, min_y + height * 0.665),
        abs=height * 0.035,
    )


def test_back_shell_has_bottom_usb_opening_and_xiao_clearance():
    gen = load_generator()

    back = gen.build_back_shell()
    sx, sy, sz = bounds_size(back)

    assert back.is_volume
    assert pytest.approx(sx, abs=0.05) == gen.BOX_W
    assert pytest.approx(sy, abs=0.05) == gen.BOX_H
    assert pytest.approx(sz, abs=0.05) == gen.BOX_D - gen.FRONT_T
    assert gen.BOARD_POCKET_W >= gen.XIAO_W + 1.0
    assert gen.BOARD_POCKET_H >= gen.XIAO_H + 1.0
    assert gen.USB_OPEN_W >= 12.0
    assert gen.USB_OPEN_H >= 8.0


def test_assembly_preview_contains_back_and_front_depth():
    gen = load_generator()

    assembled = gen.build_monitor_assembled()
    sx, sy, sz = bounds_size(assembled)

    assert pytest.approx(sx, abs=0.05) == gen.BOX_W
    assert pytest.approx(sy, abs=0.05) == gen.BOX_H
    assert pytest.approx(sz, abs=0.05) == gen.BOX_D


def test_output_names_match_spec():
    gen = load_generator()

    assert [name for name, _builder in gen.OUTPUTS] == [
        "mc_light_monitor_back.stl",
        "mc_light_monitor_front_red.stl",
        "mc_light_monitor_front_M.stl",
        "mc_light_monitor_front_assembled.stl",
        "mc_light_monitor_assembled.stl",
    ]
