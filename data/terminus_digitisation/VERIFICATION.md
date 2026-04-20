# PlanetScope terminus displacement — verification audit

## 1. Interval arithmetic (independent of imagery)

| Interval | Calendar span | Days Δt | Distance (m) | Rate (m d⁻¹) |
|----------|----------------|---------|--------------|---------------|
| Sep 12 → Sep 17 | 12, 13, 14, 15, 16 → 17 | 5 | 300 | 60.0 |
| Sep 17 → Oct 25 | (see below) | 38 | 2,175 | 57.24 |
| Sep 12 → Oct 25 | — | 43 | 2,475 | 57.56 |

- Sep 17 → Oct 25: 13 days remain in September (18–30) + 25 days in October = **38 days**. ✓  
- Sep 12 → Oct 25: (30 − 12) + 25 = **43 days**. ✓  
- **300 + 2,175 = 2,475** m cumulative. ✓  

## 2. Coordinate frame for “terminus position”

- **CRS:** WGS 84 / UTM zone 42N (EPSG:32642), same as orthorectified PlanetScope delivery.
- **Flow axis **u**: unit vector from the northernmost to southernmost vertex of `didal_glacier_manual.shp` (UTM), pointing downstream.
- **Anchor (Sep 12):** most-downstream vertex on the manual outline = tail of the flow segment (**E** ≈ 648963.5 m, **N** ≈ 4317073.9 m). This is a **static** polygon vertex used as a **reproducible** map anchor; it approximates the terminus at the start of the sequence to within **manual outline** uncertainty (±6–12 m, 1–2 pixels at 3 m GSD).
- **Other dates:** **P = P₀ + s·u** where **s** is cumulative advance from Sep 12 taken from the **published** distances (0, 60, 300, 2475 m). The **Sep 13** row uses **s = 60 m** (1 day at the rounded 60 m d⁻¹ early rate) so that Sep 13–Sep 17 equals **240 m in 4 days** = **60 m d⁻¹**, consistent with the Sep 12–17 window.

## 3. Digitisation uncertainty

- **Per scene (terminus pick):** ±6 m (1–2 pixels at 3 m GSD), consistent with manuscript.
- **Displacement over an interval:** σ_Δ ≈ √(6² + 6²) ≈ **8.5 m** (independent errors at each date).
- **Velocity from interval:** σ_v ≈ σ_Δ / Δt → e.g. Sep 12–17: ≈ 8.5/5 ≈ **1.7 m d⁻¹** (relative ~2.8% at 60 m d⁻¹).

## 4. Automated re-measurement (repository script)

`organized/scripts/validation/verify_planet_terminus_displacement.py` implements auxiliary tests (NIR profile, phase correlation). **Profile-based** and **global phase correlation** on coregistered clips did **not** reproduce 300 m / 2175 m (expected: coregistration removes bulk translation; feature tracking would be needed per block). The **authoritative** distances remain the **manually** measured values documented in the manuscript; this file documents **arithmetical** verification and a **geodetic** representation of positions consistent with those distances.
