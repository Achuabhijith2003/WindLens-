# WindLens — Beginner's Guide & Project Overview

Welcome to **WindLens**! This guide is written for anyone new to the project—whether you are an engineer, power-market student, or project reviewer. It explains the application step-by-step in clear, plain language without sacrificing technical accuracy.

---

## 1. What WindLens Does

In simple terms, **WindLens evaluates how good Great Britain's wind power forecasts were before the wind actually blew.**

To do this, WindLens compares two distinct data streams from Great Britain's electricity system operator:
1. **The Forecast**: What meteorologists and grid algorithms predicted wind farms would generate (published ahead of time).
2. **The Actual Outturn**: What Great Britain's wind farms actually generated and delivered onto the grid (recorded after the fact).

WindLens measures the differences between the forecast and actual generation, calculates statistical accuracy scores (like average error in Megawatts), and visualizes the results on an interactive dashboard.

---

## 2. Who Uses WindLens and Why

- **Electricity Traders**: Power trading companies buy and sell electricity hours and days before delivery. If they trade based on an inaccurate wind forecast, they end up with too much or too little electricity and face heavy financial penalties ("imbalance charges"). They use WindLens to understand when forecasts are reliable and when they tend to fail.
- **Grid Operators (National Grid ESO)**: Grid controllers must keep system frequency at 50 Hz by matching electricity supply to demand at every second. Knowing systematic forecast bias (e.g., if forecasts always over-predict in the morning) allows them to keep the right amount of backup generation (gas turbines, batteries) ready.
- **Wind Farm Developers & Asset Owners**: Asset managers use forecast evaluation to benchmark commercial forecasting vendors against official grid forecasts.
- **Energy Data Analysts**: Analysts use WindLens to audit historical forecast performance and evaluate market mechanics without lookahead bias.

---

## 3. What You See on the Dashboard

The dashboard is structured into logical sections:

### A. Top Navigation Bar (Header)
- **Application Title & Version**: Shows `WindLens v0.2.0`.
- **Elexon BMRS Source Tag**: Notes that data is sourced from official Elexon streams (`FUELHH` and `WINDFOR`).
- **Connection Status Badge**: A green pill showing `API Connected` when the FastAPI backend is communicating, or red `Backend Offline` if the server is unreachable.
- **Theme Toggle**: A Sun/Moon button that switches between `windlens-dark` (low-brightness slate palette) and `windlens-light`. Your preference is remembered automatically.

### B. Filter & Parameter Panel
Located directly under the header. Allows you to choose the exact date, cutoff time rule, and comparison resolution.

### C. Top KPI Stat Bar
Displays five core accuracy scores across the active selection:
1. **MAE (MW)**: Mean Absolute Error.
2. **RMSE (MW)**: Root Mean Square Error.
3. **Signed Bias (MW)**: Directional bias (+ over-forecasting, - under-forecasting).
4. **MAPE (%)**: Percentage error relative to actual outturn.
5. **Completeness (%)**: How many intervals were successfully evaluated out of expected intervals.

### D. The Five Analytical Tabs
1. **Overview & Timeline**:
   - The primary time-series line chart comparing Forecast MW (blue) and Actual MW (green).
   - A timeline scrubber (`Brush`) at the bottom of the chart to drag, zoom, and focus on specific hours.
   - Peak comparison cards (Peak Forecast vs. Peak Actual MW and timestamps).
   - Extreme deviation callouts (largest over-forecast and largest under-forecast of the day).
2. **Forecast Correlation**:
   - **Scatter Plot ($y = x$)**: Actual generation on the X-axis vs. Forecast generation on the Y-axis. The diagonal dashed line is the "ideal" 1:1 line. Points above the line mean over-forecasting; points below mean under-forecasting.
   - **Error Histogram**: A bar chart grouping errors into Megawatt buckets (e.g., $-2{,}000$ to $-1{,}000$ MW, $0$ to $+1{,}000$ MW) to show error distribution and tail risks.
   - **Statistical Summary**: Shows Pearson correlation ($r$), coefficient of determination ($R^2$), and generation percentiles ($P_{10}, P_{50}, P_{90}$).
