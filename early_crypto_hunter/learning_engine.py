import random
import json
import datetime
from typing import Dict, Any, List
from .database import Database

class LearningEngine:
    """
    Simulates price updates for logged active predictions, evaluates
    their success metrics (win rate, profit/loss, accuracy by narrative/signal),
    logs historical snapshots, and iteratively optimizes AI model weights
    and narrative multipliers to improve overall predictive accuracy.
    """
    def __init__(self, db: Database):
        self.db = db

    def update_predictions_simulation(self) -> List[Dict[str, Any]]:
        """
        Simulates price progression of currently active trades.
        Resolves predictions when they hit Take Profits or Stop Loss.
        Automatically logs a performance snapshot when trades resolve.
        """
        active_preds = self.db.get_active_predictions()
        resolved_trades = []

        for p in active_preds:
            current_price = p["current_price"]
            sl = p["stop_loss"]
            tp1 = p["take_profit_1"]
            tp2 = p["take_profit_2"]
            tp3 = p["take_profit_3"]

            # Simulate a realistic price fluctuation
            # There is a 60% chance of an upward bias for high-confidence coins
            bias = 0.05 if p["confidence"] > 65 else -0.02
            price_change_pct = random.uniform(-0.15, 0.25) + bias
            new_price = current_price * (1 + price_change_pct)
            if new_price <= 0:
                new_price = current_price * 0.1

            net_return_pct = ((new_price - p["entry_price"]) / p["entry_price"]) * 100.0

            status = "ACTIVE"
            if new_price >= tp3:
                status = "HIT_TP3"
                new_price = tp3 # capped at TP3
                net_return_pct = ((tp3 - p["entry_price"]) / p["entry_price"]) * 100.0
            elif new_price >= tp2:
                status = "HIT_TP2"
                new_price = tp2
                net_return_pct = ((tp2 - p["entry_price"]) / p["entry_price"]) * 100.0
            elif new_price >= tp1:
                status = "HIT_TP1"
            elif new_price <= sl:
                status = "HIT_SL"
                new_price = sl
                net_return_pct = ((sl - p["entry_price"]) / p["entry_price"]) * 100.0

            # 15% random chance of simulated natural trade expiration after a while
            if status == "ACTIVE" and random.random() < 0.15:
                status = "EXPIRED"

            self.db.update_prediction_price(p["id"], new_price, status, net_return_pct)

            if status != "ACTIVE":
                resolved_trades.append({
                    "id": p["id"],
                    "ticker": p["ticker"],
                    "status": status,
                    "net_return": net_return_pct
                })

        if resolved_trades:
            stats = self.calculate_performance_stats()
            self.db.save_stats_snapshot(stats)

        return resolved_trades

    def calculate_performance_stats(self) -> Dict[str, Any]:
        """
        Gathers comprehensive performance statistics for all tracked trades,
        including breakdown by narrative and primary technical signal.
        """
        all_preds = self.db.get_all_predictions()
        total_predictions = len(all_preds)
        breakdown = self.db.get_stats_breakdown()

        # Determine best narrative
        best_narrative = "N/A"
        by_narrative = breakdown.get("by_narrative", {})
        if by_narrative:
            best_narrative = max(by_narrative.keys(), key=lambda k: (by_narrative[k]["win_rate"], by_narrative[k]["avg_return"]))

        if total_predictions == 0:
            stats = {
                "total_predictions": 0,
                "win_rate": 0.0,
                "average_return": 0.0,
                "hit_tp3": 0,
                "hit_tp2": 0,
                "hit_tp1": 0,
                "hit_sl": 0,
                "expired": 0,
                "active": 0,
                "best_narrative": best_narrative,
                "breakdown": breakdown
            }
            return stats

        completed = [p for p in all_preds if p["status"] != "ACTIVE"]
        active = [p for p in all_preds if p["status"] == "ACTIVE"]

        hits = [p for p in completed if p["status"] in ("HIT_TP1", "HIT_TP2", "HIT_TP3")]
        losses = [p for p in completed if p["status"] == "HIT_SL"]

        win_rate = (len(hits) / len(completed)) * 100.0 if len(completed) > 0 else 0.0
        avg_return = sum(p["net_return_pct"] for p in completed) / len(completed) if len(completed) > 0 else 0.0

        stats = {
            "total_predictions": total_predictions,
            "win_rate": round(win_rate, 2),
            "average_return": round(avg_return, 2),
            "hit_tp3": len([p for p in completed if p["status"] == "HIT_TP3"]),
            "hit_tp2": len([p for p in completed if p["status"] == "HIT_TP2"]),
            "hit_tp1": len([p for p in completed if p["status"] == "HIT_TP1"]),
            "hit_sl": len(losses),
            "expired": len([p for p in completed if p["status"] == "EXPIRED"]),
            "active": len(active),
            "best_narrative": best_narrative,
            "breakdown": breakdown
        }

        return stats

    def optimize_ai_weights(self) -> Dict[str, float]:
        """
        Self-optimizing AI model training loop:
        Reviews resolved predictions, adjusts sub-score weights, and
        computes narrative quality multipliers to store in settings.
        """
        all_preds = self.db.get_all_predictions()
        completed = [p for p in all_preds if p["status"] in ("HIT_TP1", "HIT_TP2", "HIT_TP3", "HIT_SL")]

        weights = self.db.get_weights()
        if len(completed) < 3:
            return weights

        lr = 0.015 # learning rate
        avg_ret = sum(p["net_return_pct"] for p in completed) / len(completed)

        for name in list(weights.keys()):
            if avg_ret > 0:
                if name in ("technical", "profit"):
                    weights[name] += lr
                else:
                    weights[name] -= lr / 4.0
            else:
                if name in ("whale", "social"):
                    weights[name] += lr
                else:
                    weights[name] -= lr / 4.0

        # Renormalize weights so they sum up to exactly 1.0
        total_w = sum(weights.values())
        for k in weights:
            weights[k] = round(max(weights[k] / total_w, 0.05), 3)

        diff = round(1.0 - sum(weights.values()), 3)
        weights["technical"] = round(weights["technical"] + diff, 3)

        self.db.save_weights(weights)

        # Calculate and save Narrative Multipliers into settings
        breakdown = self.db.get_stats_breakdown()
        by_narrative = breakdown.get("by_narrative", {})
        narrative_multipliers = {}
        for nar, n_stats in by_narrative.items():
            wr = n_stats.get("win_rate", 50.0)
            avg_r = n_stats.get("avg_return", 0.0)
            # Base multiplier = 1.0; adjust up or down depending on win rate and avg return
            mult = 1.0 + ((wr - 50.0) / 100.0) + (avg_r / 200.0)
            narrative_multipliers[nar] = round(max(min(mult, 1.35), 0.70), 2)

        with self.db.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("narrative_multipliers", json.dumps(narrative_multipliers)))
            conn.commit()

        # Save stats snapshot to history
        stats = self.calculate_performance_stats()
        self.db.save_stats_snapshot(stats)

        return weights
