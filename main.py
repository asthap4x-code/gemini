import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Quotex API package (Install via: pip install quotexapi)
from quotexapi.stable_api import Quotex

from stm_strategy import analyze_stm_strategy
from ai_strategy import analyze_ai_strategy
from all_strategy import analyze_all_indicators
import pandas as pd

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = "8438883048:AAF2zz9Zypu5qCbRyjfe3R_NXhHtDaLWJ8g"
CHANNEL_ID = "1004308221939"

# Quotex Login credentials (Needed only if using API wrapper for real market data streaming)
QUOTEX_EMAIL = "janinakihoy00@gmail.com"
QUOTEX_PASSWORD = "bwih&#625VwiT"

# Initialize Quotex client
client = Quotex(email=QUOTEX_EMAIL, password=QUOTEX_PASSWORD, lang="en")

PAIRS = ["EUR/USD", "GBP/USD", "AUD/USD", "USD/JPY", "EUR/JPY"] # Add more as needed
SELECTED_STRATEGY = "stm"

async def fetch_real_quotex_candles(asset, period=60):
    """
    Fetches real historical/live candles from Quotex server using API wrapper.
    """
    try:
        # Get candles data (1 minute = 60 seconds)
        end_time = client.get_server_time()
        candles = await client.get_candles(asset, end_time, 60, period)
        
        if not candles:
            return None
            
        df = pd.DataFrame(candles)
        # Rename/format columns based on API response structure
        df = df[['open', 'high', 'low', 'close', 'volume']]
        return df
    except Exception as e:
        logging.error(f"Error fetching real data for {asset}: {e}")
        return None

async def verify_real_trade_result(pair, expected_direction):
    """
    Verifies actual win/loss from real market candle after trade completion.
    """
    await asyncio.sleep(5) # Wait for candle to fully settle
    df = await fetch_real_quotex_candles(pair)
    if df is None or len(df) < 2:
        return "UNKNOWN"
        
    last_candle = df.iloc[-1]
    open_p = last_candle['open']
    close_p = last_candle['close']
    
    if expected_direction == "CALL":
        return "WIN" if close_p > open_p else "LOSS"
    else:
        return "WIN" if close_p < open_p else "LOSS"

async def run_scanner(application):
    # Connect to Quotex
    check, reason = await client.connect()
    if not check:
        logging.error(f"Failed to connect to Quotex API: {reason}")
        return
    
    logging.info("Successfully connected to Quotex Live API!")
    bot = application.bot

    while True:
        now = datetime.now()
        if now.second >= 55:
            target_time = (now + timedelta(minutes=1)).strftime("%H:%M")
            
            for pair in PAIRS:
                df = await fetch_real_quotex_candles(pair)
                if df is None or len(df) < 30:
                    continue
                    
                signal, score = "NONE", 0
                if SELECTED_STRATEGY == "stm":
                    signal, score = analyze_stm_strategy(df)
                elif SELECTED_STRATEGY == "ai":
                    signal, score = analyze_ai_strategy(df)
                
                if signal in ["CALL", "PUT"] and score >= 80:
                    dir_icon = "🟢 CALL (UP)" if signal == "CALL" else "🔴 PUT (DOWN)"
                    
                    msg = (
                        f"🚨 **QUOTEX LIVE SIGNAL** 🚨\n\n"
                        f"📊 **Asset:** `{pair}`\n"
                        f"⏰ **Time:** `{target_time}` (1 Min)\n"
                        f"📈 **Direction:** {dir_icon}\n"
                        f"🎯 **Confidence:** `{score}%`\n\n"
                        f"⚠️ *If 1st step loses, take MTG 1 (2x)*"
                    )
                    
                    await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown")
                    
                    # Wait for 1 minute trade duration + buffer
                    await asyncio.sleep(65)
                    
                    # Verify 1st step
                    result = await verify_real_trade_result(pair, signal)
                    if result == "WIN":
                        res_msg = f"✅ **RESULT:** `{pair} ({target_time})` ➔ **WIN (1st Step)** 🎉"
                    else:
                        # MTG 1 verification check
                        await asyncio.sleep(60)
                        mtg_result = await verify_real_trade_result(pair, signal)
                        if mtg_result == "WIN":
                            res_msg = f"✅ **RESULT:** `{pair} ({target_time})` ➔ **WIN (After MTG 1)** 🔥"
                        else:
                            res_msg = f"❌ **RESULT:** `{pair} ({target_time})` ➔ **LOSS (After MTG 1)** 📉"
                    
                    await bot.send_message(chat_id=CHANNEL_ID, text=res_msg, parse_mode="Markdown")
                    break
                    
            await asyncio.sleep(30)
        else:
            await asyncio.sleep(1)

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    async def post_init(app):
        asyncio.create_task(run_scanner(app))
        
    application.post_init = post_init
    application.run_polling()

if __name__ == '__main__':
    main()