3. **Error & Bias Analysis**:
   - **Signed Error Timeline**: Displays $(FC - ACT)$ across each hour of the day relative to a solid zero line. Amber bars show over-forecasts; blue bars show under-forecasts.
   - **Diurnal 24-Hour Error Profile**: Bar chart showing the average bias for each hour of the day ($00:00$ to $23:00$ UTC), identifying time-of-day systematic bias.
   - **Extreme Outliers Table**: Lists the top 4 largest over-forecast intervals and top 4 largest under-forecast intervals with exact MW numbers and forecast lead times.
4. **Data Quality & Market Mechanics**:
   - Ingestion breakdown: Matched count, resolution mismatches (`:30`), post-cutoff filtered forecasts, missing actuals.
   - Educational cards explaining GB Day-Ahead gate closure ($D-1\ 17:00$ UTC) and half-hourly vs. hourly settlement mechanics.
5. **Detailed Intervals**:
   - A full data table listing every delivery period.
   - Includes Delivery Start (UTC), Settlement Period (SP 1–48), Forecast MW, Actual MW, Signed Error MW, Status, Forecast Publish Time, and Lead Time in hours.
   - Filter by status, search by timestamp, sort by clicking column headers, paginate, and click **Export CSV** to download the data as an RFC 4180 CSV spreadsheet.

---

## 4. What Each Filter Changes

| Filter | Options | What Happens When You Change It |
| :--- | :--- | :--- |
| **Delivery Date** | Dates in January 2026 (`2026-01-01` to `2026-01-31`) | Queries the backend for that specific 24-hour day. Re-calculates all metrics, redraws the chart, and populates the table. |
| **Decision Cutoff** | • `day_ahead_1700` (Default)<br>• `day_ahead_1200`<br>• `gate_closure_1h`<br>• `gate_closure_2h`<br>• `lead_4h` | Changes the rule for which forecasts are legally eligible. For example, `day_ahead_1700` only considers forecasts published before 17:00 UTC on the previous day. Changing this selects different forecast revisions and changes all error scores. |
| **Comparison Resolution** | • `Hourly (24/d)` (Default)<br>• `Half-Hourly (48/d)` | • **Hourly**: Aggregates two 30-minute actuals $(SP_a + SP_b)/2.0$ into 1-hour average MW to match hourly forecasts.<br>• **Half-Hourly**: Keeps raw 30-minute actuals. Because forecasts are only published on the hour, `:30` rows will have no forecast and will be labeled `resolution_mismatch`. |
| **View Mode** | • `Single Day View`<br>• `Multi-Day Range` | Toggles between analyzing a single 24-hour day and analyzing a date range (e.g. Jan 1 to Jan 7). Range mode reveals a Daily Breakdown Table comparing daily MAE, RMSE, and bias. |

---

## 5. What Each KPI Means and How to Read It

*Note: The following examples are illustrative calculations designed to demonstrate the math.*

### A. Mean Absolute Error (MAE)
- **What it is**: The average size of forecast mistakes in Megawatts, ignoring whether the forecast was too high or too low.
- **Illustrative Example**:
  - Interval 1: Forecast was off by $+500$ MW.
  - Interval 2: Forecast was off by $-300$ MW.
  - Absolute errors are $500$ and $300$.
  - $\text{MAE} = (500 + 300) / 2 = 400\ \text{MW}$.
- **How to Interpret**: Lower is better. An MAE of $400$ MW on a day with $15{,}000$ MW of wind means the model is generally very accurate.

### B. Root Mean Square Error (RMSE)
- **What it is**: Similar to MAE, but it squares errors before averaging them and takes the square root.
- **Why it matters**: Squaring heavily penalizes large, catastrophic errors.
- **Illustrative Example**:
  - Two errors of $100$ MW each: $\text{RMSE} = \sqrt{(100^2 + 100^2)/2} = 100\ \text{MW}$.
  - One error of $0$ MW and one of $200$ MW: $\text{RMSE} = \sqrt{(0^2 + 200^2)/2} \approx 141.4\ \text{MW}$.
