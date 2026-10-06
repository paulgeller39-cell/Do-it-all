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
        # Clear wallet_trades table before each test for test isolation
        with self.db.get_conn() as conn:
            conn.cursor().execute("DELETE FROM wallet_trades")
            conn.commit()
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

    def test_wallet_trade_tracking(self):
        # Record BUY trade
        trade_id1 = self.db.record_wallet_trade("NEOAI", "BUY", price=0.05, quantity=1000.0, notes="Early launch entry")
        self.assertGreater(trade_id1, 0)

        # Record SELL trade
        trade_id2 = self.db.record_wallet_trade("NEOAI", "SELL", price=0.10, quantity=500.0, notes="Taking partial 2x profits")
        self.assertGreater(trade_id2, 0)

        trades = self.db.get_wallet_trades(10)
        self.assertGreaterEqual(len(trades), 2)

        portfolio = self.db.get_wallet_portfolio()
        self.assertIn("NEOAI", portfolio["positions"])
        pos = portfolio["positions"]["NEOAI"]
        self.assertAlmostEqual(pos["quantity"], 500.0)
        self.assertAlmostEqual(pos["realized_pnl"], 25.0) # (0.10 - 0.05) * 500

    def test_wallet_api_endpoints(self):
        client = TestClient(app)

        # Test POST /api/wallet/trade
        payload = {
            "ticker": "PUMPX",
            "trade_type": "BUY",
            "price": 0.02,
            "quantity": 5000.0,
            "notes": "Testing API record"
        }
        res = client.post("/api/wallet/trade", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("portfolio", data)

        # Test GET /api/wallet/summary
        res_summary = client.get("/api/wallet/summary")
        self.assertEqual(res_summary.status_code, 200)
        summary_data = res_summary.json()
        self.assertIn("portfolio", summary_data)
        self.assertIn("recent_trades", summary_data)

if __name__ == "__main__":
    unittest.main()
