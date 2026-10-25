"""
Space Weather Alert Dispatcher & Spacecraft Safe-Mode Directives for Aditya-L1.
Issues automated early warnings and confirmed flare alerts for orbital assets.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import requests

from heliocast.logging import get_logger

logger = get_logger("heliocast.alerts.dispatcher")


@dataclass
class SpaceWeatherAlert:
    """Standardized space weather alert bulletin."""
    alert_id: str
    alert_type: str             # FORECAST_EARLY_WARNING, NOWCAST_CONFIRMED
    severity: str               # ADVISORY, WATCH, WARNING, CRITICAL
    flare_class: str
    timestamp: str
    lead_time_minutes: Optional[float]
    confidence_score: float
    neupert_verified: bool
    directive: str
    recipients: List[str]


class AlertDispatcher:
    """
    Manages generation, formatting, and dispatch of operational space weather alerts.
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self.alert_history: List[SpaceWeatherAlert] = []

    def dispatch_forecast_warning(
        self,
        predicted_class: str,
        lead_time_minutes: float,
        confidence: float,
        imminent_time: str,
    ) -> SpaceWeatherAlert:
        """
        Trigger an early warning when precursor models forecast a high-class eruption.
        """
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        alert_id = f"ALERT-FC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        if predicted_class.startswith("X"):
            severity = "CRITICAL"
            directive = (
                f"CRITICAL ISRO DIRECTIVE: Imminent {predicted_class} solar flare forecasted at Aditya-L1. "
                f"Estimated lead time: {lead_time_minutes:.1f} minutes. "
                f"Mandatory action: Place sensitive spacecraft star sensors into safe-hold; alert terrestrial grid operators."
            )
        elif predicted_class.startswith("M"):
            severity = "WARNING"
            directive = (
                f"SPACE WEATHER WARNING: {predicted_class} solar flare precursor detected. "
                f"Lead time buffer: {lead_time_minutes:.1f} minutes. "
                f"Advise standby for high-frequency radio blackouts (R1-R2 scale)."
            )
        else:
            severity = "ADVISORY"
            directive = f"Precursor activity detected: {predicted_class} event probable within {lead_time_minutes:.1f} minutes."

        alert = SpaceWeatherAlert(
            alert_id=alert_id,
            alert_type="FORECAST_EARLY_WARNING",
            severity=severity,
            flare_class=predicted_class,
            timestamp=now_utc,
            lead_time_minutes=lead_time_minutes,
            confidence_score=confidence,
            neupert_verified=False,
            directive=directive,
            recipients=["ISRO_ISTRAC", "ORBITAL_DYNAMICS", "ISSDC_PRADAN"],
        )

        self._record_and_send(alert)
        return alert

    def dispatch_nowcast_confirmed(
        self,
        flare_class: str,
        solexs_peak: float,
        helios_peak: float,
        neupert_verified: bool,
    ) -> SpaceWeatherAlert:
        """
        Trigger confirmed alert when nowcaster detects and classifies an ongoing flare.
        """
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        alert_id = f"ALERT-NC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        severity = "CRITICAL" if flare_class.startswith("X") else ("WARNING" if flare_class.startswith("M") else "ADVISORY")

        status_text = "Neupert Effect Confirmed (Non-Thermal Hard X-ray Burst Verified)" if neupert_verified else "Thermal Soft X-ray Transient"

        directive = (
            f"NOWCAST CONFIRMED: Aditya-L1 payloads registered {flare_class} solar flare. "
            f"SoLEXS Peak: {solexs_peak:.1f} count/s, HEL1OS Peak: {helios_peak:.1f} count/s. "
            f"{status_text}. Ingesting to ISSDC Master Flare Catalogue."
        )

        alert = SpaceWeatherAlert(
            alert_id=alert_id,
            alert_type="NOWCAST_CONFIRMED",
            severity=severity,
            flare_class=flare_class,
            timestamp=now_utc,
            lead_time_minutes=0.0,
            confidence_score=0.98 if neupert_verified else 0.75,
            neupert_verified=neupert_verified,
            directive=directive,
            recipients=["ISRO_ISTRAC", "SPACE_WEATHER_SENTINEL"],
        )

        self._record_and_send(alert)
        return alert

    def _record_and_send(self, alert: SpaceWeatherAlert) -> None:
        """Store in history and attempt webhook dispatch if configured."""
        self.alert_history.append(alert)
        logger.info(f"[{alert.severity}] {alert.alert_type}: {alert.directive}")

        if self.webhook_url:
            try:
                requests.post(self.webhook_url, json=asdict(alert), timeout=3.0)
            except Exception as e:
                logger.warning(f"Failed to post alert to webhook {self.webhook_url}: {e}")