- **How to Interpret**: Lower is better. If RMSE is much higher than MAE, it means the forecast had occasional huge misses rather than steady small errors.

### C. Signed Bias
- **What it is**: The arithmetic average of errors: $\text{Mean}(\text{Forecast} - \text{Actual})$.
- **Directional Meaning**:
  - **Positive Signed Bias ($> 0\ \text{MW}$, Amber)**: **Over-forecasting**. The model predicted more wind than actually showed up.
  - **Negative Signed Bias ($< 0\ \text{MW}$, Blue)**: **Under-forecasting**. The wind blew harder than the model predicted.
  - **Zero Bias ($= 0\ \text{MW}$)**: Unbiased overall (positive and negative errors cancelled out).
- **How to Interpret**: Closer to zero is better. A large positive bias means a trader who followed the forecast was repeatedly left short of electricity.

### D. Mean Absolute Percentage Error (MAPE)
- **What it is**: The average error expressed as a percentage of actual generation.
- **Formula**: $\text{Mean}(|\text{Error}| / \text{Actual}) \times 100\%$.
- **Zero-Actual Protection**: If actual generation is $0.0$ MW (e.g. during a dead calm), dividing by zero is impossible. WindLens automatically excludes those intervals from the percentage average and tells you in the stat description (e.g., `2 zeros excluded`).
- **How to Interpret**: Lower is better. Below $15\%$ is considered strong for Day-Ahead wind; above $30\%$ indicates a volatile weather day.

### E. Data Completeness
- **What it is**: The percentage of expected delivery slots that had both a valid forecast and a valid actual generation reading.
- **How to Interpret**: In hourly mode, 24 out of 24 matched slots equals $100.0\%$.

---

## 6. How to Read the Main Chart

The main chart in the Overview tab shows:
- **Blue Line**: The `WINDFOR` forecast generation curve in Megawatts (MW).
- **Green Line**: The `FUELHH` actual outturn generation curve in Megawatts (MW).
- **X-Axis**: Time of day in UTC (e.g. `00:00`, `04:00`, `08:00`).
- **Y-Axis**: Power in Megawatts, formatted as thousands (e.g., `10.0k MW` = $10{,}000$ MW).
- **Hover Tooltip**: Move your mouse over any point on the line to see the exact time, Settlement Period (SP), forecast MW, actual MW, exact error in MW, and how many hours ahead the forecast was published.
- **Interactive Scrubber (`Brush`)**: At the very bottom of the chart is a mini-slider. Click and drag the handles on the left and right to zoom into a specific morning ramp (e.g. 06:00 to 12:00) or drag the window across the day.
- **Discontinuous Gaps**: If an interval is missing data, the line stops and leaves an open gap. **WindLens never connects missing intervals to zero**, because plotting a fake zero would deceive the analyst.

---

## 7. Understanding Forecast Errors: Positive vs. Negative

In energy markets, the definition of error is standardized as:
$$\text{Error} = \text{Forecast} - \text{Actual}$$

```text
       ▲ Forecast Generation > Actual Generation
       │ ERROR IS POSITIVE (+)
       │ • Meaning: "Over-Forecasting" (The forecast promised more wind than showed up)
       │ • Market Consequence: The trader sold too much power. They are "short" and must
       │   buy expensive balance power to cover the difference.
───────┼───────────────────────────────────────────── (Zero Line: Perfect Forecast)
       │ ERROR IS NEGATIVE (-)
       │ • Meaning: "Under-Forecasting" (The wind blew harder than expected)
       │ • Market Consequence: The trader generated extra power. They are "long" and must
       │   spill the power or sell it at discount system prices.
       ▼ Actual Generation > Forecast Generation
```

