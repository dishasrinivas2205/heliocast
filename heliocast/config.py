"""
Configuration Management for HelioCast-L1.
Validates all pipeline, detection, forecasting, and storage parameters using Pydantic v2.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional, Tuple
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """
    Central validated configuration for HelioCast-L1.
    Reads from environment variables, .env file, or provides scientifically verified defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General System
    heliocast_env: str = Field(default="development", description="Execution environment")
    log_level: str = Field(default="INFO", description="Global logging verbosity")

    # Observation Cadence & Instruments
    telemetry_cadence_sec: float = Field(
        default=10.0,
        description="Sampling interval of Aditya-L1 Level-1 light curves in seconds",
        ge=1.0,
        le=300.0,
    )
    solexs_energy_band_kev: Tuple[float, float] = Field(
        default=(1.0, 22.0),
        description="Soft X-ray energy passband of SoLEXS (Silicon Drift Detector)",
    )
    helios_energy_band_kev: Tuple[float, float] = Field(
        default=(10.0, 150.0),
        description="Hard X-ray energy passband of HEL1OS (CZT & CdTe detectors)",
    )

    # Step 3: Nowcaster Detection Thresholds
    quiet_sun_baseline_window_sec: int = Field(
        default=900,
        description="Rolling window for quiet-Sun background estimation (15 minutes)",
    )
    solexs_snr_multiplier: float = Field(
        default=4.0,
        description="MAD noise multiplier for SoLEXS flare detection threshold",
    )
    helios_snr_multiplier: float = Field(
        default=3.5,
        description="MAD noise multiplier for HEL1OS impulsive burst detection",
    )
    neupert_max_delay_sec: float = Field(
        default=180.0,
        description="Maximum physical time delay between Hard X-ray burst and Soft X-ray rise derivative",
    )
    neupert_min_correlation: float = Field(
        default=0.60,
        description="Minimum Pearson correlation coefficient between dF_SXR/dt and F_HXR for Neupert verification",
    )

    # Step 4: Forecasting & Lead Time
    forecast_lead_window_min: float = Field(
        default=30.0,
        description="Target lookahead precursor forecasting window in minutes",
        ge=5.0,
        le=120.0,
    )
    forecast_horizons_min: List[float] = Field(
        default_factory=lambda: [15.0, 30.0, 45.0],
        description="Quantifiable forecast lead-time evaluation horizons in minutes",
    )
    alert_probability_threshold: float = Field(
        default=0.60,
        description="Probability threshold to trigger a visual and operational space weather alert",
        ge=0.1,
        le=0.99,
    )
    min_precursor_history_steps: int = Field(
        default=60,
        description="Minimum consecutive valid history steps required for causal feature extraction (10 min @ 10s)",
    )

    # Data Storage Paths
    database_path: str = Field(
        default="data/catalog/aditya_flares.db",
        description="Path to SQLite master flare database",
    )
    raw_data_dir: str = Field(
        default="data/raw",
        description="Path to directory for raw ISSDC PRADAN Level-1 FITS files",
    )
    sample_data_dir: str = Field(
        default="data/sample",
        description="Path to sample FITS telemetry files",
    )
    outputs_dir: str = Field(
        default="outputs",
        description="Directory for generated reports, catalogs, and metrics",
    )

    # API & Service
    api_host: str = Field(default="0.0.0.0", description="FastAPI host")
    api_port: int = Field(default=8000, description="FastAPI listening port")
    api_reload: bool = Field(default=False, description="Hot reload flag")

    # Space Weather Alert Webhook
    webhook_alert_enabled: bool = Field(default=False, description="Send alert payload to external URL")
    webhook_alert_url: Optional[str] = Field(default=None, description="External endpoint for alert dispatch")

    @field_validator("forecast_lead_window_min")
    @classmethod
    def validate_lead_window(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Lead window must be strictly positive")
        return v

    def ensure_directories(self) -> None:
        """Create all necessary runtime directories."""
        for path_str in [
            Path(self.database_path).parent,
            Path(self.raw_data_dir),
            Path(self.sample_data_dir),
            Path(self.outputs_dir),
        ]:
            path_str.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> AppSettings:
    """Retrieve cached global application settings."""
    settings = AppSettings()
    settings.ensure_directories()
    return settings
