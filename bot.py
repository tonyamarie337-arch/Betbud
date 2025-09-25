from telegram.ext import Application, CommandHandler, MessageHandler, filters
import logging
import sqlite3
import os
from dotenv import load_dotenv
import random
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
HOUSE_EDGE = float(os.getenv("HOUSE_EDGE", 0.1))

conn = sqlite3.connect("/mnt/data/solo_cashmachine.db", check_same_thread=False)
cur = conn.cursor()

async def start(update, context):
    user_id = update.effective_user.id
    cur.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    conn.commit()
    await update.message.reply_text("Welcome to Betbud! Rule your empire with /deposit, /mode, /bet, /balance, /profits, /riggame, /rigtap, /autoplay, /nuke, /superhack, /fling, /refer, /megahack, /miniapp.")

async def deposit(update, context):
    user_id = update.effective_user.id
    amount = float(context.args[0]) if context.args else 10
    url = f"https://api.paystack.co/transaction/initialize"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    data = {"email": f"user{user_id}@betbud.com","amount": int(amount* 100),"metadata": {"user_id": str(user_id)}}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        await update.message.reply_text(f"Deposit {amount} NGN: {response.json()['data']['authorization_url']}")
    else:
        await update.message.reply_text("Deposit failed. Try again.")

async def mode(update, context):
    user_id = update.effective_user.id
    mode = context.args[0].lower() if context.args else"crash"
    tap_mode = context.args[1].lower() if len(context.args) > 1 and mode =="tap" else"normal"
    if mode not in ["crash","dice","spin","tap","roulette","plinko"]:
        await update.message.reply_text("Invalid mode. Use crash, dice, spin, tap, roulette, or plinko.")
        return
    if mode =="tap" and tap_mode not in ["normal","pro"]:
        await update.message.reply_text("Tap mode must be normal or pro.")
        return
    cur.execute("UPDATE users SET tap_mode =? WHERE user_id = ?", (tap_mode, user_id))
    conn.commit()
    await update.message.reply_text(f"Mode set to {mode}{' (' + tap_mode + ')' if mode == 'tap' else ''}.")

async def bet(update, context):
    user_id = update.effective_user.id
    bet_amount = float(context.args[0]) if context.args else 10
    multiplier = float(context.args[1]) if len(context.args) > 1 else 2.0
    cur.execute("SELECT tap_mode FROM users WHERE user_id = ?", (user_id,))
    tap_mode = cur.fetchone()[0]
    mode = context.user_data.get("mode","crash")
    response = requests.post(f"https://betbud.onrender.com/bet/{mode}", json={"user_id": user_id,"bet_amount": bet_amount,"multiplier": multiplier})
    if response.status_code == 200:
        data = response.json()
        await update.message.reply_text(f"Bet {bet_amount} NGN: {'Won' if data['win'] else 'Lost'}! Profit: {data['profit']:.2f} NGN")
    else:
        await update.message.reply_text("Bet failed. Check balance or try again.")

async def balance(update, context):
    user_id = update.effective_user.id
    response = requests.get(f"https://betbud.onrender.com/balance/{user_id}")
    if response.status_code == 200:
        balance = response.json()["balance"]
        cur.execute("SELECT tap_mode FROM users WHERE user_id = ?", (user_id,))
        tap_mode = cur.fetchone()[0]
        await update.message.reply_text(f"Balance: {balance:.2f} NGN\nTap Mode: {tap_mode}")
    else:
        await update.message.reply_text("Error fetching balance.")

async def profits(update, context):
    cur.execute("SELECT mode, bet_amount, profit, created_at FROM bets WHERE user_id = ?", (7751724771,))
    bets = cur.fetchall()
    total_profit = sum(b[2] for b in bets)
    msg = f"Total Profit: {total_profit:.2f} NGN\nRecent Bets:\n" +"\n".join(f"{b[0]}: Bet {b[1]:.2f}, Profit {b[2]:.2f} ({b[3]})" for b in bets[-5:])
    await update.message.reply_text(msg)

async def riggame(update, context):
    user_id = update.effective_user.id
    if user_id!= ADMIN_USER_ID:
        await update.message.reply_text("Access denied, you sneaky fuck!")
        return
    mode = context.args[0].lower() if context.args else"crash"
    outcome = context.args[1].lower() if len(context.args) > 1 else"win"
    if mode not in ["crash","dice","spin","tap","roulette","plinko"]:
        await update.message.reply_text("Invalid mode, asshole. Use crash, dice, spin, tap, roulette, or plinko.")
        return
    cur.execute("UPDATE users SET balance = balance +? WHERE user_id = ?", (1000 if outcome =="win" else -1000, user_id))
    conn.commit()
    await update.message.reply_text(f"Rigged {mode} to {outcome}! Balance {'+' if outcome == 'win' else '-'}$1000, you sly bastard.")

