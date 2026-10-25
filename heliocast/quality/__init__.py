"""
Aditya-L1 Scientific Data Quality & Verification Module.
Provides monotonicity checking, gap discovery, availability masking,
and ratio denominator safeguards for SoLEXS and HEL1OS observations.
"""

from heliocast.quality.audit import (
    QualityAuditReport,
    TelemetryQualityAuditor,
    safe_spectral_hardness_ratio,
)

__all__ = ["TelemetryQualityAuditor", "QualityAuditReport", "safe_spectral_hardness_ratio"]
