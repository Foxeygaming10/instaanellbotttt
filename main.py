import asyncio
import sqlite3
import logging
import requests
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Bot configuration
BOT_TOKEN = "8055477611:AAE2E18M_YYqpE-WZI52tmHa3mumbF3dl2U"
SMM_API_URL = "https://dllsmm.com/api/v2"
SMM_API_KEY = "fb02ac19e4054c14da8c3a12cac1edee"
PRIMARY_ADMIN = 5078131670

# Global variables (will be loaded from database)
HELP_CONTACT = "@admin"  # Variable A
UPI_ID = "example@upi"   # Variable U
REFER_REWARD = 10        # Variable X
REFER_LIMIT = -1         # -1 means unlimited
REQUIRED_CHANNELS = []
ADMINS = [PRIMARY_ADMIN]
REFER_ENABLED = True
MAINTENANCE_MODE = False

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
def init_database():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            referred_by INTEGER,
            joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            service_name TEXT,
            link TEXT,
            quantity INTEGER,
            price REAL,
            status TEXT DEFAULT 'pending',
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Payment requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            utr_number TEXT,
            status TEXT DEFAULT 'pending',
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Services table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            smm_id INTEGER,
            price_per_1000 REAL,
            active INTEGER DEFAULT 1
        )
    ''')
    
    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Initialize default settings
    default_settings = [
        ('help_contact', '@admin'),
        ('upi_id', 'example@upi'),
        ('refer_reward', '10'),
        ('refer_limit', '-1'),
        ('required_channels', '[]'),
        ('admins', f'[{PRIMARY_ADMIN}]'),
        ('refer_enabled', 'True'),
        ('maintenance_mode', 'False')
    ]
    
    for key, value in default_settings:
        cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
    
    conn.commit()
    conn.close()

# Database helper functions
def get_setting(key):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_setting(key, value):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def create_user(user_id, username):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

def update_user_balance(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def set_user_balance(user_id, amount):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_user_balance(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def add_referral(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    result = cursor.fetchall()
    conn.close()
    return [row[0] for row in result]

def get_services():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM services WHERE active = 1')
    result = cursor.fetchall()
    conn.close()
    return result

def add_service(name, smm_id, price):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO services (name, smm_id, price_per_1000) VALUES (?, ?, ?)', (name, smm_id, price))
    conn.commit()
    conn.close()

def remove_service(service_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE services SET active = 0 WHERE id = ?', (service_id,))
    conn.commit()
    conn.close()

def create_order(order_id, user_id, service_name, link, quantity, price):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (order_id, user_id, service_name, link, quantity, price) VALUES (?, ?, ?, ?, ?, ?)',
                   (order_id, user_id, service_name, link, quantity, price))
    conn.commit()
    conn.close()

def create_payment_request(user_id, amount, utr):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO payment_requests (user_id, amount, utr_number) VALUES (?, ?, ?)', (user_id, amount, utr))
    conn.commit()
    conn.close()

# SMM Panel API functions
def place_smm_order(service_id, link, quantity):
    try:
        data = {
            'key': SMM_API_KEY,
            'action': 'add',
            'service': service_id,
            'link': link,
            'quantity': quantity
        }
        response = requests.post(SMM_API_URL, data=data)
        return response.json()
    except Exception as e:
        logger.error(f"Error placing SMM order: {e}")
        return None

def check_smm_order_status(order_id):
    try:
        data = {
            'key': SMM_API_KEY,
            'action': 'status',
            'order': order_id
        }
        response = requests.post(SMM_API_URL, data=data)
        return response.json()
    except Exception as e:
        logger.error(f"Error checking SMM order status: {e}")
        return None

# Helper functions
def is_admin(user_id):
    admins = json.loads(get_setting('admins') or f'[{PRIMARY_ADMIN}]')
    return user_id in admins

def load_global_vars():
    global HELP_CONTACT, UPI_ID, REFER_REWARD, REFER_LIMIT, REQUIRED_CHANNELS, ADMINS, REFER_ENABLED, MAINTENANCE_MODE
    HELP_CONTACT = get_setting('help_contact') or '@admin'
    UPI_ID = get_setting('upi_id') or 'example@upi'
    REFER_REWARD = int(get_setting('refer_reward') or '10')
    REFER_LIMIT = int(get_setting('refer_limit') or '-1')
    REQUIRED_CHANNELS = json.loads(get_setting('required_channels') or '[]')
    ADMINS = json.loads(get_setting('admins') or f'[{PRIMARY_ADMIN}]')
    REFER_ENABLED = get_setting('refer_enabled') == 'True'
    MAINTENANCE_MODE = get_setting('maintenance_mode') == 'True'

async def check_user_in_channels(context, user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            continue
    return True

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_global_vars()
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Handle referral
    if len(context.args) > 0:
        referrer_id = int(context.args[0])
        if referrer_id != user_id and get_user(referrer_id):
            # Check if user doesn't exist yet
            if not get_user(user_id):
                create_user(user_id, username)
                conn = sqlite3.connect('bot_database.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET referred_by = ? WHERE user_id = ?', (referrer_id, user_id))
                conn.commit()
                conn.close()
                
                # Give referral reward
                if REFER_ENABLED:
                    current_referrals = get_user(referrer_id)[2]  # referrals count
                    if REFER_LIMIT == -1 or current_referrals < REFER_LIMIT:
                        update_user_balance(referrer_id, REFER_REWARD)
                        add_referral(referrer_id)
                        await context.bot.send_message(referrer_id, f"🎉 You got ₹{REFER_REWARD} for referring a new user!")
    
    create_user(user_id, username)
    
    if REQUIRED_CHANNELS:
        if not await check_user_in_channels(context, user_id):
            keyboard = []
            for channel in REQUIRED_CHANNELS:
                keyboard.append([InlineKeyboardButton(f"📢 Join {channel}", url=f"https://t.me/{channel[1:]}")])
            keyboard.append([InlineKeyboardButton("✅ I Joined", callback_data="check_membership")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🚀 Welcome! To use this bot, you need to join our channels first:",
                reply_markup=reply_markup
            )
            return
    
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_global_vars()
    
    if MAINTENANCE_MODE and not is_admin(update.effective_user.id):
        await update.message.reply_text("🔧 Bot is under maintenance. Please wait until maintenance is over!")
        return
    
    keyboard = [
        [KeyboardButton("💰 Balance"), KeyboardButton("👥 Refer")],
        [KeyboardButton("❓ Help"), KeyboardButton("💳 Add Funds")],
        [KeyboardButton("🛒 Buy Services"), KeyboardButton("📋 Order Status")]
    ]
    
    if is_admin(update.effective_user.id):
        keyboard.append([KeyboardButton("⚙️ Admin Panel")])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"🏠 Welcome to Instagram Services Panel!\n\nChoose an option:",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_global_vars()
    text = update.message.text
    user_id = update.effective_user.id
    
    if MAINTENANCE_MODE and not is_admin(user_id) and text not in ["/start"]:
        await update.message.reply_text("🔧 Bot is under maintenance. Please wait until maintenance is over!")
        return
    
    if text == "💰 Balance":
        balance = get_user_balance(user_id)
        await update.message.reply_text(f"💰 Your Balance: ₹{balance:.2f}")
    
    elif text == "👥 Refer":
        if not REFER_ENABLED:
            await update.message.reply_text("❌ Referral program is currently not available.")
            return
            
        user_data = get_user(user_id)
        referrals = user_data[2] if user_data else 0
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        await update.message.reply_text(
            f"👥 Refer & Earn ₹{REFER_REWARD} per referral!\n\n"
            f"🔗 Your referral link:\n`{referral_link}`\n\n"
            f"📊 Total referrals: {referrals}",
            parse_mode='Markdown'
        )
    
    elif text == "❓ Help":
        await update.message.reply_text(f"❓ Need help! Contact {HELP_CONTACT}")
    
    elif text == "💳 Add Funds":
        keyboard = [[InlineKeyboardButton("✅ PAYED", callback_data="payment_done")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"💳 Pay to: {UPI_ID}\n\nAfter payment, click the button below:",
            reply_markup=reply_markup
        )
    
    elif text == "🛒 Buy Services":
        services = get_services()
        if not services:
            await update.message.reply_text("❌ No services available at the moment.")
            return
        
        keyboard = []
        for service in services:
            keyboard.append([InlineKeyboardButton(
                f"{service[1]} - ₹{service[3]}/1000", 
                callback_data=f"service_{service[0]}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🛒 Choose a service:", reply_markup=reply_markup)
    
    elif text == "📋 Order Status":
        context.user_data['waiting_for'] = 'order_status'
        await update.message.reply_text("📋 Please send your order ID:")
    
    elif text == "⚙️ Admin Panel" and is_admin(user_id):
        await show_admin_panel(update, context)
    
    # Handle admin panel states
    elif context.user_data.get('waiting_for') == 'order_status':
        order_id = text.strip()
        status_result = check_smm_order_status(order_id)
        
        if status_result:
            status = status_result.get('status', 'unknown')
            if status.lower() in ['completed', 'complete']:
                await update.message.reply_text(f"✅ Order {order_id} is completed!")
            elif status.lower() in ['pending', 'in progress', 'processing']:
                await update.message.reply_text(f"⏳ Order {order_id} is pending!")
            else:
                await update.message.reply_text(f"📋 Order {order_id} status: {status}")
        else:
            await update.message.reply_text("❌ Could not check order status. Please verify your order ID.")
        
        context.user_data.pop('waiting_for', None)
    
    # Handle payment amount input
    elif context.user_data.get('waiting_for') == 'payment_amount':
        try:
            amount = float(text)
            context.user_data['payment_amount'] = amount
            context.user_data['waiting_for'] = 'payment_utr'
            await update.message.reply_text("📝 Please enter your UTR number:")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount.")
    
    # Handle UTR input
    elif context.user_data.get('waiting_for') == 'payment_utr':
        utr = text.strip()
        amount = context.user_data.get('payment_amount')
        
        create_payment_request(user_id, amount, utr)
        
        # Send to admin
        for admin_id in ADMINS:
            keyboard = [
                [InlineKeyboardButton("✅ Accept", callback_data=f"accept_payment_{user_id}_{amount}_{utr}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"reject_payment_{user_id}_{amount}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await context.bot.send_message(
                    admin_id,
                    f"💳 New Payment Request\n\n"
                    f"👤 User ID: {user_id}\n"
                    f"💰 Amount: ₹{amount}\n"
                    f"🔢 UTR: {utr}",
                    reply_markup=reply_markup
                )
            except:
                continue
        
        await update.message.reply_text("📤 Payment request sent! Please wait for admin approval.")
        context.user_data.clear()
    
    # Handle service link input
    elif context.user_data.get('waiting_for') == 'service_link':
        link = text.strip()
        context.user_data['service_link'] = link
        context.user_data['waiting_for'] = 'service_quantity'
        await update.message.reply_text("📊 Please enter the quantity:")
    
    # Handle service quantity input
    elif context.user_data.get('waiting_for') == 'service_quantity':
        try:
            quantity = int(text)
            service_id = context.user_data.get('selected_service')
            link = context.user_data.get('service_link')
            
            # Get service details
            conn = sqlite3.connect('bot_database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM services WHERE id = ?', (service_id,))
            service = cursor.fetchone()
            conn.close()
            
            if not service:
                await update.message.reply_text("❌ Service not found.")
                context.user_data.clear()
                return
            
            service_name, smm_id, price_per_1000 = service[1], service[2], service[3]
            total_price = (quantity / 1000) * price_per_1000
            
            # Check balance
            user_balance = get_user_balance(user_id)
            if user_balance < total_price:
                await update.message.reply_text(f"❌ Insufficient balance! You need ₹{total_price:.2f} but have ₹{user_balance:.2f}")
                context.user_data.clear()
                return
            
            # Place order on SMM panel
            smm_result = place_smm_order(smm_id, link, quantity)
            
            if smm_result and 'order' in smm_result:
                order_id = str(smm_result['order'])
                
                # Deduct balance
                update_user_balance(user_id, -total_price)
                
                # Save order
                create_order(order_id, user_id, service_name, link, quantity, total_price)
                
                await update.message.reply_text(
                    f"✅ Order placed successfully!\n\n"
                    f"🆔 Order ID: `{order_id}`\n"
                    f"📋 Service: {service_name}\n"
                    f"📊 Quantity: {quantity}\n"
                    f"💰 Price: ₹{total_price:.2f}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Failed to place order. Please try again.")
            
            context.user_data.clear()
            
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid quantity.")
    
    # Admin panel handlers
    elif context.user_data.get('waiting_for') == 'check_balance_user':
        try:
            target_user_id = int(text)
            balance = get_user_balance(target_user_id)
            await update.message.reply_text(f"💰 User {target_user_id} balance: ₹{balance:.2f}")
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid user ID.")
    
    elif context.user_data.get('waiting_for') == 'edit_balance_user':
        try:
            target_user_id = int(text)
            context.user_data['target_user_id'] = target_user_id
            
            keyboard = [
                [InlineKeyboardButton("➕ Add", callback_data="balance_add")],
                [InlineKeyboardButton("➖ Deduct", callback_data="balance_deduct")],
                [InlineKeyboardButton("📝 Set", callback_data="balance_set")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("💰 Choose action:", reply_markup=reply_markup)
            context.user_data.pop('waiting_for', None)
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid user ID.")
    
    elif context.user_data.get('waiting_for') == 'balance_amount':
        try:
            amount = float(text)
            target_user_id = context.user_data.get('target_user_id')
            action = context.user_data.get('balance_action')
            
            if action == 'add':
                update_user_balance(target_user_id, amount)
                await update.message.reply_text(f"✅ Added ₹{amount} to user {target_user_id}")
            elif action == 'deduct':
                update_user_balance(target_user_id, -amount)
                await update.message.reply_text(f"✅ Deducted ₹{amount} from user {target_user_id}")
            elif action == 'set':
                set_user_balance(target_user_id, amount)
                await update.message.reply_text(f"✅ Set balance of user {target_user_id} to ₹{amount}")
            
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount.")
    
    elif context.user_data.get('waiting_for') == 'help_contact':
        if text.startswith('@'):
            set_setting('help_contact', text)
            await update.message.reply_text(f"✅ Help contact updated to {text}")
            context.user_data.clear()
        else:
            await update.message.reply_text("❌ Please enter a username starting with @")
    
    elif context.user_data.get('waiting_for') == 'upi_id':
        set_setting('upi_id', text)
        await update.message.reply_text(f"✅ UPI ID updated to {text}")
        context.user_data.clear()
    
    elif context.user_data.get('waiting_for') == 'refer_reward':
        try:
            amount = int(text)
            set_setting('refer_reward', str(amount))
            await update.message.reply_text(f"✅ Refer reward updated to ₹{amount}")
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount.")
    
    elif context.user_data.get('waiting_for') == 'refer_limit':
        try:
            limit = int(text)
            set_setting('refer_limit', str(limit))
            if limit == -1:
                await update.message.reply_text("✅ Refer limit set to unlimited")
            else:
                await update.message.reply_text(f"✅ Refer limit set to {limit}")
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number.")
    
    elif context.user_data.get('waiting_for') == 'add_admin':
        try:
            new_admin_id = int(text)
            admins = json.loads(get_setting('admins'))
            if new_admin_id not in admins:
                admins.append(new_admin_id)
                set_setting('admins', json.dumps(admins))
                await update.message.reply_text(f"✅ User {new_admin_id} added as admin")
            else:
                await update.message.reply_text("❌ User is already an admin")
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid user ID.")
    
    elif context.user_data.get('waiting_for') == 'remove_admin':
        try:
            remove_admin_id = int(text)
            if remove_admin_id == PRIMARY_ADMIN:
                await update.message.reply_text("❌ Cannot remove primary admin")
            else:
                admins = json.loads(get_setting('admins'))
                if remove_admin_id in admins:
                    admins.remove(remove_admin_id)
                    set_setting('admins', json.dumps(admins))
                    await update.message.reply_text(f"✅ User {remove_admin_id} removed from admin")
                else:
                    await update.message.reply_text("❌ User is not an admin")
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid user ID.")
    
    elif context.user_data.get('waiting_for') == 'add_channel':
        if text.startswith('@'):
            channels = json.loads(get_setting('required_channels') or '[]')
            if text not in channels:
                channels.append(text)
                set_setting('required_channels', json.dumps(channels))
                await update.message.reply_text(f"✅ Channel {text} added to required channels")
            else:
                await update.message.reply_text("❌ Channel already exists")
            context.user_data.clear()
        else:
            await update.message.reply_text("❌ Please enter a channel ID starting with @")
    
    elif context.user_data.get('waiting_for') == 'remove_channel':
        if text.startswith('@'):
            channels = json.loads(get_setting('required_channels') or '[]')
            if text in channels:
                channels.remove(text)
                set_setting('required_channels', json.dumps(channels))
                await update.message.reply_text(f"✅ Channel {text} removed from required channels")
            else:
                await update.message.reply_text("❌ Channel not found")
            context.user_data.clear()
        else:
            await update.message.reply_text("❌ Please enter a channel ID starting with @")
    
    elif context.user_data.get('waiting_for') == 'broadcast_message':
        users = get_all_users()
        sent = 0
        for user_id in users:
            try:
                await context.bot.send_message(user_id, f"📢 Broadcast:\n\n{text}")
                sent += 1
            except:
                continue
        await update.message.reply_text(f"✅ Broadcast sent to {sent} users")
        context.user_data.clear()
    
    elif context.user_data.get('waiting_for') == 'service_name':
        context.user_data['service_name'] = text
        context.user_data['waiting_for'] = 'service_smm_id'
        await update.message.reply_text("🔢 Please enter SMM panel service ID:")
    
    elif context.user_data.get('waiting_for') == 'service_smm_id':
        try:
            smm_id = int(text)
            context.user_data['service_smm_id'] = smm_id
            context.user_data['waiting_for'] = 'service_price'
            await update.message.reply_text("💰 Please enter price per 1000:")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid service ID.")
    
    elif context.user_data.get('waiting_for') == 'service_price':
        try:
            price = float(text)
            service_name = context.user_data.get('service_name')
            smm_id = context.user_data.get('service_smm_id')
            
            add_service(service_name, smm_id, price)
            await update.message.reply_text(f"✅ Service '{service_name}' added successfully!")
            context.user_data.clear()
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid price.")

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Check Balance", callback_data="check_balance")],
        [InlineKeyboardButton("✏️ Edit Balance", callback_data="edit_balance")],
        [InlineKeyboardButton("❓ Edit Help", callback_data="edit_help")],
        [InlineKeyboardButton("💳 Edit UPI ID", callback_data="edit_upi")],
        [InlineKeyboardButton("🎁 Edit Per Refer", callback_data="edit_refer_reward")],
        [InlineKeyboardButton("🔢 Set Refer Limit", callback_data="set_refer_limit")],
        [InlineKeyboardButton("👥 Edit Admins", callback_data="edit_admins")],
        [InlineKeyboardButton("📢 Edit Channels", callback_data="edit_channels")],
        [InlineKeyboardButton("📡 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("🎁 Toggle Refer", callback_data="toggle_refer")],
        [InlineKeyboardButton("🔧 Maintenance", callback_data="toggle_maintenance")],
        [InlineKeyboardButton("🛒 Edit Services", callback_data="edit_services")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "⚙️ Admin Panel" if hasattr(update, 'message') else "⚙️ Admin Panel"
    
    if hasattr(update, 'message'):
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    load_global_vars()
    user_id = query.from_user.id
    data = query.data
    
    if data == "check_membership":
        if await check_user_in_channels(context, user_id):
            await query.edit_message_text("✅ Welcome! You can now use the bot.")
            await show_main_menu(update, context)
        else:
            await query.answer("❌ Please join all required channels first!", show_alert=True)
    
    elif data == "main_menu":
        await show_main_menu(update, context)
    
    elif data == "payment_done":
        context.user_data['waiting_for'] = 'payment_amount'
        await query.edit_message_text("💰 Please enter the amount you paid:")
    
    elif data.startswith("service_"):
        service_id = int(data.split("_")[1])
        context.user_data['selected_service'] = service_id
        context.user_data['waiting_for'] = 'service_link'
        await query.edit_message_text("🔗 Please send the Instagram link:")
    
    elif data.startswith("accept_payment_"):
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        parts = data.split("_")
        payer_id = int(parts[2])
        amount = float(parts[3])
        
        update_user_balance(payer_id, amount)
        await query.edit_message_text("✅ Payment approved!")
        
        try:
            await context.bot.send_message(payer_id, f"✅ Your payment of ₹{amount} has been approved!")
        except:
            pass
    
    elif data.startswith("reject_payment_"):
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        parts = data.split("_")
        payer_id = int(parts[2])
        amount = float(parts[3])
        
        await query.edit_message_text("❌ Payment rejected!")
        
        try:
            await context.bot.send_message(payer_id, f"❌ Your payment of ₹{amount} was rejected. Any issue contact {HELP_CONTACT}")
        except:
            pass
    
    # Admin panel callbacks
    elif data == "admin_panel":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        await show_admin_panel(update, context)
    
    elif data == "check_balance":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        context.user_data['waiting_for'] = 'check_balance_user'
        await query.edit_message_text("👤 Please enter user ID to check balance:")
    
    elif data == "edit_balance":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        context.user_data['waiting_for'] = 'edit_balance_user'
        await query.edit_message_text("👤 Please enter user ID to edit balance:")
    
    elif data in ["balance_add", "balance_deduct", "balance_set"]:
        context.user_data['balance_action'] = data.split("_")[1]
        context.user_data['waiting_for'] = 'balance_amount'
        action_text = {"add": "add", "deduct": "deduct", "set": "set to"}[data.split("_")[1]]
        await query.edit_message_text(f"💰 Enter amount to {action_text}:")
    
    elif data == "edit_help":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        context.user_data['waiting_for'] = 'help_contact'
        await query.edit_message_text("❓ Enter new help contact (with @):")
    
    elif data == "edit_upi":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        context.user_data['waiting_for'] = 'upi_id'
        await query.edit_message_text("💳 Enter new UPI ID:")
    
    elif data == "edit_refer_reward":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        context.user_data['waiting_for'] = 'refer_reward'
        await query.edit_message_text("🎁 Enter new refer reward amount:")
    
    elif data == "set_refer_limit":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        context.user_data['waiting_for'] = 'refer_limit'
        await query.edit_message_text("🔢 Enter refer limit (-1 for unlimited):")
    
    elif data == "edit_admins":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Admin", callback_data="add_admin")],
            [InlineKeyboardButton("➖ Remove Admin", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👥 Admin Management:", reply_markup=reply_markup)
    
    elif data == "add_admin":
        context.user_data['waiting_for'] = 'add_admin'
        await query.edit_message_text("👤 Enter user ID to make admin:")
    
    elif data == "remove_admin":
        context.user_data['waiting_for'] = 'remove_admin'
        await query.edit_message_text("👤 Enter user ID to remove from admin:")
    
    elif data == "edit_channels":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel")],
            [InlineKeyboardButton("➖ Remove Channel", callback_data="remove_channel")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📢 Channel Management:", reply_markup=reply_markup)
    
    elif data == "add_channel":
        context.user_data['waiting_for'] = 'add_channel'
        await query.edit_message_text("📢 Enter channel ID (with @):")
    
    elif data == "remove_channel":
        context.user_data['waiting_for'] = 'remove_channel'
        await query.edit_message_text("📢 Enter channel ID to remove (with @):")
    
    elif data == "broadcast":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        context.user_data['waiting_for'] = 'broadcast_message'
        await query.edit_message_text("📡 Enter message to broadcast:")
    
    elif data == "toggle_refer":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        current_state = get_setting('refer_enabled') == 'True'
        new_state = not current_state
        set_setting('refer_enabled', str(new_state))
        
        status = "enabled" if new_state else "disabled"
        await query.edit_message_text(f"🎁 Referral system {status}!")
        await asyncio.sleep(1)
        await show_admin_panel(update, context)
    
    elif data == "toggle_maintenance":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        current_state = get_setting('maintenance_mode') == 'True'
        new_state = not current_state
        set_setting('maintenance_mode', str(new_state))
        
        status = "enabled" if new_state else "disabled"
        await query.edit_message_text(f"🔧 Maintenance mode {status}!")
        await asyncio.sleep(1)
        await show_admin_panel(update, context)
    
    elif data == "edit_services":
        if not is_admin(user_id):
            await query.answer("❌ Unauthorized", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Service", callback_data="add_service")],
            [InlineKeyboardButton("➖ Remove Service", callback_data="remove_service")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🛒 Service Management:", reply_markup=reply_markup)
    
    elif data == "add_service":
        context.user_data['waiting_for'] = 'service_name'
        await query.edit_message_text("📝 Enter service name:")
    
    elif data == "remove_service":
        services = get_services()
        if not services:
            await query.edit_message_text("❌ No services available to remove.")
            return
        
        keyboard = []
        for service in services:
            keyboard.append([InlineKeyboardButton(
                f"🗑️ {service[1]}", 
                callback_data=f"delete_service_{service[0]}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="edit_services")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🗑️ Select service to remove:", reply_markup=reply_markup)
    
    elif data.startswith("delete_service_"):
        service_id = int(data.split("_")[2])
        remove_service(service_id)
        await query.edit_message_text("✅ Service removed successfully!")
        await asyncio.sleep(1)
        await show_admin_panel(update, context)

def main():
    # Initialize database
    init_database()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Run the bot
    print("🚀 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

