import unittest
import numpy as np
from fastapi.testclient import TestClient

from early_crypto_hunter.data_engine import DataEngine
from early_crypto_hunter.technical_analysis import TechnicalAnalysisEngine, calculate_ema
from early_crypto_hunter.risk_analysis import RiskAnalysisEngine
from early_crypto_hunter.ai_scorer import AIScorer
from early_crypto_hunter.database import Database
from early_crypto_hunter.dashboard import app

class TestEarlyCryptoHunter(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.engine = DataEngine()
        self.scorer = AIScorer()

    def test_ema_calculation(self):
        prices = [10.0, 11.0, 12.0, 11.0, 10.0]
        # Test custom EMA function directly
        import pandas as pd
        series = pd.Series(prices)
        ema_res = calculate_ema(series, 3)
        self.assertEqual(len(ema_res), len(prices))
        self.assertGreater(ema_res.iloc[-1], 0)

    def test_technical_analysis(self):
        prices = list(np.sin(np.linspace(0, 10, 100)) + 10.0)
        volumes = [1000.0] * 100
        ta_res = TechnicalAnalysisEngine.analyze(prices, volumes)

        # Verify required keys are present
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
            "liquidity": 5000.0, # extremely low, triggers risk
            "volume_24h": 100000.0,
            "narrative": "Meme"
        }
        risk_res = RiskAnalysisEngine.analyze(token_data)
        self.assertIn("rug_pull_probability", risk_res)
        self.assertIn("honeypot_probability", risk_res)
        self.assertIn("overall_risk_score", risk_res)

        # SCAMCOIN should have an elevated risk score
        self.assertGreater(risk_res["overall_risk_score"], 20.0)

    def test_ai_scorer_and_planner(self):
        ta = {
            "breakout_probability": 85.0,
            "rsi": 65.0,
            "relative_volume": 2.5,
            "atr": 0.1,
            "support_levels": [0.9]
        }
        risk = {"overall_risk_score": 35.0}
        token = {"ticker": "SOLAI", "narrative": "AI", "liquidity": 500000.0}

        scores = self.scorer.compute_scores(ta, risk, token)
        plan = self.scorer.generate_trading_plan(1.0, ta, risk, scores, token)

        self.assertIn("technical_score", scores)
        self.assertIn("overall_opportunity_score", scores)

        self.assertIn("suggested_entry", plan)
        self.assertIn("stop_loss", plan)
        self.assertIn("take_profit_1", plan)
        self.assertIn("take_profit_2", plan)
        self.assertIn("risk_reward_ratio", plan)

    def test_api_routes(self):
        client = TestClient(app)

        # Test GET /
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"EARLY CRYPTO HUNTER", response.content)

        # Test GET /api/alerts
        response = client.get("/api/alerts")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

        # Test POST /api/scan
        response = client.post("/api/scan")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("opps", data)
        self.assertEqual(len(data["opps"]), 10)

if __name__ == "__main__":
    unittest.main()
