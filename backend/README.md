# HelioCast-L1 Scientific Backend

Dedicated FastAPI backend service for the ISRO Aditya-L1 solar flare nowcasting and precursor forecasting pipeline.

## Running the Backend Standalone

```bash
# From repository root:
python backend/server.py

# Or directly:
python -m backend.main
```

## Available REST API Endpoints

| Category | Endpoint | Method | Purpose |
|---|---|---|---|
| **Health** | `/api/v1/health` | GET | Subsystem health, mission metadata & payload status |
| **Telemetry** | `/api/v1/telemetry/latest` | GET | Live real-time Aditya-L1 dual-band frame (SoLEXS + HEL1OS) |
| **Light Curve** | `/api/v1/telemetry/lightcurve` | GET | Synchronized multi-band historical light curve frames |
| **Nowcaster** | `/api/v1/nowcast/detect` | POST | Trigger dual-threshold Neupert algorithmic detection scan |
| **Master Catalog** | `/api/v1/catalog/master` | GET | Query SQLite master catalog with FTS5 text search |
| **Database Diagnostics** | `/api/v1/database/stats` | GET | Total records, disk size, active regions, WAL status |
| **PRADAN Status** | `/api/v1/forecaster/pradan-status` | GET | Training status, sample count (10,800), ROC-AUC (0.986) |
| **PRADAN Retraining** | `/api/v1/forecaster/train-pradan` | POST | Retrain precursor forecaster models on mission telemetry |
| **Flare Injector** | `/api/v1/nowcast/inject-flare` | POST | Inject simulated X/M/C flare, run predictor, save to DB |
| **Agent37 AI** | `/api/v1/agent/explain` | POST | Physical flare forensics & Neupert correlation analysis |
| **API Keys** | `/api/v1/keys/status` | GET | Check operational status of all external integration keys |
| **Key Updates** | `/api/v1/keys/update` | POST | Persist live API credentials directly into `.env` |
| **Alerts** | `/api/v1/alerts/history` | GET | Active space weather bulletin log and safe-mode orders |
| **Interactive Docs** | `/docs` | GET | Swagger / OpenAPI interactive testing interface |

## Architecture

- **`heliocast/`**: Core scientific physics, ML models, and data pipelines
- **`backend/server.py`**: Standalone backend entrypoint respecting `$PORT` and `$HELIOCAST_ENV`
- **`backend/requirements.txt`**: Python dependencies needed to run the scientific server
