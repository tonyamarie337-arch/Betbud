import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
conn = sqlite3.connect('/mnt/data/solo_cashmachine.db', check_same_thread=False)
cur = conn.cursor()

async def start(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied! This is Danny's private cash machine.")
        return
    cur.execute("INSERT OR IGNORE INTO player (user_id, balance, mode, autoplay, created_at) VALUES (?, 0,?,0,?)",
                (user_id, 'crash', datetime.now().isoformat()))
    conn.commit()
    await update.message.reply_text("Welcome to your Cash Machine! Use /mode <crash|dice|spin|tap>, /deposit <amount>, /autoplay, and play at http://your-render-app.onrender.com")

async def mode(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    try:
        new_mode = context.args[0].lower()
        if new_mode in ['crash', 'dice', 'spin', 'tap']:
            cur.execute("UPDATE player SET mode =? WHERE user_id = ?", (new_mode, user_id))
            conn.commit()
            await update.message.reply_text(f"Mode set to {new_mode}!")
        else:
            await update.message.reply_text("Usage: /mode crash|dice|spin|tap")
    except IndexError:
        await update.message.reply_text("Usage: /mode crash|dice|spin|tap")

async def deposit(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    try:
        amount = float(context.args[0])
        await update.message.reply_text(f"Visit http://your-render-app.onrender.com/deposit?user_id={user_id}&amount={amount} to deposit${amount:.2f}")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /deposit <amount>")

async def balance(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    cur.execute("SELECT balance, mode, autoplay FROM player WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    balance = result[0] if result else 0
    mode = result[1] if result else 'crash'
    autoplay ="On" if result and result[2] else"Off"
    await update.message.reply_text(f"Your balance:${balance:.2f}\nMode: {mode}\nAuto-Play: {autoplay}")

async def riggame(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    try:
        action = context.args[0].lower()
        if action in ['win', 'lose']:
            mode = context.args[1].lower() if len(context.args) > 1 else 'crash'
            if mode not in ['crash', 'dice', 'spin']:
                await update.message.reply_text("Usage: /riggame win|lose [crash|dice|spin]")
                return
            os.environ[f"{mode.upper()}_WIN_RATE"] = '1.0' if action == 'win' else '0.0'
            await update.message.reply_text(f"{mode.capitalize()} game rigged to {action} next bet!")
        else:
            await update.message.reply_text("Usage: /riggame win|lose [crash|dice|spin]")
    except IndexError:
        await update.message.reply_text("Usage: /riggame win|lose [crash|dice|spin]")

async def rigtap(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    try:
        action = context.args[0].lower()
        if action == 'boost':
            os.environ['TAP_PAYOUT_RATE'] = '1.0'
            await update.message.reply_text("Tap-to-Pay rigged to 100% payout next conversion!")
        else:
            await update.message.reply_text("Usage: /rigtap boost")
    except IndexError:
        await update.message.reply_text("Usage: /rigtap boost")

async def profits(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    cur.execute("SELECT SUM(profit) FROM profits")
    total_profit = cur.fetchone()[0] or 0
    await update.message.reply_text(f"Total System Profits:${total_profit:.2f}\nView chart at http://your-render-app.onrender.com/profits")

async def hackcash(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    profit = random.uniform(20, 100)
    cur.execute("SELECT balance FROM player WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    new_balance = (result[0] if result else 0) + profit
    cur.execute("INSERT OR REPLACE INTO player (user_id, balance, mode, autoplay, created_at) VALUES (?,?,?,0,?)",
                (user_id, new_balance, 'crash', datetime.now().isoformat()))
    conn.commit()
    await update.message.reply_text(f"💸 Hacked the System! Added${profit:.2f} to your balance!")
    await context.bot.send_message(chat_id=user_id, text=f"💰 Hack Profit:${profit:.2f}")

async def fling(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    profit = random.uniform(50, 150)
    cur.execute("SELECT balance FROM player WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    new_balance = (result[0] if result else 0) + profit
    cur.execute("INSERT OR REPLACE INTO player (user_id, balance, mode, autoplay, created_at) VALUES (?,?,?,0,?)",
                (user_id, new_balance, 'crash', datetime.now().isoformat()))
    conn.commit()
    await update.message.reply_text(f"🚀 Fling Exploit! Added${profit:.2f} to your balance!")
    await context.bot.send_message(chat_id=user_id, text=f"💰 Fling Profit:${profit:.2f}")

async def nuke(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    profit = random.uniform(100, 500)
    cur.execute("SELECT balance FROM player WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    new_balance = (result[0] if result else 0) + profit
    cur.execute("INSERT OR REPLACE INTO player (user_id, balance, mode, autoplay, created_at) VALUES (?,?,?,0,?)",
                (user_id, new_balance, 'crash', datetime.now().isoformat()))
    conn.commit()
    await update.message.reply_text(f"💥 Nuke Exploit! Added${profit:.2f} to your balance!")
    await context.bot.send_message(chat_id=user_id, text=f"💰 Nuke Profit:${profit:.2f}")

async def refer(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    profit = random.uniform(10, 50)
    cur.execute("SELECT balance FROM player WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    new_balance = (result[0] if result else 0) + profit
    cur.execute("INSERT OR REPLACE INTO player (user_id, balance, mode, autoplay, created_at) VALUES (?,?,?,0,?)",
                (user_id, new_balance, 'crash', datetime.now().isoformat()))
    conn.commit()
    await update.message.reply_text(f"🤝 Referral Bonus! Added${profit:.2f} to your balance!")
    await context.bot.send_message(chat_id=user_id, text=f"💰 Referral Profit:${profit:.2f}")

async def autoplay(update, context):
    user_id = update.message.from_user.id
    if user_id!= int(os.getenv('ADMIN_USER_ID')):
        await update.message.reply_text("Access denied!")
        return
    cur.execute("SELECT autoplay FROM player WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    autoplay = not (result[0] if result else False)
    cur.execute("UPDATE player SET autoplay =? WHERE user_id = ?", (1 if autoplay else 0, user_id))
    conn.commit()
    await update.message.reply_text(f"Auto-Play {'enabled' if autoplay else 'disabled'}!")

def main():
    app = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('mode', mode))
    app.add_handler(CommandHandler('deposit', deposit))
    app.add_handler(CommandHandler('balance', balance))
    app.add_handler(CommandHandler('riggame', riggame))
    app.add_handler(CommandHandler('rigtap', rigtap))
    app.add_handler(CommandHandler('profits', profits))
    app.add_handler(CommandHandler('hackcash', hackcash))
    app.add_handler(CommandHandler('fling', fling))
    app.add_handler(CommandHandler('nuke', nuke))
    app.add_handler(CommandHandler('refer', refer))
    app.add_handler(CommandHandler('autoplay', autoplay))
    app.run_polling()

if __name__ == "__main__":
    main()