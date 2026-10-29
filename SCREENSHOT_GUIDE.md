# WindLens — Screenshot & Video Demonstration Checklist

This checklist details the exact application screens and parameter configurations to capture for project documentation, demonstration videos, and presentation slides.

All screenshots should be captured from the live, running application (running locally via `docker compose up` or local `npm run dev` + `uvicorn`). Store the captured images in `docs/screenshots/`.

---

## Screenshot Inventory

### 1. Main Overview & Time-Series Timeline
- **Suggested Filename**: `docs/screenshots/01_overview_dashboard.png`
- **Dashboard Section**: **Overview & Timeline** Tab
- **Filter Settings**:
  - Delivery Date: `2026-01-01`
  - Decision Cutoff: `Day-Ahead (D-1 17:00 UTC) - Default`
  - Comparison Resolution: `Hourly (24/d)`
  - View Mode: `Single Day View`
- **What It Demonstrates**:
  - The top KPI bar displaying MAE ($4{,}217.4$ MW), RMSE ($4{,}277.9$ MW), Signed Bias ($+4{,}217.4$ MW), MAPE ($27.65\%$), and Completeness ($100.0\%$).
  - The main Recharts line chart showing `WINDFOR` forecast generation (blue) vs. `FUELHH` actual outturn generation (green).
  - The interactive timeline brush scrubber at the bottom of the chart.
  - The 4 analytical highlight cards: Peak Forecast, Peak Actual, Max Over-Forecast, and Max Under-Forecast.
- **Requires Running Backend**: Yes (`http://localhost:8000` or Docker on port `3001`).
- **Professional Caption**: *WindLens Overview tab showing Day-Ahead forecast vs. actual wind generation outturn, interactive timeline scrubber, and peak deviation metrics for January 1, 2026.*

---

### 2. Forecast Correlation & Error Distribution
- **Suggested Filename**: `docs/screenshots/02_forecast_correlation.png`
- **Dashboard Section**: **Forecast Correlation** Tab
- **Filter Settings**:
  - Delivery Date: `2026-01-01`
  - Decision Cutoff: `Day-Ahead (D-1 17:00 UTC) - Default`
  - Comparison Resolution: `Hourly (24/d)`
- **What It Demonstrates**:
  - Top summary cards showing Pearson correlation coefficient ($r$), coefficient of determination ($R^2$), and Actual/Forecast $P_{10}$, $P_{50}$, $P_{90}$ generation percentiles.
  - Scatter plot comparing Actual generation (X-axis) against Forecast generation (Y-axis) with the dashed 1:1 $y=x$ ideal reference line. Points above the line highlight over-forecasting.
  - The forecast error distribution histogram binned by error ranges in MW (showing frequency from severe under-forecast to severe over-forecast).
- **Requires Running Backend**: Yes.
- **Professional Caption**: *Forecast Correlation tab featuring actual-versus-forecast scatter plot with 1:1 reference line and binned forecast error distribution histogram.*

---

### 3. Error Timeline & Diurnal Bias Profile
- **Suggested Filename**: `docs/screenshots/03_error_analysis.png`
- **Dashboard Section**: **Error & Bias Analysis** Tab
- **Filter Settings**:
  - Delivery Date: `2026-01-01`
  - Decision Cutoff: `Day-Ahead (D-1 17:00 UTC) - Default`
  - Comparison Resolution: `Hourly (24/d)`
- **What It Demonstrates**:
  - Signed error bar chart across the 24 hours of the delivery day with a distinct zero baseline, showing amber bars for over-forecast intervals ($FC > ACT$).
  - The 24-hour Diurnal Bias Profile bar chart calculating average error for each hour of the day ($00:00$ to $23:00$ UTC) to expose time-of-day bias.
  - The Extreme Forecast Deviations table ranking top over-forecast and under-forecast intervals with lead times.
- **Requires Running Backend**: Yes.
- **Professional Caption**: *Error & Bias Analysis tab detailing signed forecast error timeline, 24-hour diurnal bias profile by hour-of-day, and extreme deviation rankings.*

---

### 4. Data Quality & Market Mechanics Diagnostics
- **Suggested Filename**: `docs/screenshots/04_data_quality_diagnostics.png`
- **Dashboard Section**: **Data Quality & Integrity** Tab
- **Filter Settings**:
  - Delivery Date: `2026-01-01`
  - Decision Cutoff: `Day-Ahead (D-1 17:00 UTC) - Default`
  - Comparison Resolution: `Half-Hourly (48/d)` *(selected to illustrate resolution handling)*
