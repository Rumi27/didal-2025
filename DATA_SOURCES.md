# Data Sources and Provenance

---

## 1. Sentinel-1A SAR (Primary Velocity Dataset)

**Provider:** European Space Agency (ESA) — Copernicus Programme
**Product:** IW-GRDH (Interferometric Wide, Ground Range Detected, High Resolution), 10 m
**Acquisition dates:** 10 scenes, 7 September – 31 October 2025
**Tracks:** Descending Track 78 + Ascending Track 173
**Download:** https://scihub.copernicus.eu (free, registration required)
**License:** Copernicus Open Data — free access and use
**Processing:** SAR offset tracking (amplitude correlation) in ESA SNAP 9.0 with SRTM DEM-assisted coregistration. Workflow: `scripts/data_processing/process_sentinel1_velocity.py`

**Derived products in this repository:**
- 6 velocity GeoTIFFs (m d⁻¹), `data/velocity_maps/`
- V_index time series CSV, `data/velocity_maps/sentinel1_vindex_timeseries.csv`
- Stable-ground debiased pairs, `results/`

---

## 2. PlanetScope Optical Imagery (Terminus Displacement)

**Provider:** Planet Labs PBC
**Product:** PlanetScope PSScene (3 m, 4-band), 5 scenes, Sep 12 – Nov 3, 2025
**License:** Research & Education licence — **cannot be redistributed**
**Access:** Apply at https://www.planet.com/markets/education-and-research/

**What IS shared:** Manual terminus positions digitised from PlanetScope scenes — `data/terminus_digitisation/terminus_positions_verified.csv`. The underlying imagery is not included.

---

## 3. SRTM DEM

**Provider:** NASA / USGS
**Product:** SRTM 1 Arc-Second Global (v3), circa 2000, ~30 m resolution
**Download:** https://earthexplorer.usgs.gov
**DOI:** https://doi.org/10.5066/F7PR7D9D
**License:** Public domain
**Use:** DEM-assisted SAR coregistration, terrain analysis, cross-sections

---

## 4. ERA5-Land Reanalysis

**Provider:** ECMWF / Copernicus Climate Change Service (C3S)
**Product:** ERA5-Land daily, 0.1° grid, 2025
**Download:** https://cds.climate.copernicus.eu
**DOI:** https://doi.org/10.24381/cds.68d2bb30
**License:** Copernicus open data licence
**Use:** Daily temperature, precipitation, snow water equivalent for climate context
**Bias correction:** Applied using Lakhsh WMO station 38744 — see `scripts/data_processing/bias_correct_era5_with_station.py`

**Shared in this repository:** Bias-corrected daily CSV (`data/climate/ERA5_bias_corrected.csv`) and climate derivatives (`data/climate/climate_derivatives_timeseries.csv`). Raw NetCDF files should be downloaded from C3S.

---

## 5. Lakhsh Meteorological Station (WMO 38744)

**Provider:** Tajikistan Hydromet / WMO open data archive
**Period:** February 2005 – January 2026
**Location:** Lakhsh, Tajikistan (~35 km from Didal Glacier)
**File:** `data/climate/lakhsh_station_38744_2005_2026.xls`
**License:** Public domain (WMO open data)
**Use:** Ground-truth for ERA5-Land bias correction

---

## 6. GLIMS Glacier Inventory

**Provider:** NSIDC — Global Land Ice Measurements from Space
**Download ID:** glims_download_02735
**Citation:** Raup, B. et al. (2007). The GLIMS Geospatial Glacier Database. *Global and Planetary Change*, 56(1–2), 101–110. https://doi.org/10.1016/j.gloplacha.2006.07.018
**Zenodo DOI:** https://doi.org/10.7265/N5V98602
**License:** Open access with attribution
**Use:** Regional glacier boundary context

---

## 7. ITS_LIVE Glacier Velocity Archive

**Provider:** NASA / JPL — Inter-mission Time Series of Land Ice Velocity and Elevation
**Download:** https://its-live.jpl.nasa.gov
**License:** Open data, CC BY 4.0
**Citation:** Gardner, A. et al. (2023). ITS_LIVE Regional Glacier and Ice Sheet Surface Velocities. *Data in Brief*.
**Use:** Regional velocity context for comparison

---

## 8. USGS Earthquake Catalog

**Provider:** U.S. Geological Survey
**File:** `data/earthquake/usgs_earthquake_catalog_2025.csv`
**Download:** https://earthquake.usgs.gov/fdsnws/event/1/
**License:** Public domain
**Use:** Rule out seismic triggering of the surge event

---

## Reproducing the Full Processing Pipeline

```bash
# Step 1: Download Sentinel-1 scenes
python scripts/download/download_sentinel1_sar.py

# Step 2: Process SAR offset tracking in SNAP (see SNAP_WORKFLOW.md)
python scripts/data_processing/process_sentinel1_velocity.py

# Step 3: Stable-ground debiasing
python scripts/analysis/stable_ground_debias_and_uncertainty.py

# Step 4: ERA5 climate processing and bias correction
python scripts/data_processing/process_era5_climate_derivatives.py
python scripts/data_processing/bias_correct_era5_with_station.py

# Step 5: Change-point detection
python scripts/analysis/complete_h1_h2_analysis.py
```
