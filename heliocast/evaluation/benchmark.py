"""
Automated Model Benchmarking & Operational Comparison Subsystem.
Compares HelioCast-L1 models against Climatology and Persistence baselines.
"""

from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from heliocast.evaluation.skill_scores import evaluate_skill_scores
from heliocast.forecaster.features import PrecursorFeatureExtractor
from heliocast.forecaster.models import SolarFlarePredictor


class ForecastBenchmarkSuite:
    """
    Evaluates and compares multiple forecasting models on identical telemetry splits.
    """

    def __init__(self, cadence_sec: float = 10.0, alert_threshold: float = 0.60):
        self.cadence_sec = cadence_sec
        self.alert_threshold = alert_threshold
        self.extractor = PrecursorFeatureExtractor(cadence_sec=cadence_sec)

    def run_benchmark(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
    ) -> pd.DataFrame:
        """
        Run side-by-side benchmark comparison.
        """
        prior_rate = float(np.mean(y_train))
        results = []

        # 1. Climatological Baseline
        probs_clim = np.full(len(y_test), prior_rate)
        metrics_clim = evaluate_skill_scores(y_test, probs_clim, threshold=self.alert_threshold)
        metrics_clim["Model"] = "Climatology (Prior Rate)"
        results.append(metrics_clim)

        # 2. Persistence Baseline
        probs_persist = np.roll(y_test, 1)
        probs_persist[0] = 0
        metrics_persist = evaluate_skill_scores(y_test, probs_persist, threshold=self.alert_threshold)
        metrics_persist["Model"] = "Persistence Baseline"
        results.append(metrics_persist)

        # 3. Logistic Regression
        lr = SolarFlarePredictor(model_type="logistic_regression")
        lr.fit(X_train, y_train)
        probs_lr = lr.predict_proba(X_test)
        metrics_lr = evaluate_skill_scores(y_test, probs_lr, threshold=self.alert_threshold)
        metrics_lr["Model"] = "Calibrated Logistic Regression"
        results.append(metrics_lr)

        # 4. Random Forest
        rf = SolarFlarePredictor(model_type="random_forest")
        rf.fit(X_train, y_train)
        probs_rf = rf.predict_proba(X_test)
        metrics_rf = evaluate_skill_scores(y_test, probs_rf, threshold=self.alert_threshold)
        metrics_rf["Model"] = "Random Forest Ensemble (HelioCast)"
        results.append(metrics_rf)

        # 5. Gradient Boosting
        gb = SolarFlarePredictor(model_type="gradient_boosting")
        gb.fit(X_train, y_train)
        probs_gb = gb.predict_proba(X_test)
        metrics_gb = evaluate_skill_scores(y_test, probs_gb, threshold=self.alert_threshold)
        metrics_gb["Model"] = "Gradient Boosted Trees"
        results.append(metrics_gb)

        df_bench = pd.DataFrame(results)
        cols = ["Model", "TSS", "HSS", "TPR", "FPR", "FAR", "Precision", "BrierScore", "BSS", "ROCAUC"]
        return df_bench[cols]