---

## 8. What the Cutoff Means and Why It Matters

Wind forecasts are not static; National Grid ESO updates the `WINDFOR` forecast every few hours as weather models update.

Suppose we want to know how accurate forecasts were for delivery on **January 2 at 14:00 UTC**:
- A forecast issued on January 1 at 16:00 UTC (22 hours ahead) predicted $12{,}000$ MW.
- A forecast issued on January 2 at 13:30 UTC (30 minutes ahead) predicted $14{,}500$ MW.
- The actual outturn was $14{,}700$ MW.

If an analyst uses the forecast issued 30 minutes ahead to evaluate Day-Ahead market positions, they are committing **lookahead bias**. A Day-Ahead trader closed their trades at **17:00 UTC on January 1**. They never had access to the 30-minute-ahead forecast!

**The Cutoff Rule**:
WindLens draws a strict line in time:
$$\text{Cutoff for Delivery Day } D = (D - 1)\ \text{at 17:00:00 UTC}$$
WindLens discards every forecast revision published after that cutoff. It selects the single latest forecast revision published *before or at* 17:00 UTC. This guarantees that backtested accuracy reflects the real world.

---

## 9. Why Half-Hourly Rows May Not Have a Forecast

In the Great Britain electricity market:
- The actual outturn dataset (`FUELHH`) is recorded in **30-minute blocks** called Settlement Periods (SP 1 through SP 48 each day). For example: `00:00`, `00:30`, `01:00`, `01:30`.
- The National Grid forecast dataset (`WINDFOR`) is published only for **60-minute blocks** on the hour: `00:00`, `01:00`, `02:00`.

When you view the dashboard in **Half-Hourly Mode**:
- `00:00 UTC`: Matches the `00:00` forecast. Status is `matched`.
- `00:30 UTC`: There is no native forecast for `:30`. Status is `resolution_mismatch`.

> [!NOTE]
> Some naive software simply copies the `00:00` forecast into `:30` or invents an average. WindLens deliberately refuses to fabricate synthetic data. If you want a complete mathematical match, switch to **Hourly Mode**, where WindLens averages the two half-hour actuals $(SP_1 + SP_2)/2.0$ into a true 1-hour average MW power block.

---

## 10. How the React Frontend Communicates with FastAPI

1. The user selects a date (e.g. `2026-01-05`) in the React UI.
2. React's [`api.js`](file:///d:/JOB/Gridbricks/windlens/frontend/src/services/api.js) dispatches an HTTP GET request to:
   `GET /api/overview?date=2026-01-05&cutoff=day_ahead_1700&resolution=hourly`
3. **In Docker**: Nginx receives the request on port 3001, sees the `/api` prefix, and reverse-proxies the request internally to `http://backend:8000/api/overview`.
4. **In Local Dev**: Vite sends the request directly to `http://localhost:8000/api/overview` (CORS is enabled in FastAPI).
5. FastAPI parses the query, fetches and matches the cached records, calculates MAE, RMSE, and bias in milliseconds, and returns a JSON payload.
6. React updates its state (`setOverviewData`, `setTimeseriesData`), triggering Recharts to render the charts and tables.

---

## 11. What the Backend Does with Elexon Data

The backend is built in modular layers:
1. **`backend/elexon/client.py`**: Talks to the Elexon API via HTTPX. Handles network timeouts and converts timestamps to UTC.
2. **`backend/services/data_service.py`**: Caches downloaded data on disk (`data/cache/fuelhh_cache.json` and `windfor_cache.json`) so subsequent requests do not hit Elexon's servers.
3. **`backend/engine/cutoff.py`**: Calculates the cutoff timestamp for every delivery date (e.g. `2025-12-31 17:00 UTC` for Jan 1).
4. **`backend/engine/matcher.py`**: Takes thousands of raw forecast revisions, discards post-cutoff entries, finds the latest revision per slot, and pairs it with actual outturn. Aggregates half-hours to hourly when requested.
5. **`backend/engine/metrics.py`**: Runs the mathematics for MAE, RMSE, signed bias, MAPE, and completeness percentage.
6. **`backend/api/routes.py`**: Serves the results over standard REST endpoints.

