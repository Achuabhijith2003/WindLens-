# WindLens Phase 1 & 2: WINDFOR Historical Forecast Investigation & Selection Engine

## 1. Executive Summary & Objective

The objective of WindLens is to evaluate the accuracy of Great Britain wind generation forecasts against actual outturn generation across January 2026 (delivery dates `2026-01-01` to `2026-01-31`), using Elexon BMRS `FUELHH` and `WINDFOR` datasets.

A central requirement established in Phase 1 and confirmed in Phase 2 is that **publication-time filtering diverges fundamentally from delivery-time windowing**:
1. Early January 2026 delivery slots depend on forecasts generated and published in late December 2025.
2. For each delivery slot, NESO publishes multiple revisions (up to 8 times daily).
3. Forecast evaluation requires an explicit, documented **decision cutoff rule** to select the latest forecast available prior to trading/planning deadlines without lookahead leakage.

---

## 2. Live Verified Endpoint Behavior & Retrieval Strategy

In Phase 2, we probed all candidate endpoints on the live Elexon BMRS API (`https://data.elexon.co.uk/bmrs/api/v1`):

| Endpoint Path | Query Parameters Tested | Observed Status | Actual Response Structure & Behavior |
| :--- | :--- | :--- | :--- |
| **`GET /datasets/WINDFOR/stream`** | `publishDateTimeFrom`, `publishDateTimeTo` | **`HTTP 200`** | **Raw JSON List** of records. Contains every forecast run published during the publication window, with full `publishTime`, `startTime`, and `generation` (MW). **This is the only endpoint that allows range-based retrieval of historical forecast revisions without prior knowledge of exact timestamps.** |
| **`GET /datasets/WINDFOR`** | `publishDateTimeFrom`, `publishDateTimeTo` | **`HTTP 200`** | JSON Envelope `{"data": [...]}`. Functionally identical to the stream endpoint with an object wrapper. |
| **`GET /forecast/generation/wind/history`** | `from`, `to` or `publishDateTimeFrom` | **`HTTP 400`** | `{"errors": {"PublishTime": ["A value for the 'PublishTime' parameter or property was not provided."]}}`. **Requires an exact single point-in-time timestamp** (`publishTime`), making bulk range queries impossible without already knowing all publication runs. |
| **`GET /forecast/generation/wind/evolution`** | `from`, `to` | **`HTTP 400`** | `{"errors": {"StartTime": ["A value for the 'StartTime' parameter or property was not provided."]}}`. Requires a single delivery slot `startTime` to track evolution for one period. |
| **`GET /forecast/generation/wind/latest`** | `from`, `to` | **`HTTP 200`** | Returns only the **latest** forecast for each slot in the range. However, for historical dates, the latest published forecast often has `publishTime` *after* the delivery interval (retrospective outturn run, e.g. `publishTime = 2026-01-01T22:30:00Z` for `startTime = 2026-01-01T00:00:00Z`). It omits earlier day-ahead or intraday revisions prior to a trading cutoff. |
| **`GET /datasets/FUELHH/stream`** | `publishDateTimeFrom`, `publishDateTimeTo`, `fuelType=WIND` | **`HTTP 200`** | Raw JSON List of actual half-hourly generation records (`dataset: "FUELHH"`). |

### Conclusion on Endpoint Selection
**`/datasets/WINDFOR/stream` is selected as the primary forecast ingestion endpoint.** It provides complete access to all historical revisions published within any arbitrary window, enabling exact cutoff filtering.

---

## 3. Publication Window & December 2025 Lookback

Because forecasts are published ahead of delivery:
* **Day-Ahead Forecasts for Jan 1, 2026 (00:00 UTC):** Published on **2025-12-31** (e.g., between 04:30 and 17:00 UTC).
* **Multi-Day Lookahead:** NESO publishes forecasts looking forward up to 14 days ahead.
* **Retrieval Policy:** To guarantee 100% forecast coverage for delivery dates in January 2026, the ingestion engine queries WINDFOR publication timestamps with a **7-day lookback buffer**:
  $$\text{publishDateTimeFrom} = \text{delivery\_start} - 7\text{ days (e.g. 2025-12-25T00:00:00Z)}$$
  $$\text{publishDateTimeTo} = \text{delivery\_end} + 1\text{ day (e.g. 2026-02-01T00:00:00Z)}$$

