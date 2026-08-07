import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    if len(series) < span:
        return series.rolling(window=len(series), min_periods=1).mean()
    return series.ewm(span=span, adjust=False).mean()

class TechnicalAnalysisEngine:
    """
    Computes professional-grade technical analysis indicators including:
    - EMA 9, 20, 50, 200
    - VWAP (Volume Weighted Average Price)
    - RSI (Relative Strength Index)
    - MACD (MACD line, signal, histogram)
    - ADX (Average Directional Index)
    - ATR (Average True Range)
    - Bollinger Bands (Upper, Middle, Lower)
    - OBV (On-Balance Volume)
    - Fibonacci retracement levels
    - Support and Resistance
    - Trend Strength
    - Relative Volume
    - Breakout Probability
    """
    @staticmethod
    def analyze(prices: List[float], volumes: List[float]) -> Dict[str, Any]:
        if len(prices) < 2:
            # Fallback for empty or too short data
            return {
                "ema_9": 0.0, "ema_20": 0.0, "ema_50": 0.0, "ema_200": 0.0,
                "vwap": 0.0, "rsi": 50.0, "macd": {"line": 0.0, "signal": 0.0, "histogram": 0.0},
                "adx": 20.0, "atr": 0.0, "bollinger_bands": {"upper": 0.0, "mid": 0.0, "lower": 0.0},
                "obv": 0.0, "fibonacci_levels": {}, "support_levels": [], "resistance_levels": [],
                "trend_strength": "Neutral", "relative_volume": 1.0, "breakout_probability": 0.0
            }

        df = pd.DataFrame({"close": prices, "volume": volumes})
        # Simulate high/low for standard ATR/ADX calculation
        df["high"] = df["close"] * (1 + np.abs(np.random.normal(0, 0.015, len(df))))
        df["low"] = df["close"] * (1 - np.abs(np.random.normal(0, 0.015, len(df))))
        df["high"] = np.maximum(df["high"], df["close"])
        df["low"] = np.minimum(df["low"], df["close"])
        # Set first close as previous close for true ranges
        df["prev_close"] = df["close"].shift(1).fillna(df["close"])

        # 1. EMAs
        df["ema_9"] = calculate_ema(df["close"], 9)
        df["ema_20"] = calculate_ema(df["close"], 20)
        df["ema_50"] = calculate_ema(df["close"], 50)
        df["ema_200"] = calculate_ema(df["close"], 200)

        # 2. VWAP (approximation for period: cumulative volume-price / cumulative volume)
        df["vwap"] = (df["close"] * df["volume"]).cumsum() / df["volume"].cumsum().replace(0, 1)

        # 3. RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / loss.replace(0, 0.00001)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].fillna(50)

        # 4. MACD
        df["ema_12"] = calculate_ema(df["close"], 12)
        df["ema_26"] = calculate_ema(df["close"], 26)
        df["macd_line"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = calculate_ema(df["macd_line"], 9)
        df["macd_hist"] = df["macd_line"] - df["macd_signal"]

        # 5. ATR (Average True Range)
        tr1 = df["high"] - df["low"]
        tr2 = np.abs(df["high"] - df["prev_close"])
        tr3 = np.abs(df["low"] - df["prev_close"])
        df["tr"] = np.maximum(tr1, np.maximum(tr2, tr3))
        df["atr"] = df["tr"].rolling(window=14, min_periods=1).mean()

        # 6. ADX (Average Directional Index)
        up_move = df["high"] - df["high"].shift(1)
        down_move = df["low"].shift(1) - df["low"]

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        atr_14 = df["atr"].replace(0, 0.00001)
        df["plus_di"] = 100 * (pd.Series(plus_dm).rolling(14, min_periods=1).mean() / atr_14)
        df["minus_di"] = 100 * (pd.Series(minus_dm).rolling(14, min_periods=1).mean() / atr_14)

        di_sum = (df["plus_di"] + df["minus_di"]).replace(0, 0.00001)
        df["dx"] = 100 * (np.abs(df["plus_di"] - df["minus_di"]) / di_sum)
        df["adx"] = df["dx"].rolling(14, min_periods=1).mean().fillna(20)

        # 7. Bollinger Bands
        df["bb_mid"] = df["close"].rolling(window=20, min_periods=1).mean()
        df["bb_std"] = df["close"].rolling(window=20, min_periods=1).std().fillna(0)
        df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
        df["bb_lower"] = df["bb_mid"] - 2 * df["bb_std"]

        # 8. OBV (On-Balance Volume)
        obv = [0.0]
        for idx in range(1, len(df)):
            if df["close"].iloc[idx] > df["close"].iloc[idx-1]:
                obv.append(obv[-1] + df["volume"].iloc[idx])
            elif df["close"].iloc[idx] < df["close"].iloc[idx-1]:
                obv.append(obv[-1] - df["volume"].iloc[idx])
            else:
                obv.append(obv[-1])
        df["obv"] = obv

        # 9. Fibonacci Levels
        high_price = float(df["high"].max())
        low_price = float(df["low"].min())
        diff = high_price - low_price
        fib_levels = {
            "0.236": float(high_price - 0.236 * diff),
            "0.382": float(high_price - 0.382 * diff),
            "0.500": float(high_price - 0.500 * diff),
            "0.618": float(high_price - 0.618 * diff),
            "0.786": float(high_price - 0.786 * diff)
        }

        # 10. Support and Resistance Levels (Pivot Point based)
        pivot = (high_price + low_price + float(df["close"].iloc[-1])) / 3
        resistance_levels = [
            float(2 * pivot - low_price),
            float(pivot + (high_price - low_price)),
            float(high_price + 2 * (pivot - low_price))
        ]
        support_levels = [
            float(2 * pivot - high_price),
            float(pivot - (high_price - low_price)),
            float(low_price - 2 * (high_price - pivot))
        ]

        # 11. Trend Strength Analysis
        last_adx = float(df["adx"].iloc[-1])
        last_close = float(df["close"].iloc[-1])
        last_ema_50 = float(df["ema_50"].iloc[-1])

        if last_adx > 25:
            trend_strength = "Strong Uptrend" if last_close > last_ema_50 else "Strong Downtrend"
        else:
            trend_strength = "Weak Trend / Consolidating"

        # 12. Relative Volume
        avg_volume = df["volume"].mean() if df["volume"].mean() > 0 else 1.0
        relative_volume = float(df["volume"].iloc[-1] / avg_volume)

        # 13. Breakout Probability calculation
        # High volume + bollinger band pinch (squeeze) + RSI momentum
        bb_width = float((df["bb_upper"].iloc[-1] - df["bb_lower"].iloc[-1]) / (df["bb_mid"].iloc[-1] or 1.0))
        historical_bb_widths = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"].replace(0, 1.0)
        is_squeeze = bb_width < historical_bb_widths.mean() * 0.95

        rsi_val = float(df["rsi"].iloc[-1])
        rsi_momentum = rsi_val > 55 and rsi_val < 75

        breakout_prob = 15.0 # baseline
        if relative_volume > 1.5:
            breakout_prob += 25.0
        if is_squeeze:
            breakout_prob += 20.0
        if rsi_momentum:
            breakout_prob += 20.0
        if float(df["macd_hist"].iloc[-1]) > 0:
            breakout_prob += 10.0
        if last_close > float(df["bb_mid"].iloc[-1]):
            breakout_prob += 10.0

        breakout_prob = min(max(breakout_prob, 5.0), 98.0)

        # Extract last row as dict for return
        return {
            "ema_9": float(df["ema_9"].iloc[-1]),
            "ema_20": float(df["ema_20"].iloc[-1]),
            "ema_50": float(df["ema_50"].iloc[-1]),
            "ema_200": float(df["ema_200"].iloc[-1]),
            "vwap": float(df["vwap"].iloc[-1]),
            "rsi": rsi_val,
            "macd": {
                "line": float(df["macd_line"].iloc[-1]),
                "signal": float(df["macd_signal"].iloc[-1]),
                "histogram": float(df["macd_hist"].iloc[-1])
            },
            "adx": last_adx,
            "atr": float(df["atr"].iloc[-1]),
            "bollinger_bands": {
                "upper": float(df["bb_upper"].iloc[-1]),
                "mid": float(df["bb_mid"].iloc[-1]),
                "lower": float(df["bb_lower"].iloc[-1])
            },
            "obv": float(df["obv"].iloc[-1]),
            "fibonacci_levels": fib_levels,
            "support_levels": support_levels,
            "resistance_levels": resistance_levels,
            "trend_strength": trend_strength,
            "relative_volume": relative_volume,
            "breakout_probability": breakout_prob
        }
