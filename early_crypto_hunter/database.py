import sqlite3
import json
import os
import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "crypto_hunter.db")

class Database:
    """
    Handles persistence of opportunities, predictions, alerts,
    stats history snapshots, and optimized AI scoring weights using SQLite.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_PATH
        self.init_db()

    def get_conn(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            # 1. Opportunities table (latest scan results)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    ticker TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    address TEXT NOT NULL,
                    price REAL,
                    market_cap REAL,
                    liquidity REAL,
                    volume_24h REAL,
                    narrative TEXT,
                    scores_json TEXT,
                    plan_json TEXT,
                    ta_json TEXT,
                    risk_json TEXT,
                    global_metrics_json TEXT,
                    onchain_metrics_json TEXT,
                    social_metrics_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Predictions tracker (historical predictions to evaluate model accuracy)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    entry_price REAL,
                    current_price REAL,
                    stop_loss REAL,
                    take_profit_1 REAL,
                    take_profit_2 REAL,
                    take_profit_3 REAL,
                    confidence REAL,
                    status TEXT DEFAULT 'ACTIVE', -- 'ACTIVE', 'HIT_TP1', 'HIT_TP2', 'HIT_TP3', 'HIT_SL', 'EXPIRED'
                    net_return_pct REAL DEFAULT 0.0,
                    narrative TEXT DEFAULT '',
                    primary_signal TEXT DEFAULT '',
                    predicted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved_at DATETIME
                )
            """)

            # Schema migration check for columns in predictions
            try:
                cursor.execute("ALTER TABLE predictions ADD COLUMN narrative TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass

            try:
                cursor.execute("ALTER TABLE predictions ADD COLUMN primary_signal TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass

            # 3. Alerts log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    alert_type TEXT NOT NULL, -- 'WHALE_ACCUMULATION', 'VOLUME_SPIKE', 'BREAKOUT_START', 'HIGH_CONFIDENCE'
                    message TEXT NOT NULL,
                    severity TEXT DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH'
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. Settings (weights and model states)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # 5. Stats History (performance snapshots over time)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stats_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    win_rate REAL NOT NULL,
                    total_predictions INTEGER NOT NULL,
                    average_return REAL NOT NULL,
                    active_count INTEGER NOT NULL,
                    hit_tp_count INTEGER NOT NULL,
                    hit_sl_count INTEGER NOT NULL,
                    best_narrative TEXT DEFAULT 'N/A',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Seed default weights if not present
            cursor.execute("SELECT value FROM settings WHERE key = 'ai_weights'")
            if not cursor.fetchone():
                default_weights = {
                    "technical": 0.25,
                    "social": 0.20,
                    "whale": 0.20,
                    "momentum": 0.15,
                    "profit": 0.20
                }
                cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("ai_weights", json.dumps(default_weights)))

            conn.commit()

    # Weight Management
    def get_weights(self) -> Dict[str, float]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = 'ai_weights'")
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return {
            "technical": 0.25,
            "social": 0.20,
            "whale": 0.20,
            "momentum": 0.15,
            "profit": 0.20
        }

    def save_weights(self, weights: Dict[str, float]):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("ai_weights", json.dumps(weights)))
            conn.commit()

    # Opportunities Persistence
    def save_opportunity(self, opp: Dict[str, Any]):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO opportunities
                (ticker, name, address, price, market_cap, liquidity, volume_24h, narrative, scores_json, plan_json, ta_json, risk_json, global_metrics_json, onchain_metrics_json, social_metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                opp["ticker"],
                opp["name"],
                opp["address"],
                opp["price"],
                opp["market_cap"],
                opp["liquidity"],
                opp["volume_24h"],
                opp["narrative"],
                json.dumps(opp["scores"]),
                json.dumps(opp["plan"]),
                json.dumps(opp["ta"]),
                json.dumps(opp["risk"]),
                json.dumps(opp.get("global_metrics", {})),
                json.dumps(opp.get("onchain_metrics", {})),
                json.dumps(opp.get("social_metrics", {}))
            ))
            conn.commit()

    def get_latest_opportunities(self) -> List[Dict[str, Any]]:
        with self.get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM opportunities ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            opps = []
            for r in rows:
                opps.append({
                    "ticker": r["ticker"],
                    "name": r["name"],
                    "address": r["address"],
                    "price": r["price"],
                    "market_cap": r["market_cap"],
                    "liquidity": r["liquidity"],
                    "volume_24h": r["volume_24h"],
                    "narrative": r["narrative"],
                    "scores": json.loads(r["scores_json"]),
                    "plan": json.loads(r["plan_json"]),
                    "ta": json.loads(r["ta_json"]),
                    "risk": json.loads(r["risk_json"]),
                    "global_metrics": json.loads(r["global_metrics_json"]) if r["global_metrics_json"] else {},
                    "onchain_metrics": json.loads(r["onchain_metrics_json"]) if r["onchain_metrics_json"] else {},
                    "social_metrics": json.loads(r["social_metrics_json"]) if r["social_metrics_json"] else {},
                    "timestamp": r["timestamp"]
                })
            return opps

    # Predictions Persistence
    def save_prediction(self, pred: Dict[str, Any]) -> int:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            # Prevent duplicating active predictions for the same ticker
            cursor.execute("SELECT id FROM predictions WHERE ticker = ? AND status = 'ACTIVE'", (pred["ticker"],))
            existing = cursor.fetchone()
            if existing:
                return existing[0]

            cursor.execute("""
                INSERT INTO predictions
                (ticker, name, entry_price, current_price, stop_loss, take_profit_1, take_profit_2, take_profit_3, confidence, status, net_return_pct, narrative, primary_signal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pred["ticker"],
                pred["name"],
                pred["entry_price"],
                pred["entry_price"], # initially current_price = entry_price
                pred["stop_loss"],
                pred["take_profit_1"],
                pred["take_profit_2"],
                pred["take_profit_3"],
                pred.get("confidence_pct", pred.get("confidence", 50.0)),
                "ACTIVE",
                0.0,
                pred.get("narrative", ""),
                pred.get("primary_signal", pred.get("signal", ""))
            ))
            conn.commit()
            return cursor.lastrowid or 0

    def get_active_predictions(self) -> List[Dict[str, Any]]:
        with self.get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM predictions WHERE status = 'ACTIVE'")
            return [dict(r) for r in cursor.fetchall()]

    def update_prediction_price(self, pred_id: int, new_price: float, status: str, net_return: float):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            if status != "ACTIVE":
                resolved_at = datetime.datetime.now().isoformat()
                cursor.execute("""
                    UPDATE predictions
                    SET current_price = ?, status = ?, net_return_pct = ?, resolved_at = ?
                    WHERE id = ?
                """, (new_price, status, net_return, resolved_at, pred_id))
            else:
                cursor.execute("""
                    UPDATE predictions
                    SET current_price = ?, net_return_pct = ?
                    WHERE id = ?
                """, (new_price, net_return, pred_id))
            conn.commit()

    def get_all_predictions(self) -> List[Dict[str, Any]]:
        with self.get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM predictions ORDER BY predicted_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    # Stats History Persistence
    def save_stats_snapshot(self, stats: Dict[str, Any]):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO stats_history
                (win_rate, total_predictions, average_return, active_count, hit_tp_count, hit_sl_count, best_narrative)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                stats.get("win_rate", 0.0),
                stats.get("total_predictions", 0),
                stats.get("average_return", 0.0),
                stats.get("active", 0),
                stats.get("hit_tp1", 0) + stats.get("hit_tp2", 0) + stats.get("hit_tp3", 0),
                stats.get("hit_sl", 0),
                stats.get("best_narrative", "N/A")
            ))
            conn.commit()

    def get_stats_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stats_history ORDER BY timestamp ASC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_stats_breakdown(self) -> Dict[str, Any]:
        """
        Returns performance breakdown aggregated by narrative and by primary signal.
        """
        all_preds = self.get_all_predictions()
        completed = [p for p in all_preds if p["status"] != "ACTIVE"]

        narrative_stats: Dict[str, Dict[str, Any]] = {}
        signal_stats: Dict[str, Dict[str, Any]] = {}

        for p in completed:
            nar = p.get("narrative") or "General"
            sig = p.get("primary_signal") or "Standard Setup"
            is_win = p["status"] in ("HIT_TP1", "HIT_TP2", "HIT_TP3")
            ret = p.get("net_return_pct", 0.0)

            # Narrative grouping
            if nar not in narrative_stats:
                narrative_stats[nar] = {"total": 0, "wins": 0, "total_return": 0.0}
            narrative_stats[nar]["total"] += 1
            if is_win:
                narrative_stats[nar]["wins"] += 1
            narrative_stats[nar]["total_return"] += ret

            # Signal grouping
            if sig not in signal_stats:
                signal_stats[sig] = {"total": 0, "wins": 0, "total_return": 0.0}
            signal_stats[sig]["total"] += 1
            if is_win:
                signal_stats[sig]["wins"] += 1
            signal_stats[sig]["total_return"] += ret

        # Format output
        by_narrative = {}
        for nar, data in narrative_stats.items():
            tot = data["total"]
            by_narrative[nar] = {
                "total_trades": tot,
                "win_rate": round((data["wins"] / tot) * 100.0, 1) if tot > 0 else 0.0,
                "avg_return": round(data["total_return"] / tot, 2) if tot > 0 else 0.0
            }

        by_signal = {}
        for sig, data in signal_stats.items():
            tot = data["total"]
            by_signal[sig] = {
                "total_trades": tot,
                "win_rate": round((data["wins"] / tot) * 100.0, 1) if tot > 0 else 0.0,
                "avg_return": round(data["total_return"] / tot, 2) if tot > 0 else 0.0
            }

        return {
            "by_narrative": by_narrative,
            "by_signal": by_signal
        }

    # Alerts Persistence
    def save_alert(self, alert: Dict[str, Any]):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alerts (ticker, name, alert_type, message, severity)
                VALUES (?, ?, ?, ?, ?)
            """, (
                alert["ticker"],
                alert["name"],
                alert["alert_type"],
                alert["message"],
                alert["severity"]
            ))
            conn.commit()

    def get_latest_alerts(self, limit: int = 40) -> List[Dict[str, Any]]:
        with self.get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]