---

## 4. Decision Cutoff Formulation & Methodology

To avoid lookahead bias and evaluate realistic market performance, WindLens enforces an explicit cutoff rule:

### 4.1 Default Assumption: Day-Ahead 17:00 UTC (`day_ahead_1700`)
* **Definition:** For any delivery slot on date $D$, only forecasts published on or before **$(D - 1)\text{ at } 17:00:00\text{ UTC}$** are eligible.
* **Selection:** Out of all eligible forecasts for that delivery slot, the one with the latest `publishTime` ($\max(\text{publishTime})$) is selected.
* **Notice:** *This uses an assumed Day-Ahead reference benchmark of 17:00 UTC on the day prior to delivery (D-1 17:00 UTC). This is an assumed analytical benchmark and not an official Elexon statutory deadline.*

### 4.2 Configurable Cutoff Variants Supported
* `day_ahead_1200` (or `d1_1200`): D-1 at 12:00:00 UTC (noon market auction benchmark).
* `gate_closure_1h`: Exactly 1 hour before delivery `startTime` (operational dispatch benchmark).
* `lead_Xh` (e.g. `lead_4h`): Configurable $X$ hours before delivery `startTime`.
* Explicit ISO 8601 timestamp (e.g. `2025-12-31T17:00:00Z`).

### 4.3 Zero-Lookahead Enforcement
* Any forecast with `publishTime > cutoff_time` is strictly filtered out and logged under `future_forecasts_filtered_count`.
* If a delivery interval has no eligible forecast published at or before the cutoff, the status is set to `missing_forecast`. **No missing values are fabricated or silently filled with zero.**

---

## 5. Temporal Granularity: Half-Hourly vs. Hourly

An important discovery from live data verification:
* **FUELHH Outturns:** Half-hourly resolution (48 settlement periods per standard day, e.g. `00:00`, `00:30`, `01:00`, etc.).
* **WINDFOR Forecasts:** Published on hourly delivery intervals (`00:00`, `01:00`, `02:00`... 24 intervals per day).

### Matching Rule
* Records are matched by exact delivery `startTime`.
* Delivery intervals corresponding to `:00` have both actual and forecast (`status: "matched"`).
* Delivery intervals corresponding to `:30` have actual outturns but no hourly forecast, and are reported with `status: "missing_forecast"`.
* Metrics (MAE, RMSE, Bias, MAPE) are calculated **strictly on valid matched pairs**, and completeness percentage reflects the ratio of matched intervals to total expected half-hourly slots.

---

## 6. Accuracy Metrics Definitions

1. **Mean Absolute Error (MAE):**
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |\text{forecast}_i - \text{actual}_i|$$
2. **Root Mean Squared Error (RMSE):**
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (\text{forecast}_i - \text{actual}_i)^2}$$
3. **Signed Bias:**
   $$\text{Bias} = \frac{1}{N} \sum_{i=1}^N (\text{forecast}_i - \text{actual}_i)$$
   *Positive bias indicates over-forecasting; negative indicates under-forecasting.*
4. **Mean Absolute Percentage Error (MAPE):**
   $$\text{MAPE} = \frac{100\%}{M} \sum_{i=1, \text{actual}_i \neq 0}^M \frac{|\text{forecast}_i - \text{actual}_i|}{|\text{actual}_i|}$$
   *Intervals with $\text{actual} = 0$ are excluded to prevent division by zero, and the count of excluded zeros is explicitly tracked and reported.*

---

## 7. Remaining Historical Data Limitations

1. **Hourly vs. Half-Hourly Granularity:** Because WINDFOR stream publishes forecasts primarily on hourly steps while FUELHH outturns are half-hourly, half-hourly completeness is capped at ~50% unless an hourly aggregation mode or interpolation model is formally introduced in Phase 3.
2. **Unannounced Revision Intervals:** NESO updates forecasts approximately every 3 to 4 hours, but exact publication timestamps vary by several minutes per run. Range-based queries on `/datasets/WINDFOR/stream` handle this robustly.
3. **Network Latency for Full-Month Ingestion:** Ingesting 31 days of historical data from Elexon requires querying ~16 two-day windows. The local memory and disk caching layer in `DataService` mitigates repeated requests.
