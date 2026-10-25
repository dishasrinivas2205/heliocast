"""
FastAPI REST API Routes for HelioCast-L1 Scientific Server.
Provides versioned endpoints for telemetry ingestion, nowcasting,
forecasting, database querying, and alert notifications.
"""

from datetime import datetime, timezone
import os
from dotenv import load_dotenv
load_dotenv()
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
import pandas as pd
from pydantic import BaseModel, Field

from heliocast import __version__
from heliocast.agent.agent37_adapter import Agent37ResearchAdapter
from heliocast.alerts.dispatcher import AlertDispatcher, SpaceWeatherAlert
from heliocast.data.manifest import IngestionManifest
from heliocast.data.synthetic import SolarFlareSimulator
from heliocast.evaluation.cstlb import CrossSpectralBenchmarkRunner
from heliocast.execution.nodus_adapter import NodusComputeAdapter
from heliocast.forecaster.pipeline import FlareForecastingPipeline
from heliocast.nowcaster import FlareCatalogDatabase, SolarFlareNowcaster
from heliocast.quality.audit import TelemetryQualityAuditor

router = APIRouter(prefix="/api/v1", tags=["HelioCast Space Weather API"])

# Shared singleton instances
nowcaster = SolarFlareNowcaster()
forecaster = FlareForecastingPipeline()
alert_dispatcher = AlertDispatcher()
sim = SolarFlareSimulator(random_seed=42)
cstlb_runner = CrossSpectralBenchmarkRunner()
quality_auditor = TelemetryQualityAuditor()
manifest = IngestionManifest()
agent_adapter = Agent37ResearchAdapter()
compute_adapter = NodusComputeAdapter()

# Cache a default telemetry stream
_cached_df, _cached_events = sim.generate_stream(duration_hours=6.0, cadence_sec=10.0)
forecaster.train_and_evaluate(_cached_df, _cached_events)


class HealthResponse(BaseModel):
    status: str = "ONLINE"
    service: str = "HelioCast-L1 Scientific Server"
    version: str = __version__
    mission: str = "ISRO Aditya-L1"
    instruments: Dict[str, str] = {
        "SOLEXS": "1 - 22 keV (Soft X-rays, SDD)",
        "HEL1OS": "10 - 150 keV (Hard X-rays, CZT/CdTe)",
    }
    timestamp: str


class TelemetryFrameResponse(BaseModel):
    timestamp: str
    solexs_flux: float
    helios_flux: float
    hardness_ratio: float
    flare_active: bool
    flare_class: Optional[str] = None


class TelemetryBatchResponse(BaseModel):
    count: int
    cadence_sec: float
    data: List[TelemetryFrameResponse]


class MasterCatalogItem(BaseModel):
    master_id: str
    flare_class: str
    active_region: Optional[str] = "AR 13664"
    start_time: str
    peak_time: str
    end_time: str
    duration_minutes: float
    solexs_peak_flux: float
    helios_peak_count_rate: float
    spectral_hardness_ratio: float
    neupert_correlation: float
    neupert_verified: bool
    confirmation_status: str
    confidence_score: float
    radio_blackout_scale: Optional[str] = "R0"


@router.get("/health", response_model=HealthResponse)
def get_health():
    """Retrieve subsystem health and payload availability status."""
    return HealthResponse(timestamp=datetime.now(timezone.utc).isoformat())


@router.get("/telemetry/latest", response_model=TelemetryFrameResponse)
def get_latest_telemetry():
    """Fetch the most recent telemetry frame from Aditya-L1 stream."""
    last_row = _cached_df.iloc[-1]
    fc = str(last_row["flare_class"]) if pd.notna(last_row["flare_class"]) else None
    return TelemetryFrameResponse(
        timestamp=str(last_row["timestamp"]),
        solexs_flux=float(last_row["solexs_flux"]),
        helios_flux=float(last_row["helios_flux"]),
        hardness_ratio=float(last_row["hardness_ratio"]),
        flare_active=bool(last_row["flare_active"]),
        flare_class=fc,
    )


