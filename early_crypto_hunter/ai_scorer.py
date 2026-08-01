import random
from typing import Dict, Any, List

class AIScorer:
    """
    Computes professional-grade AI scores for cryptocurrencies, including:
    - Technical Score
    - Social Score
    - Whale Score
    - Momentum Score
    - Risk Score
    - Profit Score
    - Overall Opportunity Score (weighted combination of the above)

    Generates tailored Trading Plans featuring suggested entry, stop loss,
    three take-profit levels, risk/reward ratios, and holding times.

    Supports dynamic feedback tuning (learning weights) from the database.
    """

    def __init__(self, weights: Dict[str, float] = None):
        # Default starting weights which add up to 100% (or 1.0)
        self.weights = weights or {
            "technical": 0.25,
            "social": 0.20,
            "whale": 0.20,
            "momentum": 0.15,
            "profit": 0.20
        }

    def compute_scores(self, ta_results: Dict[str, Any], risk_results: Dict[str, Any], token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates all sub-scores and the final aggregated Overall Opportunity Score.
        """
        # 1. Technical Score (0-100)
        # Driven by breakout probability, RSI momentum, alignment of price with EMA, etc.
        breakout_prob = ta_results.get("breakout_probability", 50.0)
        rsi = ta_results.get("rsi", 50.0)
        rsi_factor = 100.0 - abs(rsi - 60.0) * 2.0 # penalize extreme overbought/oversold, reward optimal bullish strength
        rsi_factor = min(max(rsi_factor, 0.0), 100.0)

        rel_vol = ta_results.get("relative_volume", 1.0)
        vol_factor = min(rel_vol * 30.0, 100.0) # higher relative volume is extremely bullish

        tech_score = (breakout_prob * 0.4) + (rsi_factor * 0.3) + (vol_factor * 0.3)
        tech_score = min(max(tech_score, 0.0), 100.0)

        # 2. Social Score (0-100)
        # Driven by Twitter mentions, Reddit sentiment, Github activity
        social_data = token_data.get("social_metrics", {})
        twitter_mentions = social_data.get("twitter_mentions", 1000)
        reddit_sent = social_data.get("reddit_sentiment", 0.5)
        github_commits = social_data.get("github_commits_24h", 5)

        # Twitter normalized score (say, log scale or cap at 15000 mentions)
        tw_score = min((twitter_mentions / 15000) * 100, 100)
        reddit_score = (reddit_sent + 1) * 50 # mapping [-1, 1] to [0, 100]
        github_score = min((github_commits / 45) * 100, 100)

        social_score = (tw_score * 0.5) + (reddit_score * 0.3) + (github_score * 0.2)
        social_score = min(max(social_score, 0.0), 100.0)

        # 3. Whale Score (0-100)
        # Based on simulated/detected smart money on-chain movements
        onchain = token_data.get("onchain_metrics", {})
        whale_inflow = onchain.get("whale_inflow_usd", 100000)
        whale_score = min((whale_inflow / 800000) * 100, 100)

        # 4. Momentum Score (0-100)
        # Based on 24h price changes, Fear & Greed index, chain activity
        price_change_24h = token_data.get("price_change_24h", 0.0)
        mom_price = min(max((price_change_24h + 20) * 0.8, 0.0), 100.0)

        fng = token_data.get("global_metrics", {}).get("fear_greed_index", 50)
        mom_score = (mom_price * 0.7) + (fng * 0.3)
        mom_score = min(max(mom_score, 0.0), 100.0)

        # 5. Risk Score (0-100)
        # Taken directly from our deep risk analysis engine
        risk_score = risk_results.get("overall_risk_score", 50.0)

        # 6. Profit Score (0-100)
        # High profit score when there is deep liquidity combined with explosive momentum and low risk.
        # It measures the upside potential relative to the risk.
        liquidity = token_data.get("liquidity", 100000)
        liq_factor = min((liquidity / 1500000) * 100, 100)

        profit_score = (tech_score * 0.3) + (mom_score * 0.3) + (liq_factor * 0.2) + ((100 - risk_score) * 0.2)
        profit_score = min(max(profit_score, 0.0), 100.0)

        # 7. Overall Opportunity Score (0-100)
        # Dynamically aggregate all scores using self-optimizing learning weights
        # Also, if Risk Score is extremely high, we penalize the overall opportunity score significantly
        weighted_upside = (
            tech_score * self.weights.get("technical", 0.25) +
            social_score * self.weights.get("social", 0.20) +
            whale_score * self.weights.get("whale", 0.20) +
            mom_score * self.weights.get("momentum", 0.15) +
            profit_score * self.weights.get("profit", 0.20)
        )

        # Penalize overall opportunity score for security risk
        risk_penalty = 0.0
        if risk_score > 80.0:
            risk_penalty = (risk_score - 80.0) * 2.5 # heavy penalty for scams/rugs
        elif risk_score > 50.0:
            risk_penalty = (risk_score - 50.0) * 0.8

        overall_score = max(weighted_upside - risk_penalty, 0.0)
        overall_score = min(overall_score, 100.0)

        return {
            "technical_score": float(tech_score),
            "social_score": float(social_score),
            "whale_score": float(whale_score),
            "momentum_score": float(mom_score),
            "risk_score": float(risk_score),
            "profit_score": float(profit_score),
            "overall_opportunity_score": float(overall_score)
        }

    def generate_trading_plan(self, current_price: float, ta_results: Dict[str, Any], risk_results: Dict[str, Any], scores: Dict[str, Any], token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a tactical trading entry & exit strategy based on ATR, Support, Resistance, and Risk Levels.
        """
        atr = ta_results.get("atr", current_price * 0.05)
        if atr <= 0:
            atr = current_price * 0.05

        # Suggested entry is around current price or slightly lower if pulling back
        suggested_entry = current_price

        # Stop loss based on average true range (ATR) or support levels
        supports = ta_results.get("support_levels", [])
        if len(supports) > 0 and supports[0] < current_price:
            stop_loss = max(supports[0], current_price - 1.5 * atr)
        else:
            stop_loss = current_price - 1.5 * atr

        # If stop loss is <= 0, set to 50% of entry price
        if stop_loss <= 0:
            stop_loss = current_price * 0.8

        # Take profits: TP1 (conservative), TP2 (moderate), TP3 (ambitious)
        tp_mults = [1.5, 3.0, 5.0]
        # Adjust multiples if it's a high risk / high volatility meme coin vs low volatility layer-2
        narrative = token_data.get("narrative", "")
        if "Meme" in narrative:
            tp_mults = [3.0, 6.0, 10.0] # Higher targets
        elif "Layer-2" in narrative or "RWA" in narrative:
            tp_mults = [1.2, 2.5, 4.0] # Conservatively smaller targets

        tp1 = current_price + tp_mults[0] * atr
        tp2 = current_price + tp_mults[1] * atr
        tp3 = current_price + tp_mults[2] * atr

        # Fibonacci level adjustments if they are close
        fibs = ta_results.get("fibonacci_levels", {})
        fib_0618 = fibs.get("0.618", current_price)
        if fib_0618 > current_price:
            # Anchor one TP near golden pocket ratio
            tp2 = fib_0618

        # Risk / Reward ratio (using TP2 relative to SL)
        potential_risk = suggested_entry - stop_loss
        potential_reward = tp2 - suggested_entry
        risk_reward_ratio = float(potential_reward / (potential_risk if potential_risk > 0 else 0.00001))

        # Expected Holding Time based on technical indicators and volume
        rel_vol = ta_results.get("relative_volume", 1.0)
        if rel_vol > 2.0:
            expected_holding_time = "4 to 24 Hours"
        elif scores.get("momentum_score", 50.0) > 75:
            expected_holding_time = "12 Hours to 2 Days"
        else:
            expected_holding_time = "3 to 7 Days"

        # Confidence percentage (derived from overall score and risk levels)
        confidence = float(scores.get("overall_opportunity_score", 50.0))

        # Reasons for selection text builder
        reasons = []
        if rel_vol > 1.5:
            reasons.append("unusual trading volume expansion")
        if ta_results.get("breakout_probability", 50.0) > 70:
            reasons.append("imminent bullish breakout setup")
        if scores.get("whale_score", 50.0) > 75:
            reasons.append("aggressive smart money/whale buying on-chain")
        if scores.get("social_score", 50.0) > 75:
            reasons.append("explosive surge in social engagement across Twitter & Reddit")
        if "AI" in narrative:
            reasons.append("powerful AI thematic market tailwinds")
        elif "Meme" in narrative:
            reasons.append("high-momentum retail meme speculation")
        elif "DePIN" in narrative:
            reasons.append("strong utility-driven DePIN narrative growth")

        if not reasons:
            reasons.append("solid risk-reward configuration and positive consolidation structure")

        reason_string = f"Selected due to {', '.join(reasons[:-1]) + ' and ' + reasons[-1] if len(reasons) > 1 else reasons[0]}."

        return {
            "suggested_entry": float(suggested_entry),
            "stop_loss": float(stop_loss),
            "take_profit_1": float(tp1),
            "take_profit_2": float(tp2),
            "take_profit_3": float(tp3),
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "expected_holding_time": expected_holding_time,
            "confidence_pct": round(confidence, 1),
            "reason_for_selection": reason_string
        }
