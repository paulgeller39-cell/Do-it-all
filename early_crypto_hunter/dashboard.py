import os
import json
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import Database
from .data_engine import DataEngine
from .technical_analysis import TechnicalAnalysisEngine
from .risk_analysis import RiskAnalysisEngine
from .ai_scorer import AIScorer
from .alert_system import AlertSystem
from .learning_engine import LearningEngine

app = FastAPI(title="Early Crypto Hunter Dashboard", description="Elite Crypto Alpha Discovery Terminal")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    db = Database()
    le = LearningEngine(db)

    opps = db.get_latest_opportunities()
    if not opps:
        opps = trigger_full_scan(db)

    stats = le.calculate_performance_stats()
    weights = db.get_weights()
    alerts = db.get_latest_alerts(25)
    active_preds = db.get_active_predictions()
    stats_history = db.get_stats_history(30)
    all_preds = db.get_all_predictions()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "opps": opps[:10],
            "stats": stats,
            "weights": weights,
            "alerts": alerts,
            "active_preds": active_preds,
            "stats_history": stats_history,
            "all_preds": all_preds
        }
    )

@app.post("/api/scan")
async def api_scan():
    db = Database()
    opps = trigger_full_scan(db)
    le = LearningEngine(db)
    stats = le.calculate_performance_stats()
    return JSONResponse({
        "status": "success",
        "message": f"Successfully scanned and analyzed {len(opps)} opportunities.",
        "stats": stats,
        "opps": opps[:10]
    })

@app.post("/api/simulate")
async def api_simulate():
    db = Database()
    le = LearningEngine(db)
    resolved = le.update_predictions_simulation()

    if resolved:
        le.optimize_ai_weights()

    stats = le.calculate_performance_stats()
    weights = db.get_weights()
    active_preds = db.get_active_predictions()
    alerts = db.get_latest_alerts(25)
    stats_history = db.get_stats_history(30)

    return JSONResponse({
        "status": "success",
        "resolved_count": len(resolved),
        "resolved_details": resolved,
        "stats": stats,
        "weights": weights,
        "active_preds": active_preds,
        "alerts": alerts,
        "stats_history": stats_history
    })

@app.get("/api/opportunity/{ticker}")
async def api_opportunity(ticker: str):
    db = Database()
    opps = db.get_latest_opportunities()
    for o in opps:
        if o["ticker"].upper() == ticker.upper():
            return JSONResponse(o)
    return JSONResponse({"error": "Opportunity not found"}, status_code=404)

@app.get("/api/alerts")
async def api_get_alerts():
    db = Database()
    alerts = db.get_latest_alerts(30)
    return JSONResponse(alerts)

@app.get("/api/stats/history")
async def api_stats_history():
    db = Database()
    history = db.get_stats_history(50)
    return JSONResponse(history)

@app.get("/api/stats/breakdown")
async def api_stats_breakdown():
    db = Database()
    breakdown = db.get_stats_breakdown()
    return JSONResponse(breakdown)

@app.get("/api/predictions/all")
async def api_all_predictions():
    db = Database()
    preds = db.get_all_predictions()
    return JSONResponse(preds)


def trigger_full_scan(db: Database):
    engine = DataEngine()

    # Load narrative multipliers from settings if available
    narrative_mults = {}
    with db.get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'narrative_multipliers'")
        row = cursor.fetchone()
        if row:
            try:
                narrative_mults = json.loads(row[0])
            except Exception:
                pass

    scorer = AIScorer(weights=db.get_weights(), narrative_multipliers=narrative_mults)
    alert_sys = AlertSystem(db)

    opps = engine.get_market_opportunities()
    analyzed = []

    # Map current prices for active predictions if token address or symbol matches
    active_preds = db.get_active_predictions()
    price_map = {o["ticker"]: o["price"] for o in opps}

    for p in active_preds:
        if p["ticker"] in price_map:
            new_price = price_map[p["ticker"]]
            net_return = ((new_price - p["entry_price"]) / p["entry_price"]) * 100.0
            db.update_prediction_price(p["id"], new_price, "ACTIVE", net_return)

    for o in opps:
        ta_res = TechnicalAnalysisEngine.analyze(o["historical_prices"], o["historical_volumes"])
        risk_res = RiskAnalysisEngine.analyze(o)
        scores = scorer.compute_scores(ta_res, risk_res, o)
        plan = scorer.generate_trading_plan(o["price"], ta_res, risk_res, scores, o)

        o["ta"] = ta_res
        o["risk"] = risk_res
        o["scores"] = scores
        o["plan"] = plan

        db.save_opportunity(o)

        if scores["overall_opportunity_score"] > 55.0 and risk_res["overall_risk_score"] < 60.0:
            db.save_prediction({
                "ticker": o["ticker"],
                "name": o["name"],
                "entry_price": o["price"],
                "stop_loss": plan["stop_loss"],
                "take_profit_1": plan["take_profit_1"],
                "take_profit_2": plan["take_profit_2"],
                "take_profit_3": plan["take_profit_3"],
                "confidence_pct": plan["confidence_pct"],
                "narrative": o.get("narrative", "General"),
                "primary_signal": scores.get("primary_signal", "Standard Setup")
            })

        alert_sys.process_and_alert(o)
        analyzed.append(o)

    analyzed.sort(key=lambda x: x["scores"]["overall_opportunity_score"], reverse=True)
    return analyzed

if __name__ == "__main__":
    uvicorn.run("early_crypto_hunter.dashboard:app", host="0.0.0.0", port=8000, reload=True)