async def rigtap(update, context):
    user_id = update.effective_user.id
    if user_id!= ADMIN_USER_ID:
        await update.message.reply_text("Nice try, fucker! Admin only!")
        return
    action = context.args[0].lower() if context.args else"boost"
    if action =="boost":
        cur.execute("UPDATE users SET balance = balance + 500 WHERE user_id = ?", (user_id,))
        conn.commit()
        await update.message.reply_text("Tap payout juiced! +500 NGN, you greedy prick.")
    elif action =="mode":
        tap_mode = context.args[1].lower() if len(context.args) > 1 else"pro"
        cur.execute("UPDATE users SET tap_mode =? WHERE user_id = ?", (tap_mode, user_id))
        conn.commit()
        await update.message.reply_text(f"Tap mode cranked to {tap_mode}, you slick hustler.")

async def autoplay(update, context):
    user_id = update.effective_user.id
    if user_id!= ADMIN_USER_ID:
        await update.message.reply_text("Fuck off, only admins can autoplay!")
        return
    for_ in range(100):
        bet_amount = 10
        multiplier = 2.0
        mode = context.user_data.get("mode","crash")
        response = requests.post(f"https://betbud.onrender.com/bet/{mode}", json={"user_id": user_id,"bet_amount": bet_amount,"multiplier": multiplier})
        if response.status_code!= 200:
            await update.message.reply_text("Autoplay crashed, shit! Check logs.")
            return
    await update.message.reply_text("Autoplay: 100 bets slammed through, you money-grubbing genius!")

async def nuke(update, context):
    user_id = update.effective_user.id
    if user_id!= ADMIN_USER_ID:
        await update.message.reply_text("No nuke for you, punk!")
        return
    amount = random.randint(100, 500)
    cur.execute("UPDATE users SET balance = balance +? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    await update.message.reply_text(f"Nuke dropped! +{amount} NGN looted, you fucking legend!")

async def superhack(update, context):
    user_id = update.effective_user.id
    if user_id!= ADMIN_USER_ID:
        await update.message.reply_text("Superhack’s for bosses, not you, bitch!")
        return
    cur.execute("UPDATE users SET balance = balance + 1000 WHERE user_id = ?", (user_id,))
    conn.commit()
    await update.message.reply_text("Superhack unleashed! +1000 NGN snatched, you ruthless fuck!")

async def fling(update, context):
    user_id = update.effective_user.id
    if user_id!= ADMIN_USER_ID:
        await update.message.reply_text("Fling’s for admins, you little shit!")
        return
    amount = random.randint(20, 100)
    cur.execute("UPDATE users SET balance = balance +? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    await update.message.reply_text(f"Fling exploit landed! +{amount} NGN, you crafty bastard!")

async def refer(update, context):
    user_id = update.effective_user.id
    if user_id!= ADMIN_USER_ID:
        await update.message.reply_text("Fake referrals are admin-only, fucker!")
        return
    amount = random.randint(10, 50)
    cur.execute("UPDATE users SET balance = balance +? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    await update.message.reply_text(f"Fake referral cashed! +{amount} NGN, you sneaky prick.")

async def megahack(update, context):
    user_id = update.effective_user.id
    if user_id!= ADMIN_USER_ID:
        await update.message.reply_text("Megahack’s for the big dogs, not you, asshole!")
        return
    cur.execute("UPDATE users SET balance = balance + 5000 WHERE user_id = ?", (user_id,))
    conn.commit()
    await update.message.reply_text("Megahack fuckin’ obliterated! +5000 NGN, you goddamn kingpin!")

async def miniapp(update, context):
    user_id = update.effective_user.id
    await update.message.reply_text("Launch the Betbud Mini App: https://betbud.onrender.com/miniapp?user_id=" + str(user_id))

def main():
    app = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("mode", mode))
    app.add_handler(CommandHandler("bet", bet))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("profits", profits))
    app.add_handler(CommandHandler("riggame", riggame))
    app.add_handler(CommandHandler("rigtap", rigtap))
    app.add_handler(CommandHandler("autoplay", autoplay))
    app.add_handler(CommandHandler("nuke", nuke))
    app.add_handler(CommandHandler("superhack", superhack))
    app.add_handler(CommandHandler("fling", fling))
    app.add_handler(CommandHandler("refer", refer))
    app.add_handler(CommandHandler("megahack", megahack))
    app.add_handler(CommandHandler("miniapp", miniapp))
    app.run_polling()

if __name__ == "__main__":
    main()
