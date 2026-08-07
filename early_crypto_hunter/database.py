import sqlite3
import json
import os
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "crypto_hunter.db")

class Database:
    """
    Handles persistence of opportunities, predictions, alerts, and
    optimized AI scoring weights using a lightweight SQLite database.
    """
    def __init__(self):
        self.db_path = DB_PATH
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
                    predicted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved_at DATETIME
                )
            """)

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
                (ticker, name, entry_price, current_price, stop_loss, take_profit_1, take_profit_2, take_profit_3, confidence, status, net_return_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pred["ticker"],
                pred["name"],
                pred["entry_price"],
                pred["entry_price"], # initially current_price = entry_price
                pred["stop_loss"],
                pred["take_profit_1"],
                pred["take_profit_2"],
                pred["take_profit_3"],
                pred["confidence_pct"],
                "ACTIVE",
                0.0
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
        import datetime
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
