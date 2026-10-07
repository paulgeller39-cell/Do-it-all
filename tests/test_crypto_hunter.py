import unittest
import numpy as np
import os
import tempfile
from fastapi.testclient import TestClient

from early_crypto_hunter.data_engine import DataEngine
from early_crypto_hunter.technical_analysis import TechnicalAnalysisEngine, calculate_ema
from early_crypto_hunter.risk_analysis import RiskAnalysisEngine
from early_crypto_hunter.ai_scorer import AIScorer
from early_crypto_hunter.database import Database
from early_crypto_hunter.learning_engine import LearningEngine
from early_crypto_hunter.dashboard import app

class TestEarlyCryptoHunter(unittest.TestCase):
    def setUp(self):
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.db = Database(db_path=self.temp_db_file.name)
        self.engine = DataEngine()
        self.scorer = AIScorer()
        self.learning_engine = LearningEngine(self.db)

    def tearDown(self):
        try:
            os.remove(self.temp_db_file.name)
        except Exception:
            pass

    def test_ema_calculation(self):
        prices = [10.0, 11.0, 12.0, 11.0, 10.0]
        import pandas as pd
        series = pd.Series(prices)
        ema_res = calculate_ema(series, 3)
        self.assertEqual(len(ema_res), len(prices))
        self.assertGreater(ema_res.iloc[-1], 0)

    def test_technical_analysis(self):
        prices = list(np.sin(np.linspace(0, 10, 100)) + 10.0)
        volumes = [1000.0] * 100
        ta_res = TechnicalAnalysisEngine.analyze(prices, volumes)

        self.assertIn("rsi", ta_res)
        self.assertIn("ema_9", ta_res)
        self.assertIn("ema_50", ta_res)
        self.assertIn("macd", ta_res)
        self.assertIn("bollinger_bands", ta_res)
        self.assertIn("fibonacci_levels", ta_res)
        self.assertIn("breakout_probability", ta_res)

    def test_risk_analysis(self):
        token_data = {
            "ticker": "SCAMCOIN",
            "liquidity": 5000.0,
            "volume_24h": 100000.0,
            "narrative": "Meme"
        }
        risk_res = RiskAnalysisEngine.analyze(token_data)
        self.assertIn("rug_pull_probability", risk_res)
        self.assertIn("honeypot_probability", risk_res)
        self.assertIn("overall_risk_score", risk_res)
        self.assertGreater(risk_res["overall_risk_score"], 20.0)

    def test_ai_scorer_and_narrative_multipliers(self):
        ta = {
            "breakout_probability": 85.0,
            "rsi": 65.0,
            "relative_volume": 2.5,
            "atr": 0.1,
            "support_levels": [0.9]
        }
        risk = {"overall_risk_score": 35.0}
        token = {"ticker": "SOLAI", "narrative": "AI", "liquidity": 500000.0}

        # Test base scorer
        scores_base = self.scorer.compute_scores(ta, risk, token)
        self.assertIn("technical_score", scores_base)
        self.assertIn("primary_signal", scores_base)

        # Test with narrative multiplier
        scorer_boosted = AIScorer(narrative_multipliers={"AI": 1.25})
        scores_boosted = scorer_boosted.compute_scores(ta, risk, token)
        self.assertGreater(scores_boosted["overall_opportunity_score"], scores_base["overall_opportunity_score"])

        plan = self.scorer.generate_trading_plan(1.0, ta, risk, scores_base, token)
        self.assertIn("suggested_entry", plan)
        self.assertIn("stop_loss", plan)
        self.assertIn("take_profit_1", plan)
        self.assertIn("take_profit_2", plan)

    def test_database_stats_tracking(self):
        # Save a prediction with narrative
        pred_id = self.db.save_prediction({
            "ticker": "TESTCOIN",
            "name": "Test Coin",
            "entry_price": 1.0,
            "stop_loss": 0.8,
            "take_profit_1": 1.2,
            "take_profit_2": 1.5,
            "take_profit_3": 2.0,
            "confidence_pct": 80.0,
            "narrative": "AI",
            "primary_signal": "Bollinger Breakout"
        })
        self.assertGreater(pred_id, 0)

        # Update prediction to resolved TP1
        self.db.update_prediction_price(pred_id, 1.2, "HIT_TP1", 20.0)

        # Verify stats breakdown
        breakdown = self.db.get_stats_breakdown()
        self.assertIn("by_narrative", breakdown)
        self.assertIn("AI", breakdown["by_narrative"])
        self.assertEqual(breakdown["by_narrative"]["AI"]["win_rate"], 100.0)

        # Save and verify stats snapshot
        self.db.save_stats_snapshot({
            "win_rate": 100.0,
            "total_predictions": 1,
            "average_return": 20.0,
            "active": 0,
            "hit_tp1": 1,
            "hit_tp2": 0,
            "hit_tp3": 0,
            "hit_sl": 0,
            "best_narrative": "AI"
        })
        history = self.db.get_stats_history()
        self.assertGreater(len(history), 0)
        self.assertEqual(history[-1]["best_narrative"], "AI")

    def test_api_routes(self):
        client = TestClient(app)

        # Test GET /
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"EARLY CRYPTO HUNTER", response.content)

        # Test GET /api/alerts
        response = client.get("/api/alerts")
        self.assertEqual(response.status_code, 200)

        # Test POST /api/scan
        response = client.post("/api/scan")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")

        # Test POST /api/simulate
        response = client.post("/api/simulate")
        self.assertEqual(response.status_code, 200)

        # Test GET /api/stats/history
        response = client.get("/api/stats/history")
        self.assertEqual(response.status_code, 200)

        # Test GET /api/stats/breakdown
        response = client.get("/api/stats/breakdown")
        self.assertEqual(response.status_code, 200)

        # Test GET /api/predictions/all
        response = client.get("/api/predictions/all")
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
