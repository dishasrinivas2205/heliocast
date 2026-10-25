"""
Heliophysics Forecast Verification & Skill Scores Module.
Computes True Skill Statistic (TSS), Heidke Skill Score (HSS),
Brier Skill Score (BSS), TPR, FPR, FAR, Precision, F1, and PR-AUC.
"""

from typing import Any, Dict, Optional, Tuple
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_skill_scores(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.50,
) -> Dict[str, float]:
    """
    Compute full suite of space weather forecast skill metrics.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob >= threshold).astype(int)

    # Calculate 2x2 confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    # Base rates
    total = len(y_true)
    climatology_prior = float(np.mean(y_true)) if total > 0 else 0.0

    # Sensitivity / True Positive Rate (TPR) / Recall
    tpr = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0

    # Specificity / True Negative Rate (TNR)
    tnr = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

    # False Positive Rate (FPR) = 1 - Specificity
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

    # False Alarm Ratio (FAR) = FP / (TP + FP)
    far = float(fp / (tp + fp)) if (tp + fp) > 0 else 0.0

    # Precision
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0

    # F1 Score
    f1 = float(2 * precision * tpr / (precision + tpr)) if (precision + tpr) > 0 else 0.0

    # True Skill Statistic (TSS) = TPR - FPR
    tss = float(tpr - fpr)

    # Heidke Skill Score (HSS)
    numerator = 2.0 * (tp * tn - fp * fn)
    denominator = (tp + fn) * (fn + tn) + (tp + fp) * (fp + tn)
    hss = float(numerator / denominator) if denominator > 0 else 0.0

    # Brier Score & Brier Skill Score (BSS) vs Climatology
    bs = float(brier_score_loss(y_true, y_prob)) if total > 0 else 0.0
    bs_clim = float(np.mean((y_true - climatology_prior) ** 2)) if total > 0 else 1.0
    bss = float(1.0 - (bs / max(1e-6, bs_clim)))

    # ROC-AUC and PR-AUC
    try:
        roc_auc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5
    except Exception:
        roc_auc = 0.5

    try:
        pr_auc = float(average_precision_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else climatology_prior
    except Exception:
        pr_auc = climatology_prior

    return {
        "TSS": round(tss, 4),
        "HSS": round(hss, 4),
        "TPR": round(tpr, 4),
        "FPR": round(fpr, 4),
        "FAR": round(far, 4),
        "Precision": round(precision, 4),
        "F1": round(f1, 4),
        "BrierScore": round(bs, 4),
        "BSS": round(bss, 4),
        "ROCAUC": round(roc_auc, 4),
        "PRAUC": round(pr_auc, 4),
        "ClimatologyPrior": round(climatology_prior, 4),
        "TP": int(tp),
        "FP": int(fp),
        "TN": int(tn),
        "FN": int(fn),
    }
