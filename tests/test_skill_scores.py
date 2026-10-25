"""
Tests for Heliophysics Skill Score Calculations.
"""

import unittest
import numpy as np

from heliocast.evaluation.skill_scores import evaluate_skill_scores


class TestSkillScores(unittest.TestCase):
    def test_perfect_prediction_scores(self):
        y_true = np.array([0, 0, 0, 1, 1, 1, 0, 1])
        y_prob = np.array([0.05, 0.1, 0.0, 0.95, 0.88, 0.99, 0.1, 0.9])

        metrics = evaluate_skill_scores(y_true, y_prob, threshold=0.50)
        self.assertEqual(metrics["TSS"], 1.0)
        self.assertEqual(metrics["HSS"], 1.0)
        self.assertEqual(metrics["TPR"], 1.0)
        self.assertEqual(metrics["FAR"], 0.0)
        self.assertEqual(metrics["Precision"], 1.0)

    def test_random_chance_scores(self):
        # When model has no skill (predicts constant prior)
        y_true = np.array([0, 0, 0, 0, 1, 1])
        y_prob = np.array([0.33, 0.33, 0.33, 0.33, 0.33, 0.33])

        metrics = evaluate_skill_scores(y_true, y_prob, threshold=0.50)
        self.assertEqual(metrics["TSS"], 0.0)
        self.assertEqual(metrics["HSS"], 0.0)


if __name__ == "__main__":
    unittest.main()
