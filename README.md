# WindLens

WindLens is an electricity market analytics application for evaluating Great Britain wind generation forecasts against actual outturn generation for January 2026 delivery dates, using Elexon BMRS `FUELHH` and `WINDFOR` datasets.

## Architecture

- **Backend**: FastAPI with async Elexon client, decision cutoff engine, and resolution matching.
- **Frontend**: React 18, Tailwind CSS v4, DaisyUI v5, and Recharts.
- **Data Cache**: Local disk persistence under `data/cache/` (31 days of January 2026 data).

---

## Running with Docker Compose (Recommended)

Build and run both the frontend and backend in isolated containers:

```bash
docker compose up --build -d
```

- **Frontend Dashboard**: [http://localhost:3001](http://localhost:3001)
  *(Configurable via `FRONTEND_PORT` environment variable)*
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Frontend Proxy Route**: Requests to `http://localhost:3001/api/*` are automatically reverse-proxied to `backend:8000`.

To view status and logs:
```bash
docker compose ps
docker compose logs -f
```

To stop services:
```bash
docker compose down
```

---

## Running Locally (Development Mode)

### 1. Backend

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Run test suite:
```bash
python -m unittest discover -s backend/tests
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Run frontend tests:
```bash
npm test
```

Build for production:
```bash
npm run build
```
