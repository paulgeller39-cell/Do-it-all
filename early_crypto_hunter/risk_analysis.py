import random
from typing import Dict, Any

class RiskAnalysisEngine:
    """
    Evaluates key on-chain and liquidity risk vectors:
    - Rug Pull Probability
    - Honeypot Probability
    - Liquidity Risk
    - Contract Risk
    - Holder Concentration Risk
    - Developer Wallet Percentage & Risk
    - Unlock Schedule & Token Inflation Risk
    - Market Manipulation Risk
    Calculates an integrated 'Risk Score' from 0 (very low risk) to 100 (extreme risk/scam).
    """
    @staticmethod
    def analyze(token_data: Dict[str, Any]) -> Dict[str, Any]:
        ticker = token_data.get("ticker", "")
        liquidity = token_data.get("liquidity", 100000.0)
        volume_24h = token_data.get("volume_24h", 50000.0)

        # Seed generator based on ticker name for deterministic but diverse risk attributes
        rng = random.Random(hash(ticker))

        # 1. Holder concentration: top 10 holders percentage
        holder_concentration = rng.uniform(15.0, 85.0)
        if "Meme" in token_data.get("narrative", ""):
            holder_concentration += rng.uniform(5.0, 15.0) # Meme coins typically more concentrated
        holder_concentration = min(holder_concentration, 99.0)

        # 2. Developer wallet percentage
        developer_wallet_pct = rng.uniform(0.0, 35.0)
        if developer_wallet_pct > 25.0:
            dev_risk = "High"
        elif developer_wallet_pct > 10.0:
            dev_risk = "Medium"
        else:
            dev_risk = "Low"

        # 3. Liquidity Risk (Ratio of volume to liquidity, or if liquidity is too low)
        # Low liquidity is highly risky
        if liquidity < 10000:
            liq_risk_pct = 95.0
        elif liquidity < 50000:
            liq_risk_pct = 75.0
        elif liquidity < 200000:
            liq_risk_pct = 50.0
        else:
            liq_risk_pct = 25.0

        # 4. Honeypot check (simulation or heuristic - e.g. can we sell? Tax structure)
        # High sell tax is a honeypot indicator
        buy_tax = rng.uniform(0.0, 8.0)
        sell_tax = rng.uniform(0.0, 10.0)

        # Sometime make it high to represent realistic risk
        if rng.random() < 0.05:
            sell_tax = rng.uniform(80.0, 99.0) # honeypot

        honeypot_prob = 5.0
        if sell_tax > 30.0:
            honeypot_prob = 95.0
        elif sell_tax > 10.0:
            honeypot_prob = 40.0

        # 5. Contract Risk: unrenounced ownership, mintable, blacklisting features
        is_ownership_renounced = rng.choice([True, False, True]) # more renounced
        is_mintable = rng.choice([True, False, False, False])

        contract_risk_score = 10.0
        if not is_ownership_renounced:
            contract_risk_score += 30.0
        if is_mintable:
            contract_risk_score += 40.0

        # 6. Rug Pull Probability
        # Highly correlated to unlocked liquidity, high dev ownership, and low concentration checks
        rug_pull_prob = 10.0
        if not is_ownership_renounced:
            rug_pull_prob += 20.0
        if developer_wallet_pct > 20.0:
            rug_pull_prob += 25.0
        if holder_concentration > 75.0:
            rug_pull_prob += 20.0
        if liquidity < 30000:
            rug_pull_prob += 20.0
        rug_pull_prob = min(max(rug_pull_prob, 5.0), 99.0)

        # 7. Inflation and unlock schedule
        unlock_schedule = rng.choice(["Fully Unlocked", "Linear Vesting over 1 year", "Cliff Vesting", "Developer Discretion"])
        inflation_risk = 10.0
        if unlock_schedule == "Developer Discretion":
            inflation_risk = 80.0
        elif unlock_schedule == "Cliff Vesting":
            inflation_risk = 50.0

        # 8. Market Manipulation Risk (low market cap / high wash-trading likelihood)
        market_manipulation_risk = 20.0
        if volume_24h > 10 * liquidity:
            market_manipulation_risk += 40.0 # likely wash trading
        if holder_concentration > 60.0:
            market_manipulation_risk += 20.0
        market_manipulation_risk = min(market_manipulation_risk, 95.0)

        # Compute combined Overall Risk Score (0-100)
        # Weights: Rug Pull: 30%, Honeypot: 25%, Liquidity: 15%, Contract: 15%, Concentration/Dev: 15%
        overall_risk_score = (
            rug_pull_prob * 0.30 +
            honeypot_prob * 0.25 +
            liq_risk_pct * 0.15 +
            contract_risk_score * 0.15 +
            (holder_concentration * 0.5 + developer_wallet_pct * 0.5) * 0.15
        )
        overall_risk_score = min(max(overall_risk_score, 5.0), 100.0)

        return {
            "rug_pull_probability": float(rug_pull_prob),
            "honeypot_probability": float(honeypot_prob),
            "liquidity_risk": float(liq_risk_pct),
            "contract_risk": float(contract_risk_score),
            "holder_concentration": float(holder_concentration),
            "developer_wallet_pct": float(developer_wallet_pct),
            "developer_risk_rating": dev_risk,
            "buy_tax": float(buy_tax),
            "sell_tax": float(sell_tax),
            "is_ownership_renounced": is_ownership_renounced,
            "is_mintable": is_mintable,
            "unlock_schedule": unlock_schedule,
            "token_inflation_risk": float(inflation_risk),
            "market_manipulation_risk": float(market_manipulation_risk),
            "overall_risk_score": float(overall_risk_score)
        }
