import sqlite3
import requests
import telebot
from telebot import types

# --- CONFIGURATION ---
BOT_TOKEN = "8055477611:AAHLLG0yv5Foow_fI_BoKn0zygG9mdOnlmU"
CHANNEL_USERNAME = "@instapanelannouncement"
ADMIN_ID = 5078131670  # Primary admin
API_KEY = "c9a938d7f66e000f6d3631f15a322965"
UPI_ID = "mithulxfoxey456@fam"

bot = telebot.TeleBot(BOT_TOKEN)
conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

# In-memory store for pending admin actions
pending_actions = {}


# === UTILITY FUNCTIONS ===
def get_setting(key, default=None):
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    return row[0] if row else default


def set_setting(key, value):
    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value))
    conn.commit()


# === DATABASE SETUP ===
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    referred_by INTEGER
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    smm_id TEXT,
    price REAL
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS pending_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    txn_id TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY
)
""")
conn.commit()

# Initialize defaults
if get_setting("referral_system") is None:
    set_setting("referral_system", "on")
if get_setting("referral_limit") is None:
    set_setting("referral_limit", "5")
if get_setting("referral_reward") is None:
    set_setting("referral_reward", "1")  # Default reward: ₹1
if get_setting("channels") is None:
    set_setting("channels", CHANNEL_USERNAME)  # Default channel
if get_setting("help_contact") is None:
    set_setting("help_contact", "@flipperxd")  # Default help contact
if get_setting("upi_id") is None:
    set_setting("upi_id", UPI_ID)  # Default UPI ID
if get_setting("maintenance") is None:
    set_setting("maintenance", "off")  # Default maintenance mode

# Ensure primary admin is added
cur.execute("INSERT OR IGNORE INTO admins (id) VALUES (?)", (ADMIN_ID,))
conn.commit()


# === HELPER FUNCTIONS ===
def is_admin(user_id):
    cur.execute("SELECT id FROM admins WHERE id = ?", (user_id,))
    return cur.fetchone() is not None


def is_user_in_channel(user_id):
    cur.execute("SELECT value FROM settings WHERE key = 'channels'")
    row = cur.fetchone()
    if not row:
        return False  # No channels configured

    channels = row[0].split(',')
    for channel in channels:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"Error checking channel membership for {channel}: {e}")
            return False  # Assume user is not in channel if error occurs
    return True


def send_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💰 Balance", "➕ Add Funds")
    markup.row("🛒 Buy Services", "📢 Referral Link")
    markup.row("📖 Help")
    if is_admin(user_id):
        markup.row("/adminpanel")
    bot.send_message(user_id,
                     "👋 Welcome to Insta SMM Bot!",
                     reply_markup=markup)


# === COMMANDS ===
@bot.message_handler(commands=['start'])
def handle_start(message):
    if get_setting("maintenance") == "on" and not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "🔧 The bot is currently under maintenance. Please try again later.")
        return

    user_id = message.chat.id
    args = message.text.split()
    ref = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    if not is_user_in_channel(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(
            types.InlineKeyboardButton("✅ I Joined",
                                      callback_data="check_joined"))
        bot.send_message(
            user_id,
            "🚫 Please join the channel to use the bot. Click 'I Joined' after joining.",
            reply_markup=markup)
        return

    cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (id, referred_by) VALUES (?, ?)",
                    (user_id, ref))
        if ref and get_setting("referral_system") == "on":
            reward = float(get_setting("referral_reward", "1"))
            cur.execute("SELECT referrals FROM users WHERE id = ?", (ref,))
            row = cur.fetchone()
            if row and row[0] < int(get_setting("referral_limit")):
                cur.execute(
                    "UPDATE users SET referrals = referrals + 1, balance = balance + ? WHERE id = ?",
                    (reward, ref))
                bot.send_message(
                    ref, f"🎉 You earned ₹{reward:.2f} for a new referral!")
        conn.commit()

    send_main_menu(user_id)


@bot.callback_query_handler(func=lambda c: c.data == "check_joined")
def handle_joined(c):
    user_id = c.from_user.id
    if is_user_in_channel(user_id):
        bot.answer_callback_query(c.id, "✅ Verified! You can now use the bot.")
        send_main_menu(user_id)
    else:
        bot.answer_callback_query(
            c.id,
            "❌ You haven't joined the channel yet. Please join and try again.")


@bot.message_handler(func=lambda m: m.text == "📖 Help")
def handle_help(m):
    if get_setting("maintenance") == "on" and not is_admin(m.chat.id):
        bot.send_message(m.chat.id, "🔧 The bot is currently under maintenance. Please try again later.")
        return

    help_contact = get_setting("help_contact", "@flipperxd")
    bot.send_message(m.chat.id, f"ℹ️ Need help? Contact {help_contact}.")


@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def handle_balance(m):
    if get_setting("maintenance") == "on" and not is_admin(m.chat.id):
        bot.send_message(m.chat.id, "🔧 The bot is currently under maintenance. Please try again later.")
        return

    cur.execute("SELECT balance FROM users WHERE id = ?", (m.chat.id,))
    row = cur.fetchone()
    bal = row[0] if row else 0
    bot.send_message(m.chat.id, f"💸 Your balance: ₹{bal:.2f}")


@bot.message_handler(func=lambda m: m.text == "➕ Add Funds")
def handle_add_funds(m):
    if get_setting("maintenance") == "on" and not is_admin(m.chat.id):
        bot.send_message(m.chat.id, "🔧 The bot is currently under maintenance. Please try again later.")
        return

    upi_id = get_setting("upi_id", UPI_ID)
    bot.send_message(m.chat.id,
                     f"💳 Send payment to UPI: `{upi_id}`",
                     parse_mode="Markdown")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ I Paid", callback_data="paid"))
    bot.send_message(m.chat.id, "Tap when done.", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "paid")
def handle_paid(c):
    if get_setting("maintenance") == "on" and not is_admin(c.message.chat.id):
        bot.send_message(c.message.chat.id, "🔧 The bot is currently under maintenance. Please try again later.")
        return

    msg = bot.send_message(c.message.chat.id, "Enter amount paid:")
    bot.register_next_step_handler(msg, process_amount)


def process_amount(m):
    if not m.text.replace('.', '', 1).isdigit():
        bot.send_message(m.chat.id, "❌ Invalid number.")
        return
    amount = float(m.text)
    msg = bot.send_message(m.chat.id, "Enter transaction ID:")
    bot.register_next_step_handler(msg, process_txn, amount)


def process_txn(m, amount):
    txn = m.text.strip()
    uid = m.chat.id
    cur.execute(
        "INSERT INTO pending_payments (user_id, amount, txn_id) VALUES (?, ?, ?)",
        (uid, amount, txn))
    conn.commit()

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Approve",
                                  callback_data=f"approve_{uid}_{txn}"))
    markup.add(
        types.InlineKeyboardButton("❌ Reject",
                                  callback_data=f"reject_{uid}_{txn}"))
    bot.send_message(
        ADMIN_ID,
        f"💰 Payment Request\nUser: {uid}\nAmount: ₹{amount:.2f}\nTxn: {txn}",
        reply_markup=markup)
    bot.send_message(
        uid, "✅ Payment request sent. Please wait for admin approval.")


@bot.callback_query_handler(
    func=lambda c: c.data.startswith(("approve_", "reject_")))
def handle_payment_resp(c):
    action, uid_str, txn = c.data.split("_", 2)
    uid = int(uid_str)
    cur.execute(
        "SELECT amount FROM pending_payments WHERE user_id = ? AND txn_id = ?",
        (uid, txn))
    row = cur.fetchone()
    if not row:
        bot.answer_callback_query(c.id, "❌ Not found.")
        return

    amount = row[0]
    if action == "approve":
        cur.execute("UPDATE users SET balance = balance + ? WHERE id = ?",
                    (amount, uid))
        bot.send_message(
            uid, f"✅ Your payment of ₹{amount:.2f} has been approved.")
    else:
        bot.send_message(uid, f"❌ Your payment of ₹{amount:.2f} was rejected.")

    cur.execute(
        "DELETE FROM pending_payments WHERE user_id = ? AND txn_id = ?",
        (uid, txn))
    conn.commit()
    bot.answer_callback_query(c.id, "Handled.")


@bot.message_handler(func=lambda m: m.text == "📢 Referral Link")
def handle_referral(m):
    if get_setting("maintenance") == "on" and not is_admin(m.chat.id):
        bot.send_message(m.chat.id, "🔧 The bot is currently under maintenance. Please try again later.")
        return

    uid = m.chat.id
    cur.execute("SELECT referrals FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    count = row[0] if row else 0
    reward = float(get_setting("referral_reward", "1"))
    bot.send_message(
        uid,
        f"🌟 Referral Program 🌟\n\n🔗 Your Referral Link:\nhttps://t.me/{bot.get_me().username}?start={uid}\n\n📊 Total Referrals: {count}\n💰 Earn ₹{reward:.2f} per referral!"
    )


# === ADMIN PANEL ===
@bot.message_handler(commands=['adminpanel'])
def handle_admin(m):
    if not is_admin(m.chat.id):
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔁 Toggle Referral", "🔢 Set Referral Limit")
    markup.row("✏️ Edit Balance", "📊 Check Balance")
    markup.row("➕ Add Service", "❌ Delete Service")
    markup.row("📣 Announce", "💰 Edit Invite Reward")
    markup.row("👑 Edit Admins", "📢 Edit Channels")
    markup.row("🔧 Maintenance", "📝 Edit Help Contact")
    markup.row("💳 Edit UPI/QR", "🔙 Back")
    bot.send_message(m.chat.id, "🛠 Admin Panel", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def handle_back(m):
    send_main_menu(m.chat.id)


@bot.message_handler(func=lambda m: m.text == "🔁 Toggle Referral")
def toggle_ref(m):
    if not is_admin(m.chat.id):
        return
    curr = get_setting("referral_system")
    nxt = "off" if curr == "on" else "on"
    set_setting("referral_system", nxt)
    bot.send_message(m.chat.id, f"Referral system is now: {nxt}")


@bot.message_handler(func=lambda m: m.text == "🔢 Set Referral Limit")
def set_ref_limit(m):
    if not is_admin(m.chat.id):
        return
    msg = bot.send_message(
        m.chat.id,
        f"Current limit: {get_setting('referral_limit')}. Enter new limit:")
    bot.register_next_step_handler(msg, process_ref_limit)


def process_ref_limit(m):
    if not is_admin(m.chat.id):
        return
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Invalid number.")
        return
    set_setting("referral_limit", m.text)
    bot.send_message(m.chat.id, f"✅ Referral limit updated to {m.text}.")


@bot.message_handler(func=lambda m: m.text == "📣 Announce")
def announce_prompt(m):
    if not is_admin(m.chat.id):
        return
    msg = bot.send_message(m.chat.id, "Enter announcement message:")
    bot.register_next_step_handler(msg, broadcast_all)


def broadcast_all(m):
    if not is_admin(m.chat.id):
        return
    cur.execute("SELECT id FROM users")
    for (uid,) in cur.fetchall():
        try:
            bot.send_message(uid, f"📢 Announcement:\n{m.text}")
        except:
            pass
    bot.send_message(m.chat.id, "✅ Broadcast sent.")


@bot.message_handler(func=lambda m: m.text == "📊 Check Balance")
def check_bal_prompt(m):
    if not is_admin(m.chat.id):
        return
    msg = bot.send_message(m.chat.id, "Enter User ID to check balance:")
    bot.register_next_step_handler(msg, do_check_balance)


def do_check_balance(m):
    if not is_admin(m.chat.id):
        return
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Invalid ID.")
        return
    uid = int(m.text)
    cur.execute("SELECT balance FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if row:
        bot.send_message(m.chat.id, f"User {uid} balance: ₹{row[0]:.2f}")
    else:
        bot.send_message(m.chat.id, "User not found.")


@bot.message_handler(func=lambda m: m.text == "✏️ Edit Balance")
def edit_balance_prompt(m):
    if not is_admin(m.chat.id):
        return
    msg = bot.send_message(m.chat.id, "Enter User ID to edit balance:")
    bot.register_next_step_handler(msg, edit_balance_select)


def edit_balance_select(m):
    if not is_admin(m.chat.id):
        return
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Invalid ID.")
        return
    uid = int(m.text)
    cur.execute("SELECT id FROM users WHERE id=?", (uid,))
    if not cur.fetchone():
        bot.send_message(m.chat.id, "User not found.")
        return

    pending_actions[m.chat.id] = {"target_uid": uid}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Add", "➖ Deduct", "📝 Set")
    markup.row("🔙 Back")
    bot.send_message(m.chat.id,
                     f"Choose action for user {uid}:",
                     reply_markup=markup)


@bot.message_handler(
    func=lambda m: m.text in ["➕ Add", "➖ Deduct", "📝 Set", "🔙 Back"])
def handle_edit_action(m):
    if not is_admin(m.chat.id):
        return

    if m.text == "🔙 Back":
        pending_actions.pop(m.chat.id, None)
        handle_admin(m)
        return

    if m.chat.id not in pending_actions:
        bot.send_message(
            m.chat.id,
            "⚠️ No user selected. Please choose 'Edit Balance' first.")
        return

    action_map = {"➕ Add": "add", "➖ Deduct": "deduct", "📝 Set": "set"}

    python
    action_map = {"➕ Add": "add", "➖ Deduct": "deduct", "📝 Set": "set"}
    pending_actions[m.chat.id]["action"] = action_map[m.text]
    msg = bot.send_message(m.chat.id, "Enter amount:")
    bot.register_next_step_handler(msg, process_edit_amount)


def process_edit_amount(m):
    if not is_admin(m.chat.id):
        return

    if m.chat.id not in pending_actions:
        bot.send_message(m.chat.id, "⚠️ No pending action found.")
        return

    if not m.text.replace('.', '', 1).isdigit():
        bot.send_message(m.chat.id, "❌ Invalid amount.")
        return

    amount = float(m.text)
    action = pending_actions[m.chat.id]["action"]
    uid = pending_actions[m.chat.id]["target_uid"]

    cur.execute("SELECT balance FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if not row:
        bot.send_message(m.chat.id, "❌ User not found.")
        return

    current_bal = row[0]
    if action == "add":
        new_bal = current_bal + amount
    elif action == "deduct":
        new_bal = current_bal - amount
    else:  # set
        new_bal = amount

    cur.execute("UPDATE users SET balance = ? WHERE id = ?", (new_bal, uid))
    conn.commit()
    bot.send_message(
        m.chat.id,
        f"✅ Updated balance for user {uid}:\nOld: ₹{current_bal:.2f}\nNew: ₹{new_bal:.2f}"
    )
    pending_actions.pop(m.chat.id, None)


@bot.message_handler(func=lambda m: m.text == "➕ Add Service")
def add_service_prompt(m):
    if not is_admin(m.chat.id):
        return
    msg = bot.send_message(m.chat.id, "Enter service name:")
    bot.register_next_step_handler(msg, process_service_name)


def process_service_name(m):
    if not is_admin(m.chat.id):
        return
    pending_actions[m.chat.id] = {"service_name": m.text}
    msg = bot.send_message(m.chat.id, "Enter SMM panel ID:")
    bot.register_next_step_handler(msg, process_smm_id)


def process_smm_id(m):
    if not is_admin(m.chat.id):
        return
    pending_actions[m.chat.id]["smm_id"] = m.text
    msg = bot.send_message(m.chat.id, "Enter price:")
    bot.register_next_step_handler(msg, process_service_price)


def process_service_price(m):
    if not is_admin(m.chat.id):
        return
    if not m.text.replace('.', '', 1).isdigit():
        bot.send_message(m.chat.id, "❌ Invalid price.")
        return

    price = float(m.text)
    service_name = pending_actions[m.chat.id]["service_name"]
    smm_id = pending_actions[m.chat.id]["smm_id"]

    cur.execute(
        "INSERT INTO services (name, smm_id, price) VALUES (?, ?, ?)",
        (service_name, smm_id, price))
    conn.commit()
    bot.send_message(
        m.chat.id,
        f"✅ Added service: {service_name}\nSMM ID: {smm_id}\nPrice: ₹{price:.2f}"
    )
    pending_actions.pop(m.chat.id, None)


@bot.message_handler(func=lambda m: m.text == "❌ Delete Service")
def delete_service_prompt(m):
    if not is_admin(m.chat.id):
        return
    cur.execute("SELECT id, name FROM services")
    services = cur.fetchall()
    if not services:
        bot.send_message(m.chat.id, "❌ No services found.")
        return

    markup = types.InlineKeyboardMarkup()
    for (sid, name) in services:
        markup.add(
            types.InlineKeyboardButton(name, callback_data=f"delete_{sid}"))
    bot.send_message(m.chat.id, "Select service to delete:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("delete_"))
def handle_delete_service(c):
    if not is_admin(c.message.chat.id):
        return
    sid = int(c.data.split("_")[1])
    cur.execute("DELETE FROM services WHERE id = ?", (sid,))
    conn.commit()
    bot.answer_callback_query(c.id, "✅ Service deleted.")
    bot.delete_message(c.message.chat.id, c.message.message_id)


@bot.message_handler(func=lambda m: m.text == "💰 Edit Invite Reward")
def edit_reward_prompt(m):
    if not is_admin(m.chat.id):
        return
    msg = bot.send_message(
        m.chat.id,
        f"Current reward: ₹{get_setting('referral_reward', '1')}. Enter new reward:"
    )
    bot.register_next_step_handler(msg, process_reward)


def process_reward(m):
    if not is_admin(m.chat.id):
        return
    if not m.text.replace('.', '', 1).isdigit():
        bot.send_message(m.chat.id, "❌ Invalid amount.")
        return
    set_setting("referral_reward", m.text)
    bot.send_message(m.chat.id, f"✅ Referral reward updated to ₹{m.text}.")


@bot.message_handler(func=lambda m: m.text == "👑 Edit Admins")
def edit_admins_prompt(m):
    if not is_admin(m.chat.id):
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Add Admin", "❌ Remove Admin")
    markup.row("🔙 Back")
    bot.send_message(m.chat.id, "Admin Management:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "➕ Add Admin")
def add_admin_prompt(m):
    if not is_admin(m.chat.id):
        return
    msg = bot.send_message(m.chat.id, "Enter user ID to add as admin:")
    bot.register_next_step_handler(msg, process_add_admin)


def process_add_admin(m):
    if not is_admin(m.chat.id):
        return
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Invalid ID.")
        return
    uid = int(m.text)
    cur.execute("INSERT OR IGNORE INTO admins (id) VALUES (?)", (uid,))
    conn.commit()
    bot.send_message(m.chat.id, f"✅ Added admin: {uid}")


@bot.message_handler(func=lambda m: m.text == "❌ Remove Admin")
def remove_admin_prompt(m):
    if not is_admin(m.chat.id):
        return
    cur.execute("SELECT id FROM admins WHERE id != ?", (m.chat.id,))
    admins = cur.fetchall()
    if not admins:
        bot.send_message(m.chat.id, "❌ No other admins found.")
        return

    markup = types.InlineKeyboardMarkup()
    for (aid,) in admins:
        markup.add(types.InlineKeyboardButton(str(aid), callback_data=f"remove_{aid}"))
    bot.send_message(m.chat.id, "Select admin to remove:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("remove_"))
def handle_remove_admin(c):
    if not is_admin(c.message.chat.id):
        return
    aid = int(c.data.split("_")[1])
    cur.execute("DELETE FROM admins WHERE id = ?", (aid,))
    conn.commit()
    bot.answer_callback_query(c.id, "✅ Admin removed.")
    bot.delete_message(c.message.chat.id, c.message.message_id)


@bot.message_handler(func=lambda m: m.text == "📢 Edit Channels")
def edit_channels_prompt(m):
    if not is_admin(m.chat.id):
        return
    msg = bot.send_message(
        m.chat.id,
        f"Current channels: {get_setting('channels')}. Enter new channels (comma-separated):"
    )
    bot.register_next_step_handler(msg, process_channels)


def process_channels(m):
    if not is_admin(m.chat.id):
        return
    channels = m.text.strip()
    set_setting("channels", channels)
    bot.send_message(m.chat.id, f"✅ Channels updated to: {channels}")


@bot.message_handler(func=lambda m: m.text == "🔧 Maintenance")
def toggle_maintenance(m):
    if not is_admin(m.chat.id):
        return
    curr = get_setting("maintenance")
    nxt = "on" if curr == "off" else "off"
    set_setting("maintenance", nxt)
    bot.send_message(m.chat.id, f"Maintenance mode is now: {nxt}")


@bot.message_handler(func=lambda m: m.text == "📝 Edit Help Contact")
def edit_help_prompt(m):
    if not is_admin(m.chat.id):
        return
    msg = bot.send_message(
        m.chat.id,
        f"Current help contact: {get_setting('help_contact')}. Enter new contact:"
    )
    bot.register_next_step_handler(msg, process_help_contact)


def process_help_contact(m):
    if not is_admin(m.chat.id):
        return
    set_setting("help_contact", m.text.strip())
    bot.send_message(m.chat.id, f"✅ Help contact updated to: {m.text}")


@bot.message_handler(func=lambda m: m.text == "💳 Edit UPI/QR")
def edit_upi_prompt(m):
    if not is_admin(m.chat.id):
        return
    msg = bot.send_message(
        m.chat.id,
        f"Current UPI ID: {get_setting('upi_id')}. Enter new UPI ID:"
    )
    bot.register_next_step_handler(msg, process_upi)


def process_upi(m):
    if not is_admin(m.chat.id):
        return
    set_setting("upi_id", m.text.strip())
    bot.send_message(m.chat.id, f"✅ UPI ID updated to: {m.text}")


# === SERVICES MENU ===
@bot.message_handler(func=lambda m: m.text == "🛒 Buy Services")
def show_services(m):
    if get_setting("maintenance") == "on" and not is_admin(m.chat.id):
        bot.send_message(m.chat.id, "🔧 The bot is currently under maintenance. Please try again later.")
        return

    cur.execute("SELECT id, name, price FROM services")
    services = cur.fetchall()
    if not services:
        bot.send_message(m.chat.id, "❌ No services available.")
        return

    markup = types.InlineKeyboardMarkup()
    for (sid, name, price) in services:
        markup.add(
            types.InlineKeyboardButton(
                f"{name} (₹{price:.2f})", callback_data=f"buy_{sid}"))
    bot.send_message(m.chat.id, "🛒 Available Services:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def handle_buy_service(c):
    if get_setting("maintenance") == "on" and not is_admin(c.message.chat.id):
        bot.send_message(c.message.chat.id, "🔧 The bot is currently under maintenance. Please try again later.")
        return

    sid = int(c.data.split("_")[1])
    cur.execute("SELECT name, price FROM services WHERE id = ?", (sid,))
    row = cur.fetchone()
    if not row:
        bot.answer_callback_query(c.id, "❌ Service not found.")
        return

    name, price = row
    uid = c.from_user.id
    cur.execute("SELECT balance FROM users WHERE id = ?", (uid,))
    row = cur.fetchone()
    if not row:
        bot.answer_callback_query(c.id, "❌ User not found.")
        return

    bal = row[0]
    if bal < price:
        bot.answer_callback_query(
            c.id,
            f"❌ Insufficient balance. You need ₹{price - bal:.2f} more.")
        return

    # Deduct balance and process order
    cur.execute("UPDATE users SET balance = balance - ? WHERE id = ?",
                (price, uid))
    conn.commit()

    # Simulate API call to SMM panel
    try:
        # Replace with actual API call
        order_id = "SIMULATED_ORDER_ID"
        bot.send_message(
            uid,
            f"✅ Order placed for {name} (₹{price:.2f}).\nOrder ID: {order_id}")
    except Exception as e:
        bot.send_message(uid, f"❌ Failed to place order: {e}")
        # Refund if API fails
        cur.execute("UPDATE users SET balance = balance + ? WHERE id = ?",
                    (price, uid))
        conn.commit()

    bot.answer_callback_query(c.id, "Order processed.")


# === START BOT ===
if __name__ == "__main__":
    print("Bot started.")
    bot.infinity_polling()
