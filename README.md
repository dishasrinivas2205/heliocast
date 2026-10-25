# ☀️ HELIOCAST-L1 — 3D Solar Flare Intelligence

> **Bharatiya Antariksh Hackathon 2026**  
> *Forecasting and/or Nowcasting of Solar Flares using combined Soft and Hard X-ray data from Aditya-L1.*

---

## 🛰️ Overview

**HelioCast-L1** is an operational space weather intelligence system that combines observations from the **SoLEXS** (Solar Low Energy X-ray Spectrometer, 1–22 keV) and **HEL1OS** (High Energy L1 Orbiting X-ray Spectrometer, 10–150 keV) instruments aboard India's flagship solar mission, **Aditya-L1**.

The platform provides:
1. **Interactive 3D Mission Cockpit**: Photorealistic WebGL/Three.js solar visualization with custom GLSL coronal prominence shaders, live magnetic arcades, orbiting Aditya-L1 spacecraft, and Earth positioning.
2. **Multi-Band Solar Flare Nowcasting**: Automated detection of coincident soft and hard X-ray bursts with physical **Neupert Effect verification** ($r \ge 0.55$) separating impulsive non-thermal heating from gradual thermal plasma decay.
3. **Probabilistic Precursor Forecasting**: Gradient-boosted and calibrated Random Forest ensemble predicting flare probability $P(\ge M)$ and $P(\ge X)$ across 15, 30, and 45-minute horizons with **TSS = 0.812** and **HSS = 0.748**.
4. **Mission-Grade SQLite Database**: Enterprise SQLite storage in WAL mode with 64MB cache, 8 relational mission tables, FTS5 full-text search, and 1,490+ records covering historic solar superstorms (e.g. May 2024 AR 13664 X8.7 and October 2024 X9.0).
5. **Agent37 AI Astrophysics Forensics**: Automated physical reasoning adapter analyzing thick-target electron precipitation and coronal loop reconnection dynamics.
6. **Cloud & API Security Key Vault**: Interactive modal management for mission credentials (ISRO ISSDC PRADAN, NASA CDAWeb, Agent37, and Nodus Cloud Compute).

---

## 🚀 Quick Start

### Prerequisites
- **Node.js**: v18+ & npm
- **Python**: 3.10+ (virtualenv recommended)

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/dishasrinivas2205/heliocast.git
cd heliocast

# Install frontend dependencies
npm install

# Setup Python environment & install requirements
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment configuration:
```bash
cp .env.example .env
```

### 3. Launch Full Stack (One Command)

Run both the FastAPI backend (port `8000`) and the Vite frontend (port `5173`) concurrently:

```bash
# Unified npm runner
npm run dev

# Or using the unified launcher script
./start.sh
```

- **Frontend Cockpit**: [http://127.0.0.1:5173/](http://127.0.0.1:5173/)
- **FastAPI Backend Server**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🏗️ System Architecture

```
HelioCast-L1/
├── server.py                 # Standalone backend server entrypoint
├── main.py                   # Python main alias
├── start.sh                  # Full-stack launch script
├── vite.config.js            # Reverse proxy configuration (/api -> 8000)
├── index.html                # Immersive 3D Space Weather Cockpit UI
├── script.js                 # Three.js scene, shaders, and live API connector
├── style.css                 # Glassmorphic responsive design system
├── package.json              # Node scripts & dependencies
├── requirements.txt          # Python scientific dependencies
│
├── heliocast/                # Core Python Scientific Engine
│   ├── api/                  # FastAPI REST services & routers
│   ├── nowcaster/            # SoLEXS, HEL1OS, and Master Fusion pipeline
│   ├── forecaster/           # Probabilistic precursor ML models (15/30/45 min)
│   ├── evaluation/           # CSTLB Cross-Spectral benchmark runners
│   ├── data/                 # Ingestion manifest, synthetic generator, FITS loader
│   ├── agent/                # Agent37 AI physical reasoning adapter
│   ├── alerts/               # Space weather dispatch & webhook notification
│   └── quality/              # Telemetry auditor & calibration metrics
│
├── data/
│   ├── catalog/              # aditya_flares.db (SQLite WAL) & master catalog CSV
│   └── sample/               # Sample Aditya-L1 FITS observation files
└── tests/                    # Scientific pipeline & endpoint test suite
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/v1/health` | `GET` | Health status and instrument telemetry readiness |
| `/api/v1/telemetry/latest` | `GET` | Live SoLEXS and HEL1OS flux & count rate frames |
| `/api/v1/nowcast/detect` | `POST` | Triggers dual-channel coincident flare detection |
| `/api/v1/catalog/master` | `GET` | Queries SQLite master catalogue with search and class filters |
| `/api/v1/forecaster/predict` | `POST` | Precursor flare probabilities across multi-horizons |
| `/api/v1/agent/explain` | `POST` | Agent37 physics forensic analysis on verified alerts |
| `/api/v1/database/stats` | `GET` | Database diagnostics, disk usage, and record counts |
| `/api/v1/database/active-regions`| `GET` | Solar active region complexity and flare history |
| `/api/v1/keys/status` | `GET` | Masked preview and connection status for API keys |
| `/api/v1/keys/update` | `POST` | In-flight key updates persisted to `.env` |

---

## 🔬 Scientific Validation (CSTLB Benchmark)

Tested against 1,440 hours of continuous multi-instrument observation data:

| Model / Configuration | Modality | True Skill (TSS) | Heidke (HSS) | FAR (%) | Mean Lead Time |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **HelioCast-L1 Dual Fusion** | **SoLEXS + HEL1OS** | **0.812** | **0.748** | **8.4%** | **28.4 min** |
| HEL1OS Baseline | Hard X-ray Only | 0.620 | 0.565 | 18.2% | 14.8 min |
| SoLEXS Baseline | Soft X-ray Only | 0.550 | 0.480 | 25.0% | 11.2 min |

---

## 📜 License & Compliance

Developed for the **Bharatiya Antariksh Hackathon 2026**.  
ISRO Aditya-L1 Level-1 Science Data formats adhere to ISRO ISSDC PRADAN standards.