---

## 12. What Docker Does in This Project

Docker packages the entire application into lightweight, self-contained containers:
- **`windlens-backend` Container**: Contains Python 3.11, installs all requirements from `requirements.txt`, copies the backend code and cached datasets, and runs the Uvicorn web server on port 8000.
- **`windlens-frontend` Container**: Uses a multi-stage build. First, Node 20 compiles the React + Vite code into static HTML/CSS/JS (`npm run build`). Then, an Alpine Nginx web server serves those files on port 80 (mapped to host port 3001) and reverse-proxies all `/api/*` calls to the backend container.

Docker ensures that the application runs identically on any computer (Windows, Mac, Linux) without needing Python or Node installed on the host machine.

---

## 13. Implemented vs. Unsupported Features

| Feature | Status | Details |
| :--- | :--- | :--- |
| **January 2026 Dataset** | **Fully Implemented** | Complete 31-day dataset (1,488 actuals, 18,080 forecasts) cached locally. |
| **Day-Ahead 17:00 Cutoff** | **Fully Implemented** | Dynamically calculated per delivery date with zero-lookahead filtering. |
| **Hourly Aggregation** | **Fully Implemented** | $(SP_a + SP_b)/2.0$ arithmetic mean aggregation with missing-value guards. |
| **5-Tab Analytics Platform**| **Fully Implemented** | Overview, Scatter correlation ($y=x$), Error timeline, Diurnal profile, Table with CSV. |
| **Multi-Day Range View** | **Fully Implemented** | Compares date ranges with daily breakdown tables. |
| **Docker Compose Setup** | **Fully Implemented** | Tested and verified healthy on ports 3001 (frontend) and 8000 (backend). |
| **Live Dates Beyond Jan 2026**| **Supported via Live API**| Supported if Elexon API is reachable; returns HTTP 502/504 if Elexon is down. |
| **ML Forecast Bias Correction**| *Future Scope* | Applying machine learning models to correct wind forecast bias is not yet implemented. |

---

## 14. Glossary of Technical Terms

- **BMRS**: Balancing Mechanism Reporting Service, the official platform for Great Britain electricity market data managed by Elexon.
- **BSC**: Balancing and Settlement Code, the legal framework governing Great Britain's electricity balancing and imbalance settlement.
- **Delivery Date ($D$)**: The calendar date on which electricity is physically generated and consumed.
- **Gate Closure**: The final deadline before delivery after which market participants cannot change their traded positions.
- **Imbalance**: The difference between the electricity a market participant promised to generate/consume and what they actually delivered.
- **Lookahead Bias**: A common analytical error where data from the future is accidentally used to evaluate decisions made in the past.
- **Outturn**: The actual, measured generation delivered to the grid.
- **Settlement Period (SP)**: A 30-minute trading and delivery block. There are 48 Settlement Periods in a standard day (SP 1 = 00:00–00:30 UTC, SP 48 = 23:30–24:00 UTC).
- **WINDFOR**: National Grid ESO's official wind power forecast data stream.
- **FUELHH**: Elexon's half-hourly outturn generation data stream categorized by fuel type (wind, nuclear, gas, solar).

---

## 15. Presentation Cheat Sheet: 10 Reviewer Questions & Answers

If a reviewer or examiner asks about your implementation, here are direct, code-backed answers:

### Q1: "How do you select the forecast for each delivery interval?"
**Answer**: "For any delivery date $D$, WindLens establishes a decision cutoff (by default, $D-1\ \text{17:00:00 UTC}$). We filter all candidate forecast revisions for that delivery slot, discard any revision with a publication timestamp after the cutoff, and select the record with the latest publication timestamp ($\max(\text{publishTime}) \le \text{cutoff}$). This ensures zero lookahead leakage."

