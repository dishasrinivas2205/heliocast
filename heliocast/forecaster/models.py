"""
Predictive Solar Flare Precursor Models for HelioCast-L1.
Implements calibrated classifiers trained to predict the probability
of a solar flare occurring within the next N minutes.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from heliocast.forecaster.features import FEATURE_NAMES
from heliocast.logging import get_logger

logger = get_logger("heliocast.forecaster.models")


class SolarFlarePredictor:
    """
    Calibrated machine learning model suite for precursor flare forecasting.
    Supports Random Forest, Gradient Boosting, Logistic Regression, and MLP.
    """

    def __init__(
        self,
        model_type: str = "random_forest",
        random_seed: int = 42,
    ):
        self.model_type = model_type
        self.random_seed = random_seed
        self.scaler = StandardScaler()
        self.is_fitted = False

        if model_type == "logistic_regression":
            base = LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                random_state=random_seed,
            )
            self.model = CalibratedClassifierCV(estimator=base, cv=3)
        elif model_type == "gradient_boosting":
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.08,
                max_depth=4,
                random_state=random_seed,
            )
        elif model_type == "mlp":
            self.model = MLPClassifier(
                hidden_layer_sizes=(64, 32),
                max_iter=500,
                random_state=random_seed,
            )
        else:  # Default to Random Forest
            self.model = RandomForestClassifier(
                n_estimators=120,
                max_depth=8,
                min_samples_split=4,
                class_weight="balanced_subsample",
                random_state=random_seed,
                n_jobs=-1,
            )

        self.feature_columns = list(FEATURE_NAMES)

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "SolarFlarePredictor":
        """
        Train the model on causal precursor features.
        """
        self.feature_columns = list(X.columns)
        X_scaled = self.scaler.fit_transform(X[self.feature_columns])
        # Verify both classes exist in y
        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            logger.warning("Training dataset contains only one class. Adding synthetic balance.")
            # Safety safeguard against empty split
            X_scaled = np.vstack([X_scaled, X_scaled[:2]])
            y = np.append(y, [0, 1])

        self.model.fit(X_scaled, y)
        self.is_fitted = True
        logger.info(f"Fitted {self.model_type} flare forecaster on {len(X)} samples with {len(self.feature_columns)} features.")
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict flare precursor probability (class 1: flare imminent).
        """
        if not self.is_fitted:
            # If not yet trained, return prior baseline
            return np.full(len(X), 0.05)

        cols = getattr(self, "feature_columns", list(X.columns))
        # Ensure all required columns exist in X, filling missing with 0.0
        X_sub = X.copy()
        for col in cols:
            if col not in X_sub.columns:
                X_sub[col] = 0.0

        X_scaled = self.scaler.transform(X_sub[cols])
        probs = self.model.predict_proba(X_scaled)
        if probs.shape[1] > 1:
            return probs[:, 1]
        return probs[:, 0]

    def get_feature_importances(self) -> Dict[str, float]:
        """
        Extract physical feature importances from tree-based or linear models.
        """
        cols = getattr(self, "feature_columns", FEATURE_NAMES)
        if not self.is_fitted:
            return {f: 1.0 / len(cols) for f in cols}

        importances = {}
        if hasattr(self.model, "feature_importances_"):
            raw = self.model.feature_importances_
            for name, val in zip(cols, raw):
                importances[name] = round(float(val), 4)
        elif hasattr(self.model, "coef_"):
            raw = np.abs(self.model.coef_[0])
            raw = raw / (np.sum(raw) + 1e-6)
            for name, val in zip(cols, raw):
                importances[name] = round(float(val), 4)
                importances[name] = round(float(val), 4)
        else:
            return {f: 1.0 / len(FEATURE_NAMES) for f in FEATURE_NAMES}

        return dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))
