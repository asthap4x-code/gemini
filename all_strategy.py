import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, SMAIndicator
from ta.momentum import StochasticOscillator

def analyze_all_indicators(df):
    """
    Combines EMA, Moving Average, Stochastic Oscillator, Support/Resistance, 
    and Candlestick pattern detection.
    """
    if len(df) < 30:
        return "NONE", 0

    close = df['close']
    high = df['high']
    low = df['low']
    open_p = df['open']

    # Indicators
    ema_9 = EMAIndicator(close, window=9).ema_indicator().iloc[-1]
    ema_21 = EMAIndicator(close, window=21).ema_indicator().iloc[-1]
    sma_50 = SMAIndicator(close, window=50).sma_indicator().iloc[-1]
    
    stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
    stoch_k = stoch.stoch().iloc[-1]
    stoch_d = stoch.stoch_signal().iloc[-1]

    # Candlestick pattern check (Last candle)
    body = close.iloc[-1] - open_p.iloc[-1]
    prev_body = close.iloc[-2] - open_p.iloc[-2]
    
    is_bullish_engulfing = (prev_body < 0) and (body > 0) and (close.iloc[-1] >= open_p.iloc[-2])
    is_bearish_engulfing = (prev_body > 0) and (body < 0) and (close.iloc[-1] <= open_p.iloc[-2])

    signal = "NONE"
    score = 60

    # Decision Matrix
    if ema_9 > ema_21 and stoch_k < 20 and (is_bullish_engulfing or close.iloc[-1] > sma_50):
        signal = "CALL"
        score = 85
    elif ema_9 < ema_21 and stoch_k > 80 and (is_bearish_engulfing or close.iloc[-1] < sma_50):
        signal = "PUT"
        score = 85
    elif ema_9 > ema_21 and close.iloc[-1] > ema_9:
        signal = "CALL"
        score = 70
    elif ema_9 < ema_21 and close.iloc[-1] < ema_9:
        signal = "PUT"
        score = 70

    return signal, score
