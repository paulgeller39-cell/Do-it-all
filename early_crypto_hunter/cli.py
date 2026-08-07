import sys
import click
import json
from tabulate import tabulate # Fallback to standard manual formatting if tabulate isn't installed
from .database import Database
from .data_engine import DataEngine
from .technical_analysis import TechnicalAnalysisEngine
from .risk_analysis import RiskAnalysisEngine
from .ai_scorer import AIScorer
from .alert_system import AlertSystem
from .learning_engine import LearningEngine

def print_header(text: str):
    print("\n" + "="*60)
    print(f" {text.upper()} ".center(60, "#"))
    print("="*60)

@click.group()
def cli():
    """Early Crypto Hunter CLI - Elite AI Market Research Agent"""
    pass

@cli.command()
def scan():
    """Scan the market for the latest opportunities & trigger alerts."""
    print_header("Scanning Cryptocurrency Market")
    db = Database()
    engine = DataEngine()
    scorer = AIScorer(weights=db.get_weights())
    alert_sys = AlertSystem(db)

    print("[*] Fetching live data from public sources & DEX metrics...")
    opps = engine.get_market_opportunities()

    analyzed_opps = []
    print(f"[*] Analyzing {len(opps)} potential candidates with quantitative indicators...")
    for o in opps:
        # Run TA
        ta_res = TechnicalAnalysisEngine.analyze(o["historical_prices"], o["historical_volumes"])
        # Run Risk
        risk_res = RiskAnalysisEngine.analyze(o)
        # Compute AI scores
        scores = scorer.compute_scores(ta_res, risk_res, o)
        # Generate plan
        plan = scorer.generate_trading_plan(o["price"], ta_res, risk_res, scores, o)

        o["ta"] = ta_res
        o["risk"] = risk_res
        o["scores"] = scores
        o["plan"] = plan

        # Save to SQLite
        db.save_opportunity(o)

        # If opportunity is safe & promising, auto-log as a simulated prediction
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

        # Run real-time alerts scanner
        alert_sys.process_and_alert(o)
        analyzed_opps.append(o)

    # Sort opportunities by overall opportunity score
    analyzed_opps.sort(key=lambda x: x["scores"]["overall_opportunity_score"], reverse=True)

    print("\nRANKED TOP OPPORTUNITIES:")
    print(f"{'Rank':<5} | {'Symbol':<10} | {'Name':<20} | {'Price':<12} | {'AI Score':<10} | {'Risk Score':<10} | {'Narrative':<10}")
    print("-" * 85)
    for i, o in enumerate(analyzed_opps[:10]):
        rank_symbol = f"#{i+1}"
        if i == 0:
            rank_symbol = "👑 #1"
        print(f"{rank_symbol:<5} | {o['ticker']:<10} | {o['name'][:20]:<20} | ${o['price']:<11.4f} | {o['scores']['overall_opportunity_score']:<10.1f} | {o['risk']['overall_risk_score']:<10.1f} | {o['narrative']:<10}")

    print("\n[+] Market Scan Complete. Data saved to SQLite database. Alerts triggered where applicable.")

@cli.command()
def status():
    """Display prediction performance stats, active trades, and current model weights."""
    print_header("System Performance & Active Predictions")
    db = Database()
    le = LearningEngine(db)

    stats = le.calculate_performance_stats()
    weights = db.get_weights()

    print("\nCURRENT MODEL SCORING WEIGHTS:")
    for k, v in weights.items():
        print(f" - {k.capitalize():<12}: {v*100:.1f}%")

    print("\nPREDICTION PERFORMANCE STATS:")
    print(f" - Total Predictions Tracked : {stats['total_predictions']}")
    print(f" - Win Rate                 : {stats['win_rate']:.2f}%")
    print(f" - Average Return per Trade : {stats['average_return']:.2f}%")
    print(f" - Active Predictions       : {stats['active']}")
    print(f" - Hit Take Profit 1/2/3    : {stats['hit_tp1']} / {stats['hit_tp2']} / {stats['hit_tp3']}")
    print(f" - Hit Stop Loss            : {stats['hit_sl']}")
    print(f" - Expired / Exited         : {stats['expired']}")

    active_preds = db.get_active_predictions()
    if active_preds:
        print("\nACTIVE TRACKED PREDICTIONS:")
        print(f"{'Symbol':<10} | {'Entry Price':<12} | {'Current Price':<12} | {'SL':<10} | {'TP2':<10} | {'Net Return':<10}")
        print("-" * 75)
        for p in active_preds:
            net_ret = ((p["current_price"] - p["entry_price"]) / p["entry_price"]) * 100.0
            print(f"{p['ticker']:<10} | ${p['entry_price']:<11.4f} | ${p['current_price']:<11.4f} | ${p['stop_loss']:<9.4f} | ${p['take_profit_2']:<9.4f} | {net_ret:+.2f}%")
    else:
        print("\n[*] No active predictions. Run 'scan' to find and log high confidence setups.")

@cli.command()
def simulate():
    """Simulate next step of price changes, resolve trades, and optimize weights."""
    print_header("Simulating Price Progress & Learning Loop")
    db = Database()
    le = LearningEngine(db)

    print("[*] Progressing active prediction prices randomly/heuristically...")
    resolved = le.update_predictions_simulation()

    if resolved:
        print(f"\n[!] RESOLVED {len(resolved)} PREDICTIONS:")
        for r in resolved:
            symbol = r["ticker"]
            status = r["status"]
            ret = r["net_return"]
            icon = "📈" if "TP" in status else "📉"
            print(f" - {icon} {symbol}: {status} with net return of {ret:+.2f}%")

        print("\n[*] Optimizing AI scoring weights based on feedback outcomes...")
        old_weights = db.get_weights()
        new_weights = le.optimize_ai_weights()
        print("Updated Model Weights:")
        for k in new_weights:
            diff = (new_weights[k] - old_weights.get(k, 0.0)) * 100
            print(f" - {k.capitalize():<12}: {new_weights[k]*100:.1f}% ({diff:+.1f}%)")
    else:
        print("\n[*] Prices updated. No predictions resolved in this step. Keep simulating to hit targets!")

    stats = le.calculate_performance_stats()
    print(f"\n[+] Updated Performance Stats -> Win Rate: {stats['win_rate']:.1f}% | Total Tracked: {stats['total_predictions']}")

@cli.command()
def alerts():
    """View the latest triggered alerts."""
    print_header("Latest Triggered Alerts")
    db = Database()
    latest = db.get_latest_alerts(30)

    if latest:
        print(f"{'Time':<20} | {'Symbol':<8} | {'Type':<20} | {'Severity':<8} | {'Message'}")
        print("-" * 110)
        for a in latest:
            # Shorten message
            msg = a["message"]
            if len(msg) > 60:
                msg = msg[:57] + "..."
            print(f"{a['timestamp']:<20} | {a['ticker']:<8} | {a['alert_type']:<20} | {a['severity']:<8} | {msg}")
    else:
        print("[*] No alerts in logs. Run 'scan' to trigger automated alerts.")

if __name__ == "__main__":
    cli()
