import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import random
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from telegram import Bot
import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '7751724771'))
HOUSE_EDGE = float(os.getenv('HOUSE_EDGE', '0.1'))
CRASH_WIN_RATE = float(os.getenv('CRASH_WIN_RATE', '0.8'))
DICE_WIN_RATE = float(os.getenv('DICE_WIN_RATE', '0.66'))
SPIN_WIN_RATE = float(os.getenv('SPIN_WIN_RATE', '0.5'))
TAP_PAYOUT_RATE = float(os.getenv('TAP_PAYOUT_RATE', '0.9'))

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Initialize SQLite database
conn = sqlite3.connect('/mnt/data/solo_cashmachine.db', check_same_thread=False)
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS player (
    user_id INTEGER PRIMARY KEY,
    balance REAL,
    mode TEXT,
    autoplay BOOLEAN,
    created_at TEXT)''')
cur.execute('''
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    bet_amount REAL,
    multiplier REAL,
    outcome TEXT,
    profit REAL,
    mode TEXT,
    created_at TEXT)''')
cur.execute('''
CREATE TABLE IF NOT EXISTS profits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profit REAL,
    mode TEXT,
    created_at TEXT)''')
conn.commit()

class BetRequest(BaseModel):
    user_id: int
    bet_amount: float
    multiplier: float
    mode: str

async def send_telegram_notification(message):
    for attempt in range(3):
        try:
            await telegram_bot.send_message(chat_id=ADMIN_USER_ID, text=message)
            logger.info(f"Telegram notification sent: {message}")
            return
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(2)
    logger.error("Failed to send Telegram notification after 3 attempts")

def update_balance(user_id, amount, mode='crash'):
    cur.execute("SELECT balance FROM player WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    new_balance = (result[0] if result else 0) + amount
    cur.execute("INSERT OR REPLACE INTO player (user_id, balance, mode, autoplay, created_at) VALUES (?,?,?,0,?)",
                (user_id, new_balance, mode, datetime.now().isoformat()))
    conn.commit()
    return new_balance

def update_profit(profit, mode):
    cur.execute("INSERT INTO profits (profit, mode, created_at) VALUES (?,?,?)",
                (profit, mode, datetime.now().isoformat()))
    conn.commit()
    cur.execute("SELECT SUM(profit) FROM profits")
    total_profit = cur.fetchone()[0] or 0
    return total_profit

async def autoplay_loop():
    while True:
        try:
            cur.execute("SELECT user_id, balance, mode FROM player WHERE autoplay = 1")
            for user_id, balance, mode in cur.fetchall():
                if balance < 1:
                    continue
                bet_amount = 1.0
                multiplier = 2.0 if mode in ['crash', 'dice'] else 3.0
                if mode == 'crash':
                    outcome ="win" if random.random() < CRASH_WIN_RATE else"lose"
                    crash_point = multiplier + random.uniform(0.1, 8.0) if outcome =="win" else random.uniform(1.0, multiplier - 0.1)
                    player_profit = bet_amount* (multiplier - 1) * (1 - HOUSE_EDGE) if outcome =="win" else -bet_amount
                elif mode == 'dice':
                    roll = random.randint(1, 6)
                    outcome ="win" if roll >= 4 else"lose"
                    crash_point = roll
                    player_profit = bet_amount* (multiplier - 1) * (1 - HOUSE_EDGE) if outcome =="win" else -bet_amount
                elif mode == 'spin':
                    symbols = [random.randint(1, 3) for_ in range(3)]
                    outcome ="win" if len(set(symbols)) == 1 else"lose"
                    crash_point = symbols[0]
                    player_profit = bet_amount* (multiplier - 1) * (1 - HOUSE_EDGE) if outcome =="win" else -bet_amount
                else:  # tap
                    outcome ="win"
                    crash_point = 1
                    player_profit = bet_amount* TAP_PAYOUT_RATE
                house_profit = bet_amount* HOUSE_EDGE if outcome =="lose" else -player_profit* HOUSE_EDGE
                new_balance = update_balance(user_id, player_profit + house_profit, mode)
                update_profit(house_profit, mode)
                cur.execute("INSERT INTO bets (user_id, bet_amount, multiplier, outcome, profit, mode, created_at) VALUES (?,?,?,?,?,?,?)",
                            (user_id, bet_amount, multiplier, outcome, player_profit, mode, datetime.now().isoformat()))
                conn.commit()
                await send_telegram_notification(
                    f"🤖 Auto-Play {mode.capitalize()}\nAmount:${bet_amount:.2f} @ {multiplier}x\nOutcome: {outcome}\nPlayer Profit:${player_profit:.2f}\nHouse Profit:${house_profit:.2f}\nBalance:${new_balance:.2f}"
                )
            await asyncio.sleep(60)  # Run every minute
        except Exception as e:
            logger.error(f"Auto-play error: {e}")
            await asyncio.sleep(300)

@app.post("/bet")
async def place_bet(bet: BetRequest):
    try:
        if bet.mode not in ['crash', 'dice', 'spin', 'tap']:
            raise HTTPException(status_code=400, detail="Invalid mode")
        cur.execute("SELECT balance FROM player WHERE user_id = ?", (bet.user_id,))
        result = cur.fetchone()
        balance = result[0] if result else 0
        if balance < bet.bet_amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        if bet.mode == 'crash':
            outcome ="win" if random.random() < CRASH_WIN_RATE else"lose"
            crash_point = bet.multiplier + random.uniform(0.1, 8.0) if outcome =="win" else random.uniform(1.0, bet.multiplier - 0.1)
            player_profit = bet.bet_amount* (bet.multiplier - 1) * (1 - HOUSE_EDGE) if outcome =="win" else -bet.bet_amount
        elif bet.mode == 'dice':
            roll = random.randint(1, 6)
            outcome ="win" if roll >= 4 else"lose"
            crash_point = roll
            player_profit = bet.bet_amount* (bet.multiplier - 1) * (1 - HOUSE_EDGE) if outcome =="win" else -bet.bet_amount
        elif bet.mode == 'spin':
            symbols = [random.randint(1, 3) for_ in range(3)]
            outcome ="win" if len(set(symbols)) == 1 else"lose"
            crash_point = symbols[0]
            player_profit = bet.bet_amount* (bet.multiplier - 1) * (1 - HOUSE_EDGE) if outcome =="win" else -bet.bet_amount
        else:  # tap
            outcome ="win"
            crash_point = bet.multiplier
            player_profit = bet.bet_amount* TAP_PAYOUT_RATE

        house_profit = bet.bet_amount* HOUSE_EDGE if outcome =="lose" else -player_profit* HOUSE_EDGE
        new_balance = update_balance(bet.user_id, player_profit + house_profit, bet.mode)
        total_profit = update_profit(house_profit, bet.mode)

        cur.execute("INSERT INTO bets (user_id, bet_amount, multiplier, outcome, profit, mode, created_at) VALUES (?,?,?,?,?,?,?)",
                    (bet.user_id, bet.bet_amount, bet.multiplier, outcome, player_profit, bet.mode, datetime.now().isoformat()))
        conn.commit()

        await send_telegram_notification(
            f"🎮 {bet.mode.capitalize()} Action\nAmount:${bet.bet_amount:.2f} @ {bet.multiplier}x\nOutcome: {outcome}\nPlayer Profit:${player_profit:.2f}\nHouse Profit:${house_profit:.2f}\nBalance:${new_balance:.2f}\nTotal System Profit:${total_profit:.2f}"
        )

        return {"status":"success","outcome": outcome,"balance": new_balance,"crash_point": crash_point}
    except Exception as e:
        logger.error(f"Error processing {bet.mode} action: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deposit")
async def deposit(user_id: int, amount: float):
    for attempt in range(3):
        try:
            response = requests.post("https://api.paystack.co/transaction/initialize",
                headers={"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"},
                json={"email": f"danny_{user_id}@example.com","amount": int(amount* 100)}
            )
            response.raise_for_status()
            data = response.json()
            new_balance = update_balance(user_id, amount)
            await send_telegram_notification(f"💸 Deposit\nAmount:${amount:.2f}\nNew Balance:${new_balance:.2f}\nPaystack URL: {data['data']['authorization_url']}")
            return {"status":"success","balance": new_balance,"paystack_url": data['data']['authorization_url']}
        except Exception as e:
            logger.error(f"Deposit attempt {attempt + 1} failed: {e}")
            if attempt == 2:
                raise HTTPException(status_code=500, detail=str(e))
            await asyncio.sleep(2)

@app.post("/withdraw")
async def withdraw(user_id: int, amount: float):
    try:
        cur.execute("SELECT balance FROM player WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        balance = result[0] if result else 0
        if balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        new_balance = update_balance(user_id, -amount)
        await send_telegram_notification(f"💳 Withdrawal\nAmount:${amount:.2f}\nNew Balance:${new_balance:.2f}\nNote: Complete withdrawal via Paystack dashboard.")
        return {"status":"success","balance": new_balance}
    except Exception as e:
        logger.error(f"Error processing withdrawal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/balance")
async def get_balance(user_id: int):
    cur.execute("SELECT balance FROM player WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    return {"balance": result[0] if result else 0}

@app.get("/profit_data")
async def get_profit_data():
    cur.execute("SELECT mode, SUM(profit), strftime('%Y-%m-%d', created_at) FROM profits GROUP BY strftime('%Y-%m-%d', created_at), mode")
    data = {"crash": [],"dice": [],"spin": [],"tap": [],"labels": []}
    for mode, profit, date in cur.fetchall():
        if date not in data["labels"]:
            data["labels"].append(date)
        data[mode].append(profit)
    return data

async def start_autoplay():
    asyncio.create_task(autoplay_loop())

if __name__ == "__main__":
    asyncio.run(start_autoplay())
    uvicorn.run(app, host="0.0.0.0", port=8000)