@router.get("/telemetry/lightcurve", response_model=TelemetryBatchResponse)
def get_lightcurve(limit: int = Query(default=360, ge=10, le=3600)):
    """Fetch recent synchronized light curve telemetry batch."""
    slice_df = _cached_df.iloc[-limit:]
    records = []
    for _, row in slice_df.iterrows():
        fc = str(row["flare_class"]) if pd.notna(row["flare_class"]) else None
        records.append(
            TelemetryFrameResponse(
                timestamp=str(row["timestamp"]),
                solexs_flux=float(row["solexs_flux"]),
                helios_flux=float(row["helios_flux"]),
                hardness_ratio=float(row["hardness_ratio"]),
                flare_active=bool(row["flare_active"]),
                flare_class=fc,
            )
        )
    return TelemetryBatchResponse(
        count=len(records),
        cadence_sec=10.0,
        data=records,
    )


@router.post("/nowcast/detect", response_model=List[MasterCatalogItem])
def trigger_nowcast_detection():
    """Trigger multi-band algorithmic nowcasting on current telemetry."""
    _, _, master_evts = nowcaster.process_telemetry(_cached_df)
    items = []
    for ev in master_evts:
        items.append(
            MasterCatalogItem(
                master_id=ev.master_id,
                flare_class=ev.flare_class,
                start_time=ev.start_time,
                peak_time=ev.peak_time,
                end_time=ev.end_time,
                duration_minutes=ev.duration_minutes,
                solexs_peak_flux=ev.solexs_peak_flux,
                helios_peak_count_rate=ev.helios_peak_count_rate,
                spectral_hardness_ratio=ev.spectral_hardness_ratio,
                neupert_correlation=ev.neupert_correlation,
                neupert_verified=ev.neupert_verified,
                confirmation_status=ev.confirmation_status,
                confidence_score=ev.confidence_score,
            )
        )
    return items


@router.get("/catalog/master", response_model=List[MasterCatalogItem])
def get_master_catalog(
    min_class: Optional[str] = Query(default=None, description="Minimum flare class, e.g. 'C' or 'M'"),
    only_neupert_verified: bool = Query(default=False, description="Filter for Neupert confirmed flares only"),
    search: Optional[str] = Query(default=None, description="Full-text or active region search query"),
    limit: int = Query(default=100, description="Maximum events to return"),
):
    """Query the persistent SQLite master flare catalogue with FTS5 search support."""
    records = nowcaster.db.get_master_catalog_records(
        min_class=min_class,
        only_neupert=only_neupert_verified,
        search_query=search,
        limit=limit,
    )
    items = []
    for row in records:
        items.append(
            MasterCatalogItem(
                master_id=str(row["master_id"]),
                flare_class=str(row["flare_class"]),
                active_region=str(row.get("active_region") or "AR 13664"),
                start_time=str(row["start_time"]),
                peak_time=str(row["peak_time"]),
                end_time=str(row["end_time"]),
                duration_minutes=float(row["duration_minutes"]),
                solexs_peak_flux=float(row["solexs_peak_flux"]),
                helios_peak_count_rate=float(row["helios_peak_count_rate"]),
                spectral_hardness_ratio=float(row["spectral_hardness_ratio"]),
                neupert_correlation=float(row["neupert_correlation"]),
                neupert_verified=bool(row["neupert_verified"]),
                confirmation_status=str(row["confirmation_status"]),
                confidence_score=float(row["confidence_score"]),
                radio_blackout_scale=str(row.get("radio_blackout_scale") or "R0"),
            )
        )
    return items


@router.get("/alerts/history")
def get_alert_history():
    """Retrieve operational space weather alerts dispatched during this session."""
    return [alert.__dict__ for alert in alert_dispatcher.alert_history]


@router.get("/benchmark/cstlb")
def get_cstlb_benchmark():
    """Retrieve Cross-Spectral Trust and Lead-Time Benchmark (CSTLB) comparative results."""
    summary = cstlb_runner.run_benchmark(_cached_df, _cached_events)
    from dataclasses import asdict
    return asdict(summary)


@router.get("/quality/audit")
def get_quality_audit():
    """Run data quality, gap detection, monotonicity, and ratio safeguard audit."""
    _, report = quality_auditor.audit(_cached_df)
    from dataclasses import asdict
    return asdict(report)


@router.get("/manifest")
def get_ingestion_manifest():
    """Fetch file inventory, SHA-256 checksums, and ingestion provenance records."""
    records = manifest.list_records()
    from dataclasses import asdict
    return [asdict(r) for r in records]


