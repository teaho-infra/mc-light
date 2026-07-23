# McDonald Mark Outline Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the distorted uniformly buffered mark with a deterministic parametric silhouette that matches `hardware/McDonald.jpeg`.

**Architecture:** Keep `m_polygon(width)` as the only public two-dimensional mark builder. Construct one symmetric polygon from independent outer and inner cubic Bezier segments, then let the existing front-part extrusion and STL export pipeline consume it unchanged.

**Tech Stack:** Python 3, NumPy, Shapely, Trimesh, pytest.

## Global Constraints

- Keep the nominal mark width at `M_WIDTH = 24.0`.
- Keep the front panel at `FRONT_T = 1.2`.
- Keep the red/yellow front parts flush and complementary.
- Do not load `McDonald.jpeg` in production code.
- Do not change back-shell, XIAO, USB, or enclosure dimensions.

---

### Task 1: Correct and Verify the Mark Silhouette

**Files:**
- Modify: `hardware/test_generate_m_shell.py`
- Modify: `hardware/generate_m_shell.py`
- Regenerate: `hardware/mc_light_monitor_front_red.stl`
- Regenerate: `hardware/mc_light_monitor_front_M.stl`
- Regenerate: `hardware/mc_light_monitor_front_assembled.stl`
- Regenerate: `hardware/mc_light_monitor_assembled.stl`

**Interfaces:**
- Consumes: `m_polygon(width: float = M_WIDTH) -> shapely.geometry.Polygon`
- Produces: the same `m_polygon()` interface and the existing `OUTPUTS` meshes.

- [ ] **Step 1: Replace coarse logo tests with reference-derived failing assertions**

Add normalized cross-section assertions:

```python
def test_m_mark_matches_reference_proportions():
    gen = load_generator()
    mark = gen.m_polygon()
    min_x, min_y, max_x, max_y = mark.bounds
    width = max_x - min_x
    height = max_y - min_y

    assert width / height == pytest.approx(1.145, abs=0.025)

    left_outer = vertical_span(mark, min_x + width * 0.04)
    left_leg = vertical_span(mark, min_x + width * 0.125)
    left_crown = vertical_span(mark, min_x + width * 0.25)
    center_foot = vertical_span(mark, min_x + width * 0.50)

    assert left_outer == pytest.approx((min_y, min_y + height * 0.512), abs=height * 0.04)
    assert left_leg == pytest.approx((min_y, min_y + height * 0.830), abs=height * 0.04)
    assert left_crown == pytest.approx(
        (min_y + height * 0.910, min_y + height * 0.994),
        abs=height * 0.035,
    )
    assert center_foot == pytest.approx(
        (min_y + height * 0.071, min_y + height * 0.665),
        abs=height * 0.035,
    )
```

Retain the existing foot-presence assertions and add:

```python
assert mark.is_valid
assert mark.geom_type == "Polygon"
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
pytest hardware/test_generate_m_shell.py::test_m_mark_matches_reference_proportions -q
```

Expected: FAIL because the current mark has a width-to-height ratio near `1.04`
and thicker, taller crowns than the reference.

- [ ] **Step 3: Implement one explicit symmetric Bezier outline**

Keep the existing `cubic_points()` evaluator. Replace the line-buffer union with
a polygon contour defined in normalized coordinates:

```python
outer_left = cubic_points((0.0, 0.0), (0.01, 0.64), (0.14, 1.0), (0.275, 1.0), steps)
outer_valley = cubic_points((0.275, 1.0), (0.39, 1.0), (0.47, 0.72), (0.5, 0.665), steps)[1:]
outer = outer_left + outer_valley
outer += [(1.0 - x, y) for x, y in reversed(outer[:-1])]

inner_right = cubic_points((0.865, 0.0), (0.86, 0.55), (0.82, 0.91), (0.75, 0.91), steps)
inner_right += cubic_points((0.75, 0.91), (0.68, 0.91), (0.61, 0.66), (0.56, 0.55), steps)[1:]
inner_right += cubic_points((0.56, 0.55), (0.545, 0.43), (0.545, 0.16), (0.54, 0.071), steps)[1:]
inner_left = [(1.0 - x, y) for x, y in reversed(inner_right)]

normalized = outer + [(1.0, 0.0), (0.865, 0.0)] + inner_right[1:]
normalized += [(0.46, 0.071)] + inner_left[1:] + [(0.0, 0.0)]
points = [(x * width, y * width / 1.145) for x, y in normalized]
poly = Polygon(points)
```

Center the validated polygon from its actual bounds exactly as before. Remove
the no-longer-used `LineString` and `unary_union` imports.

- [ ] **Step 4: Run the focused test and tune only Bezier control points**

Run:

```bash
pytest hardware/test_generate_m_shell.py::test_m_mark_matches_reference_proportions -q
```

Expected: PASS. If a cross-section misses its tolerance, change only the
control points governing that cross-section; do not loosen the tolerance.

- [ ] **Step 5: Run the complete geometry suite**

Run:

```bash
pytest hardware/test_generate_m_shell.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Regenerate STL artifacts**

Run:

```bash
python3 hardware/generate_m_shell.py
```

Expected: five files exported; every line reports `watertight=True`.

- [ ] **Step 7: Perform visual and mesh verification**

Render the normalized corrected silhouette beside the supplied reference and
confirm that the crown thickness, shoulder width, center valley, and three feet
match. Confirm the four changed front/assembly STL files have valid volumes and
the front remains `38 x 38 x 1.2 mm`.
