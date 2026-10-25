"""
Precursor Forecasting Pipeline Orchestrator for Aditya-L1.
Handles ground-truth horizon labeling, causal dataset generation,
model training, chronological validation, and real-time probability inference.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from heliocast.forecaster.features import PrecursorFeatureExtractor
from heliocast.forecaster.lead_time import LeadTimeEstimator, LeadTimeRecord
from heliocast.forecaster.models import SolarFlarePredictor
from heliocast.logging import get_logger

logger = get_logger("heliocast.forecaster.pipeline")


@dataclass
class ForecastResult:
    """Consolidated forecasting run outputs."""
    probabilities: np.ndarray
    lead_times: List[LeadTimeRecord]
    metrics: Dict[str, float]
    feature_importances: Dict[str, float]
    horizon_minutes: float


class FlareForecastingPipeline:
    """
    End-to-end precursor flare forecasting engine.
    """

    def __init__(
        self,
        horizon_minutes: float = 30.0,
        cadence_sec: float = 10.0,
        alert_threshold: float = 0.60,
        model_type: str = "random_forest",
    ):
        self.horizon_minutes = horizon_minutes
        self.cadence_sec = cadence_sec
        self.alert_threshold = alert_threshold
        self.model_type = model_type

        self.extractor = PrecursorFeatureExtractor(cadence_sec=cadence_sec)
        self.model = SolarFlarePredictor(model_type=model_type)
        self.lead_time_estimator = LeadTimeEstimator(alert_threshold=alert_threshold)

    def generate_labels(
        self,
        telemetry_df: pd.DataFrame,
        flare_events: List[Dict[str, Any]],
    ) -> np.ndarray:
        """
        Create binary labels indicating if a flare peak occurs within the lookahead horizon [t, t + H].
        """
        timestamps = pd.to_datetime(telemetry_df["timestamp"], utc=True)
        y = np.zeros(len(telemetry_df), dtype=int)
        horizon_delta = pd.Timedelta(minutes=self.horizon_minutes)

        for fl in flare_events:
            peak_dt = pd.to_datetime(fl.get("peak_time"), utc=True)
            # Active lookahead window: any step where peak is between now and now + horizon
            mask = (timestamps <= peak_dt) & (timestamps >= peak_dt - horizon_delta)
            y[mask.to_numpy()] = 1

        return y

    def train_and_evaluate(
        self,
        train_df: pd.DataFrame,
        train_events: List[Dict[str, Any]],
        test_df: Optional[pd.DataFrame] = None,
        test_events: Optional[List[Dict[str, Any]]] = None,
    ) -> ForecastResult:
        """
        Train precursor predictor and evaluate skill scores on holdout partition.
        """
        # 1. Feature Extraction
        X_train = self.extractor.extract_features(train_df)
        y_train = self.generate_labels(train_df, train_events)

        # 2. Train Model
        self.model.fit(X_train, y_train)

        # 3. Test Evaluation
        eval_df = test_df if test_df is not None else train_df
        eval_events = test_events if test_events is not None else train_events

        X_eval = self.extractor.extract_features(eval_df)
        y_eval = self.generate_labels(eval_df, eval_events)
        probs = self.model.predict_proba(X_eval)

        # 4. Heliophysics Skill Scores
        from heliocast.evaluation.skill_scores import evaluate_skill_scores
        metrics = evaluate_skill_scores(y_eval, probs, threshold=self.alert_threshold)

        # 5. Empirical Lead-Time Computation
        lead_times = self.lead_time_estimator.evaluate(eval_df, probs, eval_events)

        importances = self.model.get_feature_importances()

        logger.info(
            f"Forecasting evaluation completed: TSS={metrics.get('TSS', 0.0):.4f}, "
            f"HSS={metrics.get('HSS', 0.0):.4f}, TPR={metrics.get('TPR', 0.0)*100:.1f}%, "
            f"FAR={metrics.get('FAR', 0.0)*100:.1f}%"
        )

        return ForecastResult(
            probabilities=probs,
            lead_times=lead_times,
            metrics=metrics,
            feature_importances=importances,
            horizon_minutes=self.horizon_minutes,
        )

    def predict_stream(self, stream_df: pd.DataFrame) -> np.ndarray:
        """
        Inference on streaming or newly arrived telemetry frames.
        """
        X = self.extractor.extract_features(stream_df)
        return self.model.predict_proba(X)