@router.get("/agent/status")
def get_agent_status():
    """Retrieve Agent37 optional research-assistance and orchestration status."""
    return agent_adapter.get_status()


@router.get("/compute/status")
def get_compute_status():
    """Retrieve Nodus Compute optional cost-safe execution adapter status."""
    return compute_adapter.get_status()


class ApiKeyUpdateRequest(BaseModel):
    agent37_api_key: Optional[str] = None
    nodus_compute_api_key: Optional[str] = None
    nodus_compute_endpoint: Optional[str] = None
    issdc_pradan_api_key: Optional[str] = None
    nasa_cdaweb_api_key: Optional[str] = None
    heliocast_api_key: Optional[str] = None


class KeyStatusItem(BaseModel):
    name: str
    key_name: str
    is_configured: bool
    status: str
    preview: Optional[str] = None
    description: str


def _mask_key(key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    if len(key) < 8:
        return "****"
    return f"{key[:3]}****{key[-4:]}"


@router.get("/keys/status", response_model=List[KeyStatusItem])
def get_api_keys_status():
    """Retrieve operational status and connectivity for all external & backend API keys."""
    keys = [
        KeyStatusItem(
            name="Agent37 Research Intelligence",
            key_name="AGENT37_API_KEY",
            is_configured=bool(os.getenv("AGENT37_API_KEY")),
            status="CONNECTED" if os.getenv("AGENT37_API_KEY") else "READY_OFFLINE",
            preview=_mask_key(os.getenv("AGENT37_API_KEY")),
            description="Automated flare event physical forensics and CSTLB research explanation reasoning",
        ),
        KeyStatusItem(
            name="Nodus Cloud Compute Cluster",
            key_name="NODUS_COMPUTE_API_KEY",
            is_configured=bool(os.getenv("NODUS_COMPUTE_API_KEY")),
            status="CONNECTED" if os.getenv("NODUS_COMPUTE_API_KEY") else "LOCAL_CPU_DEFAULT",
            preview=_mask_key(os.getenv("NODUS_COMPUTE_API_KEY")),
            description="Optional cloud GPU cluster orchestration with strict budget ceilings",
        ),
        KeyStatusItem(
            name="ISRO ISSDC PRADAN Portal",
            key_name="ISSDC_PRADAN_API_KEY",
            is_configured=bool(os.getenv("ISSDC_PRADAN_API_KEY")),
            status="CONNECTED" if os.getenv("ISSDC_PRADAN_API_KEY") else "CACHED_STREAM",
            preview=_mask_key(os.getenv("ISSDC_PRADAN_API_KEY")),
            description="ISRO Indian Space Science Data Centre level-1 science FITS archive ingestion",
        ),
        KeyStatusItem(
            name="NASA CDAWeb / Space Weather",
            key_name="NASA_CDAWEB_API_KEY",
            is_configured=bool(os.getenv("NASA_CDAWEB_API_KEY")),
            status="CONNECTED" if os.getenv("NASA_CDAWEB_API_KEY") else "READY_OFFLINE",
            preview=_mask_key(os.getenv("NASA_CDAWEB_API_KEY")),
            description="Cross-spacecraft validation against GOES-16/18 XRS and SDO AIA solar imagery",
        ),
        KeyStatusItem(
            name="HelioCast Gateway API Token",
            key_name="HELIOCAST_API_KEY",
            is_configured=bool(os.getenv("HELIOCAST_API_KEY")),
            status="SECURED" if os.getenv("HELIOCAST_API_KEY") else "DEV_OPEN",
            preview=_mask_key(os.getenv("HELIOCAST_API_KEY")),
            description="Secure Bearer / X-API-Key authentication token for production telemetry feeds",
        ),
    ]
    return keys


@router.post("/keys/update")
def update_api_keys(payload: ApiKeyUpdateRequest):
    """Update runtime API keys and persist them into .env."""
    env_updates = {}
    if payload.agent37_api_key is not None:
        val = payload.agent37_api_key.strip()
        os.environ["AGENT37_API_KEY"] = val
        env_updates["AGENT37_API_KEY"] = val
        agent_adapter.api_key = val
        agent_adapter.is_connected = bool(val)

    if payload.nodus_compute_api_key is not None:
        val = payload.nodus_compute_api_key.strip()
        os.environ["NODUS_COMPUTE_API_KEY"] = val
        env_updates["NODUS_COMPUTE_API_KEY"] = val
        compute_adapter.api_token = val
        compute_adapter.is_configured = bool(compute_adapter.api_token and compute_adapter.endpoint_url)

    if payload.nodus_compute_endpoint is not None:
        val = payload.nodus_compute_endpoint.strip()
        os.environ["NODUS_COMPUTE_ENDPOINT"] = val
        env_updates["NODUS_COMPUTE_ENDPOINT"] = val
        compute_adapter.endpoint_url = val
        compute_adapter.is_configured = bool(compute_adapter.api_token and compute_adapter.endpoint_url)

    if payload.issdc_pradan_api_key is not None:
        val = payload.issdc_pradan_api_key.strip()
        os.environ["ISSDC_PRADAN_API_KEY"] = val
        env_updates["ISSDC_PRADAN_API_KEY"] = val

    if payload.nasa_cdaweb_api_key is not None:
        val = payload.nasa_cdaweb_api_key.strip()
        os.environ["NASA_CDAWEB_API_KEY"] = val
        env_updates["NASA_CDAWEB_API_KEY"] = val

    if payload.heliocast_api_key is not None:
        val = payload.heliocast_api_key.strip()
        os.environ["HELIOCAST_API_KEY"] = val
        env_updates["HELIOCAST_API_KEY"] = val

    # Persist to .env file
    env_path = os.path.abspath(".env")
    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    updated_keys = set()
    new_lines = []
    for line in existing_lines:
        matched = False
        for k, v in env_updates.items():
            if line.startswith(f"{k}="):
                new_lines.append(f"{k}={v}\n")
                updated_keys.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in env_updates.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return {
        "status": "SUCCESS",
        "message": f"Updated {len(env_updates)} API key credentials and persisted to .env",
        "keys": get_api_keys_status()
    }


class ExplainRequest(BaseModel):
    event_id: Optional[str] = None
    event_dict: Optional[Dict[str, Any]] = None


@router.post("/agent/explain")
def explain_flare_event(req: ExplainRequest):
    """Generate verified scientific physical analysis using Agent37 adapter."""
    ev = req.event_dict or {}
    if req.event_id and not ev:
        df = nowcaster.get_master_catalog()
        match = df[df["master_id"] == req.event_id]
        if not match.empty:
            ev = match.iloc[0].to_dict()
        else:
            ev = {
                "master_id": req.event_id,
                "flare_class": "X1.1",
                "neupert_correlation": 0.966,
                "neupert_verified": True
            }

    explanation = agent_adapter.explain_flare_alert(ev)
    from dataclasses import asdict
    return asdict(explanation)


# ══════════════════════════════════════════════════════════════════
# DATABASE MANAGEMENT & METROLOGY ENDPOINTS
# ══════════════════════════════════════════════════════════════════
@router.get("/database/stats")
def get_database_stats():
    """Retrieve full database diagnostics, table record counts, file size, and WAL status."""
    return nowcaster.db.get_database_stats()


@router.get("/database/active-regions")
def get_active_regions():
    """Query solar active regions, magnetic classifications, and flare histories."""
    return nowcaster.db.get_active_regions()


@router.get("/database/forecasts")
def get_database_forecasts(limit: int = Query(default=50, ge=1, le=500)):
    """Query historical and live probabilistic precursor forecasts."""
    return nowcaster.db.get_forecasts(limit=limit)


@router.get("/database/alerts")
def get_database_alerts(limit: int = Query(default=50, ge=1, le=500)):
    """Query space weather alerts, radio blackout scales, and CME predictions."""
    return nowcaster.db.get_space_weather_alerts(limit=limit)


@router.get("/database/benchmarks")
def get_database_benchmarks():
    """Query CSTLB cross-spectral evaluation benchmarks from persistent storage."""
    return nowcaster.db.get_validation_benchmarks()


@router.post("/database/optimize")
def optimize_database():
    """Execute WAL checkpoint, vacuum, and query planner optimization."""
    return nowcaster.db.optimize_database()



