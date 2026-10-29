# WindLens Phase 1: WINDFOR Historical Publication Records Investigation

## 1. Executive Summary & Objective

In Phase 1 of WindLens, we investigated the Elexon BMRS **WINDFOR** (Wind Generation Forecast) dataset.
A central requirement is to **not assume that the endpoint's publication-time filtering returns all forecasts needed for the January 2026 delivery period**.

This document details:
1. The structural mechanics of WINDFOR records.
2. Verified API behavior and endpoint variations.
3. Why publication-time filtering diverges fundamentally from delivery-period windowing.
4. Remaining uncertainties and decisions required for Phase 2 forecast-to-actual matching.

---

## 2. WINDFOR Data Model & Semantics

In the Elexon BMRS API, each WINDFOR record represents an operational wind generation forecast produced by NESO (National Energy System Operator, formerly National Grid ESO):

| Field | Type | Description |
| :--- | :--- | :--- |
| `dataset` | `string` | `"WINDFOR"` |
| `publishTime` | `ISO 8601 string` | Timestamp when NESO computed and published the forecast run. |
| `startTime` | `ISO 8601 string` | Target 30-minute settlement block or delivery hour being forecasted. |
| `settlementDate` | `string (YYYY-MM-DD)` | Settlement date of the target delivery block. |
| `settlementPeriod` | `integer (1-50)` | Settlement period of the target delivery block. |
| `generation` | `integer / float` | Forecasted aggregate wind generation across GB in Megawatts (MW). |

---

## 3. Verified Endpoint Behavior

### 3.1 Dataset Stream Endpoint: `/datasets/WINDFOR/stream`
* **Base URL:** `https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream`
* **Accepted Query Parameters:**
  * `publishDateTimeFrom` (`ISO 8601 date-time`): Start of the publication window (inclusive).
  * `publishDateTimeTo` (`ISO 8601 date-time`): End of the publication window (inclusive).
  * `format` (`json`, `xml`, `csv`): Default `json`.
* **Verified Behavior:**
  * If `publishDateTimeFrom` is supplied, `publishDateTimeTo` must also be supplied.
  * The stream endpoint filters **strictly on `publishTime`**. It does **not** accept `settlementDate` or `startTime` filters.
  * Omission of publication parameters on standard `/datasets/WINDFOR` defaults to returning the latest available forecast run.

### 3.2 Dedicated Forecast Endpoints: `/forecast/generation/wind/...`
Elexon also provides analytical endpoints under the forecast domain:
* `GET /forecast/generation/wind/history` (Accepts `from` and `to` query parameters)
* `GET /forecast/generation/wind/evolution` (Accepts target delivery timestamps and tracks how forecasts evolved over successive runs)
* `GET /forecast/generation/wind/latest`

---

## 4. Why Publication-Time Filtering != Delivery-Period Windowing

A naive assumption that querying `publishDateTimeFrom=2026-01-01T00:00:00Z` to `publishDateTimeTo=2026-01-31T23:59:59Z` retrieves the complete forecasts for January 2026 delivery is incorrect for three major structural reasons:

### 4.1 Prior-Period Generation (Lookahead Window)
Forecasts are generated **in advance** of electricity delivery:
* **Day-Ahead Forecasts:** A forecast for delivery on `2026-01-01 00:00:00Z` (Settlement Period 1) is generated and published on **2025-12-31** (typically around 17:00 UTC or earlier).
* **Multi-Day Horizon:** NESO publishes forecasts looking forward up to 14 days. A 2-day or 7-day ahead forecast for early January would have been published in late December 2025.
* **Impact:** Querying solely `publishDateTime >= 2026-01-01` **omits all Day-Ahead and multi-day ahead forecasts for the beginning of January 2026**.

### 4.2 Month-End Overhang (Projections into February)
* Forecasts published towards the end of January (e.g. `publishTime = 2026-01-31 23:00:00Z`) project into February 2026 (`startTime = 2026-02-01 00:00:00Z` and beyond).
* **Impact:** A publication-window query includes delivery intervals belonging to the subsequent month, requiring explicit client-side delivery filtering.

### 4.3 Multi-Revision Multiplicity (Intraday Evolution)
* NESO updates wind forecasts **up to 8 times daily** (approximately every 3 hours).
* For any single half-hour delivery slot `startTime` in January 2026 (e.g. `2026-01-15 14:00:00Z`), there exist multiple distinct WINDFOR records, each with a different `publishTime` and updated `generation` figure.
* **Impact:** Querying the publication stream returns multiple records per settlement period. Simply aggregating or taking the sum will produce meaningless figures unless a revision-selection strategy is applied.

---

## 5. Remaining Uncertainties & Phase 2 Architectural Decisions

Before building accuracy metrics or pairing actuals with forecasts in Phase 2, the following engineering decisions must be finalized:

| Area | Uncertainty / Decision Required | Proposed Strategy |
| :--- | :--- | :--- |
| **Lookback Buffer** | How far back into December 2025 must we query `publishDateTime` to capture Day-Ahead forecasts for January 1st? | Query with a buffer starting at least `2025-12-25T00:00:00Z` (7-day lookback) and partition in 2-day windows. |
| **Forecast Horizon Selection** | Which forecast revision should be compared against FUELHH actuals? | 1. **Day-Ahead (D-1 17:00 UTC):** Standard market benchmark.<br>2. **Final Intraday (Gate Closure - 1h):** Operational dispatch benchmark.<br>3. **Full Evolution Matrix:** Evaluate error degradation as lead time decreases. |
| **Endpoint Selection** | Should ingestion rely on `/datasets/WINDFOR/stream` or `/forecast/generation/wind/history`? | Verify in Phase 2 whether `/forecast/generation/wind/history` filters by delivery `startTime` directly, which may reduce client-side post-filtering. |
| **Data Gaps / Restatements** | Are there retrospective restatements of WINDFOR runs or delivery intervals with missing revisions? | Implement deduplication and revision tracking indexed by `(startTime, publishTime)`. |

---

## 6. Summary of Verification in Exploration Module

The WindLens Python backend exploration module includes:
1. `WindforRecord` validation and lead-time extraction (`startTime - publishTime`).
2. Verification of `delivery_extends_beyond_query_window` and `delivery_precedes_query_window`.
3. Revision counting per delivery slot (`mean_revisions_per_delivery_time` and `max_revisions_for_single_delivery_time`).
4. Unit tests (`test_windfor_investigation_and_lead_times`) confirming that multi-horizon and multi-revision behavior is handled deterministically.