- **What It Demonstrates**:
  - The 6-tile diagnostic grid reporting: Expected Slots (48), Matched Pairs (24), Resolution Mismatch (24), Missing Forecasts (0), Missing Actuals (0), and Post-Cutoff Filtered forecasts.
  - The educational market mechanics cards explaining Day-Ahead Gate Closure ($D-1\ 17:00$ UTC) zero-lookahead rules and Settlement Period resolution alignment.
- **Requires Running Backend**: Yes.
- **Professional Caption**: *Data Quality diagnostics highlighting Elexon pipeline integrity counts, half-hourly resolution mismatch handling, and gate-closure mechanics.*

---

### 5. Interval Investigation & CSV Export
- **Suggested Filename**: `docs/screenshots/05_interval_table.png`
- **Dashboard Section**: **Detailed Intervals** Tab
- **Filter Settings**:
  - Delivery Date: `2026-01-01`
  - Decision Cutoff: `Day-Ahead (D-1 17:00 UTC) - Default`
  - Comparison Resolution: `Hourly (24/d)`
  - Table Options: Status filter set to `All Statuses`, search query cleared or demonstrating a search.
- **What It Demonstrates**:
  - The paginated, sortable interval table with column headers: Delivery Start (UTC), Settlement Period (SP), Forecast, Actual, Signed Error, Status, Forecast Published Time, and Lead Time.
  - Column sorting indicator arrows, status badges (`matched`), and the **Export CSV** download button.
- **Requires Running Backend**: Yes.
- **Professional Caption**: *Detailed Intervals tab displaying sortable delivery period records, publication lead times, and CSV data export functionality.*

---

### 6. Multi-Day Range Accuracy Evaluation
- **Suggested Filename**: `docs/screenshots/06_multiday_range.png`
- **Dashboard Section**: **Single Day / Multi-Day Range Toggle**
- **Filter Settings**:
  - Mode: `Multi-Day Range`
  - From Date: `2026-01-01`
  - To Date: `2026-01-07`
  - Decision Cutoff: `day_ahead_1700`
  - Comparison Resolution: `Hourly (24/d)`
- **What It Demonstrates**:
  - Aggregate metrics across the entire 7-day period.
  - The Daily Accuracy Breakdown Table listing MAE, RMSE, Signed Bias, MAPE, Matched/Expected intervals, and Completeness percentage for each day from Jan 1 through Jan 7.
- **Requires Running Backend**: Yes.
- **Professional Caption**: *Multi-day range evaluation comparing daily forecast accuracy metrics and completeness across January 1–7, 2026.*

---

### 7. Alternative Light Theme
- **Suggested Filename**: `docs/screenshots/07_light_theme.png`
- **Dashboard Section**: Header theme toggle switched to `windlens-light`
- **Filter Settings**: Any single-day selection
- **What It Demonstrates**:
  - The clean, high-contrast `windlens-light` theme token palette with crisp light slate surfaces and accessible typography.
- **Requires Running Backend**: Yes (or rendered static view).
- **Professional Caption**: *WindLens user interface operating under the alternative crisp light theme.*

---

### 8. Interactive FastAPI Swagger API Documentation
- **Suggested Filename**: `docs/screenshots/08_fastapi_swagger_docs.png`
- **URL**: `http://localhost:8000/docs`
- **What It Demonstrates**:
  - The interactive OpenAPI / Swagger documentation showing all 4 endpoints (`/api/health`, `/api/overview`, `/api/timeseries`, `/api/accuracy`), query parameters, schema models, and the "Try it out" feature.
- **Requires Running Backend**: Yes (`python -m uvicorn backend.main:app` or Docker).
- **Professional Caption**: *Interactive FastAPI OpenAPI / Swagger documentation displaying typed endpoint contracts and schemas.*

---

## Step-by-Step Instructions to Capture Genuine Screenshots

1. **Start the Application**:
   ```bash
   docker compose up --build -d
   ```
2. **Open the Dashboard in your Browser**:
   Navigate to [http://localhost:3001](http://localhost:3001).
3. **Capture Each View**:
   - Use your operating system's built-in screenshot utility:
     - **Windows**: `Windows Key + Shift + S` (Snipping Tool).
     - **macOS**: `Cmd + Shift + 4`.
     - **Linux**: `Shift + PrtScn`.
   - Maximize your browser window to standard 1080p ($1920 \times 1080$) for clean proportions and legible typography.
4. **Save Files**:
   Save each screenshot into `docs/screenshots/` matching the filenames in the table above.
5. **Verify API Documentation**:
   Navigate to [http://localhost:8000/docs](http://localhost:8000/docs) and capture `08_fastapi_swagger_docs.png`.

