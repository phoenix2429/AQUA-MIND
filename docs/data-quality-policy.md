# AQUA-MIND Data Quality Policy — Version 1

**Policy date:** 2026-09-20  
**Policy version:** 1  
**Status:** Applied to all five-state normalized datasets

---

## Executive Summary

All five states contain a small but significant fraction of physically impossible
groundwater level values. These are confirmed encoding errors — not real observations.
Left unfiltered, they make ML metrics meaningless (training R² = −1.00 for persistence).

This document defines the physical plausibility filter applied before any ML training
or analytics computation. Raw and normalized files are **never modified**.

---

## Physical Plausibility Bounds

| Parameter | Value | Justification |
|---|---|---|
| **Lower bound** | −300.0 m | Deepest wells monitored by CGWB in India; anything deeper is not captured by these sensors |
| **Upper bound** | +50.0 m | Conservative artesian / flowing well limit; Indian basins rarely exceed +10 m above land surface |

Groundwater level convention used by NWDP:
- **Negative** = depth below land surface (most common; well is below ground level)
- **Positive** = head above land surface (artesian / overflowing conditions)

---

## Investigation Findings — Per State

### Andhra Pradesh

| Station | District | Min | Max | Extreme Count | Pattern |
|---|---|---|---|---|---|
| Gondiparla | GUNTUR | −918 | 52 | 2 | Isolated spikes; −918 is impossible |
| Gangulakunta HO Gottipalla | GUNTUR | −997 | 52 | 7 | Near −999.999 sentinel |
| Rajasahebpeta | Kadapa | −995 | 0.5 | 2 | −999.999 sentinel |
| Dharmajigudem | WEST GODAVARI | −994 | −30 | 1 | −999.999 sentinel |
| Dudyala | Kadapa | −856 | −5 | 2 | Deep single-station spike |

**Pattern:** −999.999 is a clear null/missing sentinel.  
Values like −856, −632 may be genuine deep wells but isolated from station's normal readings.

---

### Karnataka

| Station | District | Min | Max | Extreme Count | Pattern |
|---|---|---|---|---|---|
| Chickbagewadi_1 | Belagavi | **−1,561,912,100** | 940 | **1,688** | Persistent extreme — coordinate accidentally stored in GWL column |
| Viswanathahalli | Chitradurga | −25 | **9,505,536** | 1 | Single isolated spike (impossible) |
| Jonigarahalli_1 | Tumkur | −95 | **9,282,538** | 1 | Single isolated spike |
| Shivarpatna | Kolar | −88 | **8,643,413** | 2 | Pair of impossible readings |
| Muddapura_1 | Chitradurga | −31 | **8,592,535** | 1 | Single isolated spike |

**Pattern:** Karnataka has **two distinct error types**:
1. `Chickbagewadi_1` — continuous systematic encoding error (likely coordinate value −15.6° × 10⁸)
2. All other stations — isolated single-observation spikes (sensor fault / transmission error)

Karnataka is the most severe state. 236,548 observations with |value| > 100.

---

### Maharashtra

| Station | District | Min | Max | Extreme Count | Pattern |
|---|---|---|---|---|---|
| Sonambe | Nashik | −43 | **459,884** | 1 | Single isolated spike |
| Kuran_1 | Ahmadnagar | −46 | **418,485** | 4 | Small cluster of large positives |
| Shirtav | Satara | **−3,326** | 0 | 1 | Single negative extreme |
| Takli Rangopant | Jalna | **−1,792** | −15 | **1,934 + 956** | Persistent through both periods |
| Kanhalda | Jalgaon | −14 | 1,019 | 4 | Positive spikes |

**Pattern:** `Takli Rangopant` has **2,890 systematic extreme negative values across both periods** — likely a faulty sensor that consistently reports −1,792 m. Will be excluded by filter.

---

### Tamil Nadu

