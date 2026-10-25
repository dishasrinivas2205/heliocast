"""
Causal Heliophysical Precursor Feature Extraction Engine for Aditya-L1.
Extracts strictly backward-looking time-series features with zero lookahead leakage.
Supports modality-specific feature sets: SoLEXS-only, HEL1OS-only, and Combined Fusion.
"""

from typing import List, Optional, Tuple
import numpy as np
import pandas as pd

from heliocast.logging import get_logger

logger = get_logger("heliocast.forecaster.features")

SOLEXS_FEATURE_NAMES = [
    "solexs_flux_current",
    "solexs_grad_short",
    "solexs_grad_long",
    "solexs_accel",
    "solexs_rolling_std_5m",
    "solexs_rolling_std_15m",
    "solexs_energy_integral_15m",
    "flux_ratio_to_baseline",
]

HELIOS_FEATURE_NAMES = [
    "helios_flux_current",
    "helios_grad_short",
    "helios_rolling_std_5m",
    "helios_burst_energy_10m",
]

CROSS_SPECTRAL_NAMES = [
    "hardness_ratio_current",
    "hardness_ratio_mean_10m",
    "hardness_ratio_delta",
    "solexs_valid",
    "helios_valid",
]

FEATURE_NAMES = SOLEXS_FEATURE_NAMES + ["helios_flux_current", "hardness_ratio_current", "helios_grad_short", "helios_rolling_std_5m", "hardness_ratio_mean_10m", "hardness_ratio_delta"]


class PrecursorFeatureExtractor:
    """
    Computes causal physical precursor features for single-instrument and fused flare forecasting.
    """

    def __init__(self, cadence_sec: float = 10.0, min_denominator_threshold: float = 5.0):
        self.cadence_sec = cadence_sec
        self.min_denominator_threshold = min_denominator_threshold

    def extract_features(
        self,
        df: pd.DataFrame,
        modality: str = "combined",
    ) -> pd.DataFrame:
        """
        Extract causal features from telemetry dataframe for the specified instrument modality.
        Options: 'combined', 'solexs', 'helios'
        """
        n = len(df)
        features = pd.DataFrame(index=df.index)

        # 1. SoLEXS Soft X-Ray features
        if "solexs_flux" in df.columns:
            sxr = df["solexs_flux"].to_numpy(dtype=float)
            sxr_series = pd.Series(np.nan_to_num(sxr, nan=0.0))
            solexs_valid = pd.notna(df["solexs_flux"]) & (df["solexs_flux"] >= 0.0)
        else:
            sxr = np.zeros(n)
            sxr_series = pd.Series(sxr)
            solexs_valid = pd.Series(False, index=df.index)

        w_short = max(3, int(60.0 / self.cadence_sec))
        w_long = max(6, int(300.0 / self.cadence_sec))
        w_10m = max(8, int(600.0 / self.cadence_sec))
        w_15m = max(10, int(900.0 / self.cadence_sec))

        features["solexs_flux_current"] = sxr_series
        features["solexs_grad_short"] = (sxr_series - sxr_series.shift(w_short)).fillna(0.0)
        features["solexs_grad_long"] = (sxr_series - sxr_series.shift(w_long)).fillna(0.0)

        # Second derivative / thermal acceleration
        grad1 = features["solexs_grad_short"]
        features["solexs_accel"] = (grad1 - grad1.shift(w_short)).fillna(0.0)

        features["solexs_rolling_std_5m"] = sxr_series.rolling(window=w_long, min_periods=1).std().fillna(0.0)
        features["solexs_rolling_std_15m"] = sxr_series.rolling(window=w_15m, min_periods=1).std().fillna(0.0)
        features["solexs_energy_integral_15m"] = sxr_series.rolling(window=w_15m, min_periods=1).sum().fillna(0.0) * self.cadence_sec

        rolling_base = sxr_series.rolling(window=w_15m * 2, min_periods=1).quantile(0.20).fillna(150.0)
        features["flux_ratio_to_baseline"] = sxr_series / np.maximum(rolling_base, 10.0)

        # 2. HEL1OS Hard X-Ray features
        if "helios_flux" in df.columns:
            hxr = df["helios_flux"].to_numpy(dtype=float)
            hxr_series = pd.Series(np.nan_to_num(hxr, nan=0.0))
            helios_valid = pd.notna(df["helios_flux"]) & (df["helios_flux"] >= 0.0)
        else:
            hxr = np.zeros(n)
            hxr_series = pd.Series(hxr)
            helios_valid = pd.Series(False, index=df.index)

        features["helios_flux_current"] = hxr_series
        features["helios_grad_short"] = (hxr_series - hxr_series.shift(w_short)).fillna(0.0)
        features["helios_rolling_std_5m"] = hxr_series.rolling(window=w_long, min_periods=1).std().fillna(0.0)
        features["helios_burst_energy_10m"] = hxr_series.rolling(window=w_10m, min_periods=1).sum().fillna(0.0) * self.cadence_sec

        # 3. Cross-Spectral Hardness Ratio (with numerical zero guards)
        safe_denom = np.maximum(sxr_series.to_numpy(), self.min_denominator_threshold)
        raw_hr = np.where(sxr_series > self.min_denominator_threshold, hxr_series.to_numpy() / safe_denom, 0.0)
        hr_series = pd.Series(np.nan_to_num(raw_hr, nan=0.0))

        features["hardness_ratio_current"] = hr_series
        features["hardness_ratio_mean_10m"] = hr_series.rolling(window=w_10m, min_periods=1).mean().fillna(0.0)
        features["hardness_ratio_delta"] = (hr_series - hr_series.shift(w_long)).fillna(0.0)

        features["solexs_valid"] = solexs_valid.astype(float)
        features["helios_valid"] = helios_valid.astype(float)

        features = features.replace([np.inf, -np.inf], 0.0).fillna(0.0)

        # Select columns by requested modality
        if modality.lower() in ["solexs", "solexs_only"]:
            return features[SOLEXS_FEATURE_NAMES]
        elif modality.lower() in ["helios", "helios_only"]:
            return features[HELIOS_FEATURE_NAMES]
        else:
            # Default combined features (compatible with existing code)
            return features[FEATURE_NAMES]
