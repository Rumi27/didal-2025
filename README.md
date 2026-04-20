# SAR Monitoring Limits in Narrow Valley Glaciers: Rapid Motion at Didal Glacier, Tajikistan (2025)

This repository contains all data, processing scripts, and analysis code accompanying the paper:

> **"SAR monitoring limits in narrow valley glaciers: rapid motion at Didal Glacier, Tajikistan"**
> *Journal of Glaciology* — **under review**

> This repository is made available ahead of acceptance to support the review process.
> The Zenodo DOI and full citation will be added upon acceptance.

---

## Study Summary

Didal Glacier (38.97°N, 70.72°E, Pamir Mountains, Tajikistan, ~1.6 km²) underwent a rapid detachment-type surge event in September–October 2025. The terminus advanced 2,475 m over 43 days (57–60 m d⁻¹). This repository documents the SAR and optical remote sensing monitoring effort and the limits of Sentinel-1 SAR for narrow valley glaciers (<500 m width).

---

## Repository Structure

```
.
├── data/
│   ├── velocity_maps/          # Sentinel-1 SAR velocity GeoTIFFs (6 epochs) + V_index time series CSV
│   ├── glacier_outlines/       # Didal Glacier boundary shapefiles (manual + RGI)
│   ├── stable_ground/          # Stable-ground validity masks, debiasing statistics
│   ├── terminus_digitisation/  # Manual terminus positions from PlanetScope (CSV + LaTeX table)
│   ├── climate/                # ERA5-Land bias-corrected time series + Lakhsh open station data
│   └── earthquake/             # USGS earthquake catalog (Sep–Oct 2025, regional)
├── scripts/
│   ├── data_processing/        # Sentinel-1 offset tracking, ERA5 processing, bias correction
│   ├── analysis/               # Stable-ground debiasing, uncertainty, change-point detection
│   ├── figure_generation/      # Scripts to reproduce all paper figures
│   ├── download/               # Download scripts for Sentinel-1, Sentinel-2, ERA5, DEM
│   ├── validation/             # Cross-track validation, autoRIFT, same-track comparison
│   └── measurement/            # Terminus digitisation and displacement measurement tools
├── results/
│   ├── change_point/           # PELT change-point detection results
│   ├── uncertainty/            # Per-epoch LoD, NMAD, uncertainty statistics
│   ├── bias_correction/        # ERA5 bias correction summary
│   └── *.csv                   # 6-day and 12-day debiased velocity pairs
├── DATA_SOURCES.md             # Full data provenance and download instructions
├── requirements.txt            # Python dependencies
└── README.md
```

---

## Key Data Files

| File | Description |
|---|---|
| `data/velocity_maps/sentinel1_vindex_timeseries.csv` | Sentinel-1 V_index time series — main result |
| `data/velocity_maps/velocity_YYYYMMDD_YYYYMMDD.tif` | Per-epoch SAR offset-tracking velocity maps (m d⁻¹) |
| `data/stable_ground/stable_ground_mask_clean.shp` | Stable-ground validation polygon |
| `data/stable_ground/pairwise_stable_ground_stats.csv` | Per-pair NMAD, bias, LoD statistics |
| `data/terminus_digitisation/terminus_positions_verified.csv` | Manual terminus positions (lat/lon, date, displacement) |
| `data/climate/ERA5_bias_corrected.csv` | Daily temperature & precipitation, bias-corrected to Lakhsh station |
| `data/climate/lakhsh_station_38744_2005_2026.xls` | Lakhsh WMO station 38744 (public meteorological record) |
| `results/change_point/pelt_changepoint_results.json` | PELT algorithm change-point dates and velocities |

---

## Quick Start

### Install dependencies
```bash
pip install -r requirements.txt
```

### Load the V_index time series
```python
import pandas as pd
df = pd.read_csv("data/velocity_maps/sentinel1_vindex_timeseries.csv", parse_dates=["date"])
print(df.head())
```

### Reproduce the stable-ground debiasing
```bash
python scripts/analysis/stable_ground_debias_and_uncertainty.py
```

### Reproduce paper figures
```bash
python scripts/figure_generation/fig14_changepoint_publication.py
python scripts/figure_generation/fig15_spatial_maps_publication_v2.py
```

---

## Data Not Included (Licensing Restrictions)

| Dataset | Reason | How to Access |
|---|---|---|
| **PlanetScope imagery** | Commercial research license — cannot redistribute | Request from [Planet Labs](https://www.planet.com/markets/education-and-research/) |
| **Raw Sentinel-1 SAFE files** (~345 GB) | Freely available from ESA | [Copernicus Open Access Hub](https://scihub.copernicus.eu) — Track 78 & 173, Sep–Oct 2025 |
| **Raw Sentinel-2 SAFE files** (~71 GB) | Freely available from ESA | [Copernicus Open Access Hub](https://scihub.copernicus.eu) |
| **AWS Kyzylsu station** | Restricted institutional data | Contact data owners |

See `DATA_SOURCES.md` for full provenance and citations.

---

## Citation

> **Paper is currently under review.** Citation will be updated upon acceptance.

In the meantime, if you use this data or code, please cite this repository directly:

```bibtex
@misc{Didal_Glacier_2025_repo,
  author    = {[Authors]},
  title     = {SAR monitoring limits in narrow valley glaciers: rapid motion at Didal Glacier, Tajikistan — data and code repository},
  year      = {2025},
  publisher = {GitHub},
  url       = {https://github.com/Rumi27/didal-2025}
}
```

---

## License

- **Code:** MIT License
- **Data (derived products):** CC BY 4.0
- **Lakhsh station data:** Public domain (WMO open data)
- **ERA5-Land (bias-corrected CSV):** Derived from Copernicus Climate Change Service data — CC BY 4.0
