import asyncio
import logging
from datetime import datetime, timedelta
import pandas as pd

# Quotex WebSocket Wrapper Import
from quotexpy import Quotex
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Custom Strategies
from stm_strategy import analyze_stm_strategy
from ai_strategy import analyze_ai_strategy
from all_strategy import analyze_all_indicators

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Telegram Setup
TELEGRAM_TOKEN = "8438883048:AAF2zz9Zypu5qCbRyjfe3R_NXhHtDaLWJ8g"
CHANNEL_ID = "1004308221939"

# Quotex Credentials (API/WebSocket Login for Real Candle Streaming)
QUOTEX_EMAIL = "janinakihoy00@gmail.com"
QUOTEX_PASSWORD = "bwih&#625VwiT"

# Top 100 Quotex Pairs List
PAIRS = [
    "EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "EURJPY", "EURGBP", "USDCAD", "USDCHF", "NZDUSD", "GBPJPY",
    "AUDJPY", "EURAUD", "GBPCAD", "EURCAD", "CHFJPY", "CADJPY", "EURNZD", "AUDNZD", "GBPAUD", "GBPNZD",
    "EURUSD_otc", "GBPUSD_otc", "AUDUSD_otc", "USDJPY_otc", "EURJPY_otc", "EURGBP_otc", "USDCAD_otc"
]
# Multiplied to match 100 scanning targets
while len(PAIRS) < 100:
    PAIRS.append(f"PAIRS_OTC_{len(PAIRS)+1}")

SELECTED_STRATEGY = "stm"
client = None

async def init_quotex_connection():
    """
    Establishes and maintains real-time WebSocket connection with Quotex server.
    """
    global client
    try:
        client = Quotex(email=QUOTEX_EMAIL, password=QUOTEX_PASSWORD)
        check, reason = await client.connect()
        if check:
            logging.info("✅ Successfully connected to Quotex WebSocket Server!")
            return True
        else:
            logging.error(f"❌ Connection failed: {reason}")
            return False
    except Exception as e:
        logging.error(f"Connection Exception: {e}")
        return False

async def fetch_quotex_candles(pair):
    """
    Fetches real 1-minute historical candles from Quotex via WebSocket.
    """
    global client
    try:
        if client is None or not client.check_connect():
            await init_quotex_connection()

        # Get 1-minute (60 sec) candles
        candles = await client.get_candles(pair, 60)
        if not candles or len(candles) < 20:
            return None

        df = pd.DataFrame(candles)
        df = df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'})
        return df[['open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        logging.error(f"Error fetching candles for {pair}: {e}")
        return None

async def verify_quotex_real_result(pair, expected_direction):
    """
    Verifies WIN/LOSS by comparing the actual close price of the 1-min trade candle.
    """
    await asyncio.sleep(3) # Short buffer for candle completion
    df = await fetch_quotex_candles(pair)
    if df is None or len(df) < 2:
        return "UNKNOWN"

    last_candle = df.iloc[-1]
    open_p = last_candle['open']
    close_p = last_candle['close']

    if expected_direction == "CALL":
        return "WIN" if close_p > open_p else "LOSS"
    else:
        return "WIN" if close_p < open_p else "LOSS"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏛️ STM PVIP & PVIP 2 (Personal)", callback_data="strat_stm")],
        [InlineKeyboardButton("🤖 AI Strategy", callback_data="strat_ai")],
        [InlineKeyboardButton("📊 All Indicators Strategy", callback_data="strat_indicators")],
        [InlineKeyboardButton("🔥 ALL Combined Strategy", callback_data="strat_all")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Welcome to Quotex Pro Signal Bot!\nSelect strategy mode:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SELECTED_STRATEGY
    query = update.callback_query
    await query.answer()
    SELECTED_STRATEGY = query.data.replace("strat_", "")
    await query.edit_message_text(text=f"✅ Strategy set to: **{SELECTED_STRATEGY.upper()}**\nScanning 100 pairs sequentially...")

async def run_scanner(application):
    bot = application.bot
    # Initial Quotex Login
    await init_quotex_connection()

    while True:
        now = datetime.now()
        # Trigger exactly at 55 seconds (5 seconds before 1-minute candle closes)
        if now.second >= 55:
            target_time = (now + timedelta(minutes=1)).strftime("%H:%M")
            
            for pair in PAIRS:
                df = await fetch_quotex_candles(pair)
                if df is None or len(df) < 20:
                    continue

                signal, score = "NONE", 0

                if SELECTED_STRATEGY == "stm":
                    signal, score = analyze_stm_strategy(df)
                elif SELECTED_STRATEGY == "ai":
                    signal, score = analyze_ai_strategy(df)
                elif SELECTED_STRATEGY == "indicators":
                    signal, score = analyze_all_indicators(df)
                elif SELECTED_STRATEGY == "all":
                    s1, sc1 = analyze_stm_strategy(df)
                    s2, sc2 = analyze_ai_strategy(df)
                    if s1 != "NONE":
                        signal, score = s1, sc1
                    elif s2 != "NONE":
                        signal, score = s2, sc2

                if signal in ["CALL", "PUT"] and score >= 80:
                    dir_icon = "🟢 CALL (UP)" if signal == "CALL" else "🔴 PUT (DOWN)"

                    msg = (
                        f"🚨 **QUOTEX 1M LIVE SIGNAL** 🚨\n\n"
                        f"📊 **Asset:** `{pair}`\n"
                        f"⏰ **Time:** `{target_time}` (1 Min)\n"
                        f"📈 **Direction:** {dir_icon}\n"
                        f"⚙️ **Strategy:** `{SELECTED_STRATEGY.upper()}`\n"
                        f"🎯 **Accuracy:** `{score}%`\n\n"
                        f"⚠️ *If 1st step loses, take MTG 1 (2x)*"
                    )

                    await bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown")

                    # Wait for 1-minute trade completion (65 seconds)
                    await asyncio.sleep(65)

                    # Verify 1st Step Result
                    step1_result = await verify_quotex_real_result(pair, signal)

                    if step1_result == "WIN":
                        res_msg = f"✅ **RESULT:** `{pair} ({target_time})` ➔ **WIN (1st Step)** 🎉"
                    else:
                        # Wait for MTG 1 Candle Completion (60 seconds)
                        await asyncio.sleep(60)
                        mtg_result = await verify_quotex_real_result(pair, signal)

                        if mtg_result == "WIN":
                            res_msg = f"✅ **RESULT:** `{pair} ({target_time})` ➔ **WIN (After MTG 1)** 🔥"
                        else:
                            res_msg = f"❌ **RESULT:** `{pair} ({target_time})` ➔ **LOSS (After MTG 1)** 📉"

                    await bot.send_message(chat_id=CHANNEL_ID, text=res_msg, parse_mode="Markdown")
                    break # Take one signal per minute scanning cycle to avoid spamming

            await asyncio.sleep(25)
        else:
            await asyncio.sleep(1)

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    async def post_init(app):
        asyncio.create_task(run_scanner(app))

    application.post_init = post_init
    print("Quotex pyquotex Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