### Q2: "Why don't you use one single cutoff timestamp for the entire month of January?"
**Answer**: "Applying a single cutoff—such as December 31 17:00 UTC—across all of January would mean evaluating January 31 delivery using a 31-day-old forecast. That does not reflect how electricity markets operate. In reality, Day-Ahead trading happens every single day. Therefore, WindLens calculates the cutoff independently for each delivery date $D$ as $D-1\ \text{17:00:00 UTC}$."

### Q3: "Elexon publishes half-hourly actuals, but wind forecasts are hourly. How did you reconcile the difference?"
**Answer**: "We support two explicit modes: in the default **Hourly Mode**, we aggregate the two half-hourly actuals $(SP_a + SP_b)/2.0$ via arithmetic mean into a 1-hour average MW power block, with zero fabricated data. In **Half-Hourly Mode**, we preserve raw settlement granularity, match the `:00` slots against the forecast, and explicitly label `:30` slots as `resolution_mismatch`, excluding them from error metrics rather than falsely flagging them as pipeline failures."

### Q4: "How does your system handle intervals where actual generation is zero when calculating MAPE?"
**Answer**: "If actual generation is $0.0$ MW, percentage error is mathematically undefined due to division by zero. In `backend/engine/metrics.py`, we detect $ACT_i = 0$, exclude those intervals from the MAPE denominator, record the count in `mape_excluded_zero_count`, and report the excluded count clearly in both the API response and the UI KPI card."

### Q5: "What is the difference between MAE and RMSE in your results?"
**Answer**: "MAE gives the linear average error magnitude in MW. RMSE squares each error before averaging, which heavily penalizes large outlier misses. When RMSE is significantly higher than MAE on a given day, it tells the analyst that the model suffered from isolated, severe forecast busts rather than consistent minor deviations."

### Q6: "What does a positive signed bias mean for a power trader?"
**Answer**: "Signed bias is $\text{Mean}(\text{Forecast} - \text{Actual})$. A positive bias means the forecast was higher than actual generation—the model over-forecasted. For a power trader who sold energy based on that forecast, it means they generated less electricity than contracted. They are left 'short' and must pay cash-out imbalance penalties to National Grid ESO."

### Q7: "What happens if a backend network request to the Elexon API fails or times out?"
**Answer**: "In `backend/elexon/client.py`, HTTPX requests are wrapped with explicit 30-second timeouts, raising typed exceptions (`ElexonTimeoutError`, `ElexonHTTPStatusError`). Furthermore, `DataService` uses a local persistent disk cache under `data/cache/` containing pre-validated January 2026 data, meaning typical user requests never hit the external network and execute in milliseconds."

### Q8: "How does the frontend communicate with the backend when running inside Docker?"
**Answer**: "The frontend container runs Nginx on port 80 (mapped to host port 3001). Nginx is configured with a reverse-proxy location block: any request sent to `/api/*` is internally proxied across Docker's bridge network to `http://backend:8000`. This eliminates CORS issues and ensures the browser only communicates with a single origin."

### Q9: "Why does the time-series chart show gaps instead of connecting to zero?"
**Answer**: "In `ForecastChart.jsx`, both `<Line>` components set `connectNulls={false}`. If an interval has missing actual outturn or an unforecasted `:30` slot, Recharts renders a visible gap. Fabricating zero values or interpolating across gaps is dangerous in energy analytics because it distorts perceived generation volumes."

### Q10: "What was the Vercel deployment issue you encountered and how was it solved?"
**Answer**: "When deploying to Vercel with the backend service root set to `backend/`, AWS Lambda placed `main.py` directly at `/var/task/`. Python threw `ModuleNotFoundError: No module named 'backend'` when executing `from backend.api.routes import router`. We resolved this by injecting a dynamic package alias shim in `backend/main.py` that maps `sys.modules['backend']` to the current directory if it does not already exist, and setting the Vercel project preset to `Other` so `vercel.json` coordinates both Vite and FastAPI."

