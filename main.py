from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import random
from datetime import datetime
import uvicorn
import logging
import os
from dotenv import load_dotenv
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
HOUSE_EDGE = float(os.getenv("HOUSE_EDGE", 0.1))
CRASH_WIN_RATE = float(os.getenv("CRASH_WIN_RATE", 0.8))
DICE_WIN_RATE = float(os.getenv("DICE_WIN_RATE", 0.66))
SPIN_WIN_RATE = float(os.getenv("SPIN_WIN_RATE", 0.5))
TAP_PAYOUT_RATE = float(os.getenv("TAP_PAYOUT_RATE", 0.9))
ROULETTE_WIN_RATE = float(os.getenv("ROULETTE_WIN_RATE", 0.6))
PLINKO_WIN_RATE = float(os.getenv("PLINKO_WIN_RATE", 0.7))

conn = sqlite3.connect("/mnt/data/solo_cashmachine.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    tap_mode TEXT DEFAULT 'normal')""")
cur.execute("""
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    bet_amount REAL,
    multiplier REAL,
    outcome TEXT,
    profit REAL,
    mode TEXT,
    created_at TEXT)""")
conn.commit()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    if data["event"] =="charge.success":
        user_id = int(data["data"]["metadata"]["user_id"])
        amount = data["data"]["amount"] / 100
        cur.execute("UPDATE users SET balance = balance +? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        logger.info(f"Deposit {amount} NGN for user {user_id}")
    return {"status":"success"}

@app.post("/bet/{mode}")
async def place_bet(mode: str, request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    bet_amount = float(data.get("bet_amount"))
    multiplier = float(data.get("multiplier", 2.0))
    cur.execute("SELECT balance, tap_mode FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    if not user or user[0] < bet_amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    win = False
    profit = -bet_amount
    if mode =="crash":
        win = random.random() < CRASH_WIN_RATE
        if win:
            profit = bet_amount* (multiplier* (1 - HOUSE_EDGE)) - bet_amount
    elif mode =="dice":
        win = random.random() < DICE_WIN_RATE
        if win:
            profit = bet_amount* (multiplier* (1 - HOUSE_EDGE)) - bet_amount
    elif mode =="spin":
        win = random.random() < SPIN_WIN_RATE
        if win:
            profit = bet_amount* (multiplier* (1 - HOUSE_EDGE)) - bet_amount
    elif mode =="tap":
        win = random.random() < TAP_PAYOUT_RATE
        tap_multiplier = 1.5 if user[1] =="normal" else 3.0
        if win:
            profit = bet_amount* (tap_multiplier* (1 - HOUSE_EDGE)) - bet_amount
    elif mode =="roulette":
        win = random.random() < ROULETTE_WIN_RATE
        if win:
            profit = bet_amount* (multiplier* (1 - HOUSE_EDGE)) - bet_amount
    elif mode =="plinko":
        win = random.random() < PLINKO_WIN_RATE
        plinko_multipliers = [2.0, 3.0, 5.0, 10.0]
        multiplier = random.choice(plinko_multipliers) if win else 0
        if win:
            profit = bet_amount* (multiplier* (1 - HOUSE_EDGE)) - bet_amount
    cur.execute("UPDATE users SET balance = balance +? WHERE user_id = ?", (profit, user_id))
    cur.execute("INSERT INTO bets (user_id, bet_amount, multiplier, outcome, profit, mode, created_at) VALUES (?,?,?,?,?,?,?)",
                (user_id, bet_amount, multiplier,"win" if win else"lose", profit, mode, datetime.now().isoformat()))
    conn.commit()
    return {"status":"success","win": win,"profit": profit}

@app.get("/balance/{user_id}")
async def get_balance(user_id: int):
    cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cur.fetchone()
    if balance:
        return {"balance": balance[0]}
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/profits", response_class=HTMLResponse)
async def profits(request: Request):
    cur.execute("SELECT mode, bet_amount, profit, created_at FROM bets WHERE user_id = ?", (7751724771,))
    bets = [{"mode": b[0],"bet_amount": b[1],"profit": b[2],"created_at": b[3]} for b in cur.fetchall()]
    return templates.TemplateResponse("profits.html", {"request": request,"bets": bets})

@app.get("/healthz")
async def health():
    return {"status":"ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