| Station | District | Min | Max | Extreme Count | Pattern |
|---|---|---|---|---|---|
| Thirupurambiyam | Thanjavur | −44 | **4,435,987** | 1 | Single isolated spike |
| Avadi_2 | Tiruvallur | −42 | **4,109,788** | 2 | Pair of huge positives |
| Uthamapalayam_1 | Theni | **−2,473** | 178 | 318 | Mix of −999.999 and very deep |
| Kumanantholu | Theni | −211 | 1,769 | 353 | Persistent positives — elevation offset? |
| Kommeswaram | Tirupathur | −9 | **1,504** | 267 | Long run of impossible readings |
| Sunnambur | Madurai | **−999.999** | 11 | 40 | Classic sentinel null |
| Thanjavur | Thanjavur | **−999.999** | −40 | 70 | All-sentinel station for period |

**Pattern:** −999.999 sentinel values confirmed. Several stations have hundreds of persistently high positive values — likely meter-vs-centimeter unit confusion (÷100 would give reasonable values).

---

### Telangana

| Station | District | Min | Max | Extreme Count | Pattern |
|---|---|---|---|---|---|
| Chillargi_1 | KAMAREDDY | −46 | **84,464** | 1 | Single isolated spike |
| Kerelli_1 | VIKARABAD | −62 | **5,765** | 1 | Single isolated spike |
| Karjavelly | KUMURAM BHEEM | −62 | **4,065** | 1 | Single isolated spike |
| Pakpatla | NIRMAL | **−3,014** | 1 | 1 | Single negative extreme |
| Ramchandrapur_2 | SIDDIPET | **−1,192** | 15 | 1 | Single negative extreme |
| Uppal Bhagayath | MEDCHAL | −41 | **2,839,585** | 1 | Single isolated spike (2026 period) |
| Garla_1 | MAHABUBABAD | −50 | **47,079** | 1 | Single isolated spike |

**Pattern:** Telangana extremes are almost exclusively isolated single-observation spikes. Very low extreme count per station — almost certainly transmission errors.

---

## What the Filter Does

1. **Reads** each state's normalized CSV from `data/processed/all_states/`
2. **Rejects** rows where `groundwater_level < −300.0 OR > +50.0`
3. **Writes** accepted rows to `data/processed/quality_filtered/<file>.quality_filtered.csv`
4. **Writes** per-file exclusion reports as JSON
5. **Does NOT** modify raw or normalized files
6. **Does NOT** silently discard — all exclusions are counted and sampled

---

## What the Filter Does NOT Do

- Does **not** interpolate missing values
- Does **not** impute using neighboring timestamps
- Does **not** flag or impute the −999.999 sentinel separately (it is excluded by the bounds)
- Does **not** handle the Tamil Nadu centimeter/meter confusion — this requires a separate unit-conversion investigation
- Does **not** modify station metadata

---

## Acknowledged Limitations

1. **Deep-well false rejections:** A small number of genuinely deep wells (e.g. Andhra Pradesh
   Dudyala at −856 m in the 2026 period) may be real observations that are rejected by the
   −300 m lower bound. These are individually rare and the systematic encoding errors (Karnataka
   −1.56 billion) justify the conservative bound.

2. **Tamil Nadu centimeter confusion:** Several Tamil Nadu stations appear to have consistent
   readings in the +1,500–4,000 range which, if divided by 100 (cm to m), would be reasonable
   (15–40 m). This is not automatically corrected — it requires domain confirmation.

3. **Takli Rangopant (Maharashtra):** Station consistently reads −1,792 m across 2,890 observations
   across both 2021–2025 and 2026–2030 periods. Excluded by filter. Likely a faulty sensor.

---

## Recommended Future Actions

- [ ] Confirm with NWDP/CGWB whether Andhra Pradesh −856 m wells are legitimate
- [ ] Investigate Tamil Nadu cm/m confusion with NWDP source data notes
- [ ] Flag `Takli Rangopant` and `Chickbagewadi_1` as sensor-failure stations in the station registry
- [ ] Re-evaluate filter bounds after domain expert review
- [ ] Increase lower bound to −500 m if deep-well confirmations require it

---

## Filter Application Command

```powershell
python scripts/apply_quality_filter.py \
  --input-dir data/processed/all_states \
  --output-dir data/processed/quality_filtered \
  --lower -300 \
  --upper 50
```

Output: `data/processed/quality_filtered/quality_filter_summary.json`
