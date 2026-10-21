import numpy as np
import pandas as pd
from ta.trend import EMAIndicator

def analyze_stm_pvip(df):
    """
    STM PVIP Strategy:
    - Uptrend: 3 to 10 consecutive green candles followed by 1 red candle -> Next candle UP.
    - Downtrend: 3 to 10 consecutive red candles followed by 1 green candle -> Next candle DOWN.
    """
    if len(df) < 15:
        return "NONE", 0

    closes = df['close'].values
    opens = df['open'].values
    
    # Check candle colors (Green = 1, Red = -1)
    colors = [1 if closes[i] > opens[i] else -1 for i in range(len(df))]
    
    # Look at recent candles (excluding the very last forming candle if needed, or using completed ones)
    recent_colors = colors[-12:-1]  # Last 11 completed candles
    
    # Check for Uptrend pattern: [Green, Green, ..., Red]
    # Count consecutive greens at the end of the sequence before the last red
    if recent_colors[-1] == -1:  # Last completed is red
        green_count = 0
        for c in reversed(recent_colors[:-1]):
            if c == 1:
                green_count += 1
            else:
                break
        if 3 <= green_count <= 10:
            return "CALL", 85

    # Check for Downtrend pattern: [Red, Red, ..., Green]
    if recent_colors[-1] == 1:  # Last completed is green
        red_count = 0
        for c in reversed(recent_colors[:-1]):
            if c == -1:
                red_count += 1
            else:
                break
        if 3 <= red_count <= 10:
            return "PUT", 85

    return "NONE", 0

def analyze_stm_pvip2(df):
    """
    STM PVIP 2 Strategy:
    - EMA 10 filter + Horizontal Line / Price touch with 55-85% body rule.
    """
    if len(df) < 25:
        return "NONE", 0

    close = df['close']
    open_p = df['open']
    high = df['high']
    low = df['low']

    # Calculate EMA 10
    ema_10 = EMAIndicator(close, window=10).ema_indicator()
    current_ema = ema_10.iloc[-1]
    
    curr_close = close.iloc[-1]
    curr_open = open_p.iloc[-1]
    curr_high = high.iloc[-1]
    curr_low = low.iloc[-1]
    
    body_size = abs(curr_close - curr_open)
    if body_size == 0:
        return "NONE", 0

    # Check if candles are above EMA 10 (Uptrend) or below EMA 10 (Downtrend)
    is_above_ema = curr_close > current_ema and close.iloc[-2] > ema_10.iloc[-2]
    is_below_ema = curr_close < current_ema and close.iloc[-2] < ema_10.iloc[-2]

    # Find a recent horizontal level (where close of one candle equals open of next)
    level_found = False
    target_level = 0
    for i in range(len(df) - 5, len(df) - 1):
        if abs(close.iloc[i-1] - open_p.iloc[i]) < 0.00005:
            target_level = close.iloc[i-1]
            level_found = True
            break

    if not level_found:
        # Fallback to recent swing high/low as horizontal line
        target_level = high.iloc[-5:-1].mean() if is_above_ema else low.iloc[-5:-1].mean()

    # Check price return / touch to the line
    if is_above_ema and curr_low <= target_level <= curr_high:
        # Calculate percentage of green body above the horizontal line
        if curr_close > curr_open:  # Green candle
            above_line_portion = curr_close - target_level
            percentage = (above_line_portion / body_size) * 100
            if 55 <= percentage <= 85:
                return "CALL", 90

    elif is_below_ema and curr_low <= target_level <= curr_high:
        # Calculate percentage of red body below the horizontal line
        if curr_close < curr_open:  # Red candle
            below_line_portion = target_level - curr_close
            percentage = (below_line_portion / body_size) * 100
            if 55 <= percentage <= 85:
                return "PUT", 90

    return "NONE", 0

def analyze_stm_strategy(df):
    """
    Master STM wrapper combining PVIP and PVIP 2
    """
    signal, conf = analyze_stm_pvip(df)
    if signal != "NONE":
        return signal, conf
        
    signal, conf = analyze_stm_pvip2(df)
    return signal, conf
