import os
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

# Setup template path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Ensure static assets exist if we mount
os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    db = Database()
    le = LearningEngine(db)

    # Get latest data
    opps = db.get_latest_opportunities()
    if not opps:
        # Auto scan on first page load if DB empty
        opps = trigger_full_scan(db)

    stats = le.calculate_performance_stats()
    weights = db.get_weights()
    alerts = db.get_latest_alerts(25)
    active_preds = db.get_active_predictions()
    wallet_portfolio = db.get_wallet_portfolio()
    wallet_trades = db.get_wallet_trades(20)

    # We will pass weights as JSON to template for Chart.js
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "opps": opps[:10], # Top 10 ranked
            "stats": stats,
            "weights": weights,
            "alerts": alerts,
            "active_preds": active_preds,
            "wallet_portfolio": wallet_portfolio,
            "wallet_trades": wallet_trades
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

    # Run optimize if resolved
    if resolved:
        le.optimize_ai_weights()

    stats = le.calculate_performance_stats()
    weights = db.get_weights()
    active_preds = db.get_active_predictions()
    alerts = db.get_latest_alerts(25)

    return JSONResponse({
        "status": "success",
        "resolved_count": len(resolved),
        "resolved_details": resolved,
        "stats": stats,
        "weights": weights,
        "active_preds": active_preds,
        "alerts": alerts
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

@app.get("/api/wallet/summary")
async def api_wallet_summary():
    db = Database()
    portfolio = db.get_wallet_portfolio()
    trades = db.get_wallet_trades(50)
    return JSONResponse({
        "portfolio": portfolio,
        "recent_trades": trades
    })

@app.post("/api/wallet/trade")
async def api_record_trade(request: Request):
    data = await request.json()
    ticker = data.get("ticker", "").strip()
    trade_type = data.get("trade_type", "BUY").strip().upper()
    price = float(data.get("price", 0.0))
    quantity = float(data.get("quantity", 0.0))
    notes = data.get("notes", "")

    if not ticker or price <= 0 or quantity <= 0:
        return JSONResponse({"error": "Invalid ticker, price, or quantity"}, status_code=400)

    db = Database()
    trade_id = db.record_wallet_trade(ticker, trade_type, price, quantity, notes)
    portfolio = db.get_wallet_portfolio()
    return JSONResponse({
        "status": "success",
        "trade_id": trade_id,
        "portfolio": portfolio
    })


def trigger_full_scan(db: Database):
    engine = DataEngine()
    scorer = AIScorer(weights=db.get_weights())
    alert_sys = AlertSystem(db)

    opps = engine.get_market_opportunities()
    analyzed = []

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

        # Save predictions for highly scoring and safe candidates
        if scores["overall_opportunity_score"] > 55.0 and risk_res["overall_risk_score"] < 60.0:
            db.save_prediction({
                "ticker": o["ticker"],
                "name": o["name"],
                "entry_price": o["price"],
                "stop_loss": plan["stop_loss"],
                "take_profit_1": plan["take_profit_1"],
                "take_profit_2": plan["take_profit_2"],
                "take_profit_3": plan["take_profit_3"],
                "confidence_pct": plan["confidence_pct"]
            })

        alert_sys.process_and_alert(o)
        analyzed.append(o)

    analyzed.sort(key=lambda x: x["scores"]["overall_opportunity_score"], reverse=True)
    return analyzed

if __name__ == "__main__":
    uvicorn.run("early_crypto_hunter.dashboard:app", host="0.0.0.0", port=8000, reload=True)
