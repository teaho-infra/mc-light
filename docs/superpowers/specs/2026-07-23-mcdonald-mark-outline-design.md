# McDonald Mark Outline Correction

## Goal

Correct the yellow mark in the monitor front-panel STL so its silhouette matches
`hardware/McDonald.jpeg` while preserving the existing 24 mm nominal width,
1.2 mm flush front-panel thickness, split-color STL workflow, and case geometry.

## Root Cause

The current `m_polygon()` buffers three center lines with a uniform stroke width.
That construction makes the arch crowns too thick, the arches too tall and
narrow, the outside shoulders too steep, and the center foot too short. A
normalized raster comparison against the supplied reference has an
intersection-over-union score of only 0.6409.

## Selected Design

Build one symmetric filled polygon from explicit outer and inner cubic Bezier
curves. The outer contour controls the overall shoulders and arch crowns. The
inner contour independently controls the two counters and center valley, so
stroke thickness can vary like the reference instead of being imposed by a
uniform buffer.

Keep the outline parameterized by `width / M_WIDTH`. Center the final polygon
from its actual bounds. Do not load the JPEG at generation time; the generated
STL must remain deterministic and self-contained.

## Alternatives Considered

- Trace the JPEG into a long fixed point list. This gives high fidelity but is
  difficult to understand, tune, and review.
- Extract the yellow mask from the JPEG every time the STL is generated. This
  keeps the raster appearance but couples production output to image-processing
  thresholds and an external asset.
- Fit independent Bezier contours. This gives comparable visual fidelity with a
  small, deterministic, maintainable geometry definition. This is selected.

## Verification

- Add a failing test for the reference width-to-height ratio.
- Add a failing test for reference-relative crown, valley, and foot positions.
- Add a failing raster-similarity test using a compact set of normalized
  reference silhouette samples rather than loading the JPEG in production.
- Retain existing volume, alignment, size, and assembly tests.
- Regenerate all affected STL outputs and confirm they are watertight.
- Render a normalized before/after overlay for visual inspection.

## Scope

Only the yellow mark geometry, its focused tests, and generated STL artifacts
change. The back shell, front thickness, red/yellow split, box dimensions, and
USB/XIAO geometry remain unchanged.
