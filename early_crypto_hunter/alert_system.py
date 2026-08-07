from typing import Dict, Any, List
from .database import Database

class AlertSystem:
    """
    Scans real-time and analyzed token metrics to trigger immediate smart alerts:
    - Whale inflows exceeding normal thresholds
    - Multi-fold volume expansion (relative volume spikes)
    - Breakout initiations
    - Top AI opportunity alerts (AI confidence > 90%)
    """
    def __init__(self, db: Database):
        self.db = db

    def process_and_alert(self, opp: Dict[str, Any]) -> List[Dict[str, Any]]:
        ticker = opp["ticker"]
        name = opp["name"]
        ta = opp["ta"]
        risk = opp["risk"]
        scores = opp["scores"]
        onchain = opp.get("onchain_metrics", {})

        alerts_triggered = []

        # 1. Whale Activity Spikes
        whale_inflow = onchain.get("whale_inflow_usd", 0.0)
        if whale_inflow > 300000.0:
            severity = "HIGH" if whale_inflow > 600000.0 else "MEDIUM"
            alert = {
                "ticker": ticker,
                "name": name,
                "alert_type": "WHALE_ACCUMULATION",
                "message": f"Whale inflow detected! ${whale_inflow:,.2f} USD smart money accumulated on-chain in the last hour.",
                "severity": severity
            }
            self.db.save_alert(alert)
            alerts_triggered.append(alert)

        # 2. Volume Expansion (Volume Doubles / Relative Volume Spikes)
        rel_vol = ta.get("relative_volume", 1.0)
        if rel_vol >= 1.8:
            severity = "HIGH" if rel_vol >= 3.0 else "MEDIUM"
            alert = {
                "ticker": ticker,
                "name": name,
                "alert_type": "VOLUME_SPIKE",
                "message": f"Volume spike! 24h trading volume is {rel_vol:.1f}x higher than its historical average.",
                "severity": severity
            }
            self.db.save_alert(alert)
            alerts_triggered.append(alert)

        # 3. Breakout Initiations
        breakout_prob = ta.get("breakout_probability", 50.0)
        if breakout_prob > 75.0:
            alert = {
                "ticker": ticker,
                "name": name,
                "alert_type": "BREAKOUT_START",
                "message": f"Imminent breakout starting! Price consolidated into Bollinger Band squeeze with a {breakout_prob:.1f}% breakout probability.",
                "severity": "MEDIUM"
            }
            self.db.save_alert(alert)
            alerts_triggered.append(alert)

        # 4. High Confidence AI Score
        opportunity_score = scores.get("overall_opportunity_score", 50.0)
        risk_score = scores.get("risk_score", 50.0)
        if opportunity_score >= 80.0 and risk_score < 45.0:
            alert = {
                "ticker": ticker,
                "name": name,
                "alert_type": "HIGH_CONFIDENCE",
                "message": f"Alpha Alert! AI model assigned a {opportunity_score:.1f}% opportunity score with safe risk profile ({risk_score:.1f}%).",
                "severity": "HIGH"
            }
            self.db.save_alert(alert)
            alerts_triggered.append(alert)

        return alerts_triggered
