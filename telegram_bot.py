import logging
import sqlite3
import asyncio
import aiohttp
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

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
MAINTENANCE_MODE = False
REFER_ENABLED = True

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
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')
    
    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER,
            service_name TEXT,
            instagram_link TEXT,
            quantity INTEGER,
            amount REAL,
            status TEXT DEFAULT 'pending',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Services table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            smm_id INTEGER,
            price_per_1000 REAL
        )
    ''')
    
    # Required channels table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS required_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_link TEXT,
            channel_id TEXT
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
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Initialize settings
    settings = [
        ('help_contact', '@admin'),
        ('upi_id', 'example@upi'),
        ('refer_reward', '10'),
        ('refer_limit', '-1'),
        ('maintenance_mode', 'False'),
        ('refer_enabled', 'True')
    ]
    
    cursor.executemany('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', settings)
    
    # Add primary admin
    cursor.execute('INSERT OR IGNORE INTO users (user_id, is_admin) VALUES (?, 1)', (PRIMARY_ADMIN,))
    
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
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def create_user(user_id, username=None, referred_by=None):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, referred_by) 
        VALUES (?, ?, ?)
    ''', (user_id, username, referred_by))
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

def is_admin(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def add_admin(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = ?', (user_id,))
    if cursor.rowcount == 0:
        cursor.execute('INSERT INTO users (user_id, is_admin) VALUES (?, 1)', (user_id,))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    if user_id == PRIMARY_ADMIN:
        return False
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_admin = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True

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
    cursor.execute('SELECT * FROM services')
    result = cursor.fetchall()
    conn.close()
    return result

def add_service(name, smm_id, price_per_1000):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO services (name, smm_id, price_per_1000) VALUES (?, ?, ?)', 
                   (name, smm_id, price_per_1000))
    conn.commit()
    conn.close()

def remove_service(service_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM services WHERE id = ?', (service_id,))
    conn.commit()
    conn.close()

def get_required_channels():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM required_channels')
    result = cursor.fetchall()
    conn.close()
    return result

def add_required_channel(channel_link, channel_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO required_channels (channel_link, channel_id) VALUES (?, ?)', 
                   (channel_link, channel_id))
    conn.commit()
    conn.close()

def remove_required_channel(channel_link):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM required_channels WHERE channel_link = ?', (channel_link,))
    conn.commit()
    conn.close()

def create_payment_request(user_id, amount, utr_number):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO payment_requests (user_id, amount, utr_number) VALUES (?, ?, ?)',
                   (user_id, amount, utr_number))
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return request_id

def get_payment_request(request_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM payment_requests WHERE id = ?', (request_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def update_payment_request_status(request_id, status):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE payment_requests SET status = ? WHERE id = ?', (status, request_id))
    conn.commit()
    conn.close()

# SMM API functions
async def place_smm_order(service_id, link, quantity):
    async with aiohttp.ClientSession() as session:
        data = {
            'key': SMM_API_KEY,
            'action': 'add',
            'service': service_id,
            'link': link,
            'quantity': quantity
        }
        try:
            async with session.post(SMM_API_URL, data=data) as response:
                result = await response.json()
                return result
        except Exception as e:
            return {'error': str(e)}

async def check_smm_order_status(order_id):
    async with aiohttp.ClientSession() as session:
        data = {
            'key': SMM_API_KEY,
            'action': 'status',
            'order': order_id
        }
        try:
            async with session.post(SMM_API_URL, data=data) as response:
                result = await response.json()
                return result
        except Exception as e:
            return {'error': str(e)}

# Keyboard layouts
def main_menu_keyboard(user_id):
    keyboard = [
        [KeyboardButton("💰 Balance"), KeyboardButton("👥 Refer")],
        [KeyboardButton("❓ Help"), KeyboardButton("💳 Add Funds")],
        [KeyboardButton("🛒 Buy Services"), KeyboardButton("📋 Order Status")]
    ]
    
    if is_admin(user_id):
        keyboard.append([KeyboardButton("⚙️ Admin Panel")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_panel_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 Check Balance", callback_data="admin_check_balance"),
         InlineKeyboardButton("✏️ Edit Balance", callback_data="admin_edit_balance")],
        [InlineKeyboardButton("❓ Edit Help", callback_data="admin_edit_help"),
         InlineKeyboardButton("💳 Edit UPI ID", callback_data="admin_edit_upi")],
        [InlineKeyboardButton("🎁 Edit Per Refer", callback_data="admin_edit_refer"),
         InlineKeyboardButton("🔢 Set Refer Limit", callback_data="admin_refer_limit")],
        [InlineKeyboardButton("👤 Edit Admins", callback_data="admin_edit_admins"),
         InlineKeyboardButton("📢 Edit Channels", callback_data="admin_edit_channels")],
        [InlineKeyboardButton("📡 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("🎁 Toggle Refer", callback_data="admin_toggle_refer")],
        [InlineKeyboardButton("🔧 Maintenance", callback_data="admin_maintenance"),
         InlineKeyboardButton("🛒 Edit Services", callback_data="admin_edit_services")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def edit_balance_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add", callback_data="balance_add"),
         InlineKeyboardButton("➖ Deduct", callback_data="balance_deduct"),
         InlineKeyboardButton("🔄 Set", callback_data="balance_set")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def edit_admins_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Admin", callback_data="add_admin"),
         InlineKeyboardButton("➖ Remove Admin", callback_data="remove_admin")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def edit_channels_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"),
         InlineKeyboardButton("➖ Remove Channel", callback_data="remove_channel")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def edit_services_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Service", callback_data="add_service"),
         InlineKeyboardButton("➖ Remove Service", callback_data="remove_service")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def services_list_keyboard():
    services = get_services()
    keyboard = []
    for service in services:
        keyboard.append([InlineKeyboardButton(f"🛒 {service[1]}", callback_data=f"buy_service_{service[0]}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def remove_services_keyboard():
    services = get_services()
    keyboard = []
    for service in services:
        keyboard.append([InlineKeyboardButton(f"🗑️ {service[1]}", callback_data=f"delete_service_{service[0]}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_edit_services")])
    return InlineKeyboardMarkup(keyboard)

# Check if user joined required channels
async def check_user_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    channels = get_required_channels()
    for channel in channels:
        try:
            member = await context.bot.get_chat_member(channel[2], user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            continue
    return True

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Check for referral
    referred_by = None
    if context.args and context.args[0].startswith('ref_'):
        try:
            referred_by = int(context.args[0][4:])
        except:
            pass
    
    # Create user if doesn't exist
    if not get_user(user_id):
        create_user(user_id, username, referred_by)
        
        # Process referral reward
        if referred_by and get_user(referred_by):
            refer_reward = int(get_setting('refer_reward'))
            refer_enabled = get_setting('refer_enabled') == 'True'
            
            if refer_enabled:
                # Check refer limit
                refer_limit = int(get_setting('refer_limit'))
                referrer = get_user(referred_by)
                if refer_limit == -1 or referrer[3] < refer_limit:  # referrals count
                    update_user_balance(referred_by, refer_reward)
                    # Update referrals count
                    conn = sqlite3.connect('bot_database.db')
                    cursor = conn.cursor()
                    cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = ?', (referred_by,))
                    conn.commit()
                    conn.close()
                    
                    # Notify referrer
                    try:
                        await context.bot.send_message(
                            referred_by,
                            f"🎉 {refer_reward} Rs added to your balance by referring user {user_id}!"
                        )
                    except:
                        pass
    
    # Check required channels
    channels = get_required_channels()
    if channels and not await check_user_membership(context, user_id):
        keyboard = []
        for channel in channels:
            keyboard.append([InlineKeyboardButton(f"📢 Join Channel", url=channel[1])])
        keyboard.append([InlineKeyboardButton("✅ I Joined", callback_data="check_membership")])
        
        await update.message.reply_text(
            "🔒 To use this bot, you need to join the required channels first:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Show main menu
    await update.message.reply_text(
        "🎉 Welcome to Instagram Services Bot!\n\n"
        "Choose an option from the menu below:",
        reply_markup=main_menu_keyboard(user_id)
    )

async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if await check_user_membership(context, user_id):
        await query.edit_message_text(
            "✅ Welcome! You can now use the bot.",
            reply_markup=None
        )
        await context.bot.send_message(
            user_id,
            "🎉 Welcome to Instagram Services Bot!\n\n"
            "Choose an option from the menu below:",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await query.edit_message_text(
            "❌ Please join all required channels first and then click 'I Joined' again."
        )

# Message handlers
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Check maintenance mode
    if get_setting('maintenance_mode') == 'True' and not is_admin(user_id):
        await update.message.reply_text("🔧 Bot is under maintenance. Please wait until maintenance is over.")
        return
    
    # Check if user exists
    if not get_user(user_id):
        await start(update, context)
        return
    
    # Handle different menu options
    if text == "💰 Balance":
        user = get_user(user_id)
        balance = user[2] if user else 0
        await update.message.reply_text(f"💰 Your current balance: ₹{balance:.2f}")
    
    elif text == "👥 Refer":
        if get_setting('refer_enabled') != 'True':
            await update.message.reply_text("❌ Referral program is currently not available.")
            return
            
        user = get_user(user_id)
        referrals = user[3] if user else 0
        refer_reward = get_setting('refer_reward')
        refer_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
        
        await update.message.reply_text(
            f"👥 **Referral Program**\n\n"
            f"💰 Earn ₹{refer_reward} for each referral!\n"
            f"📊 Your referrals: {referrals}\n\n"
            f"🔗 Your referral link:\n`{refer_link}`\n\n"
            f"Share this link with your friends!",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif text == "❓ Help":
        help_contact = get_setting('help_contact')
        await update.message.reply_text(f"❓ Need help! Contact {help_contact}")
    
    elif text == "💳 Add Funds":
        upi_id = get_setting('upi_id')
        keyboard = [[InlineKeyboardButton("✅ PAID", callback_data="payment_paid")]]
        await update.message.reply_text(
            f"💳 **Add Funds**\n\n"
            f"Pay to: `{upi_id}`\n\n"
            f"After payment, click the button below:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif text == "🛒 Buy Services":
        keyboard = services_list_keyboard()
        if not keyboard.inline_keyboard[:-1]:  # No services except back button
            await update.message.reply_text("❌ No services available at the moment.")
        else:
            await update.message.reply_text(
                "🛒 **Available Services**\n\nChoose a service:",
                reply_markup=keyboard
            )
    
    elif text == "📋 Order Status":
        context.user_data['waiting_for'] = 'order_id_check'
        await update.message.reply_text("📋 Please enter your order ID:")
    
    elif text == "⚙️ Admin Panel" and is_admin(user_id):
        await update.message.reply_text(
            "⚙️ **Admin Panel**\n\nChoose an option:",
            reply_markup=admin_panel_keyboard()
        )
    
    # Handle user input based on context
    elif 'waiting_for' in context.user_data:
        await handle_user_input(update, context)

async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    waiting_for = context.user_data.get('waiting_for')
    
    # Handle service purchase flow first
    if waiting_for == 'instagram_link':
        # Validate Instagram link
        if 'instagram.com' not in text:
            await update.message.reply_text("❌ Please enter a valid Instagram link.")
            return
        
        context.user_data['instagram_link'] = text
        context.user_data['waiting_for'] = 'quantity'
        await update.message.reply_text("🔢 Please enter the quantity:")
        return
    
    elif waiting_for == 'quantity':
        try:
            quantity = int(text)
            if quantity <= 0:
                await update.message.reply_text("❌ Please enter a valid quantity.")
                return
            
            service = context.user_data['selected_service']
            instagram_link = context.user_data['instagram_link']
            
            # Calculate cost
            cost = (quantity / 1000) * service[3]  # price_per_1000
            
            # Check user balance
            user = get_user(user_id)
            if user[2] < cost:  # balance
                await update.message.reply_text(f"❌ Insufficient balance. Required: ₹{cost:.2f}, Available: ₹{user[2]:.2f}")
                return
            
            # Deduct balance
            update_user_balance(user_id, -cost)
            
            # Place order on SMM panel
            result = await place_smm_order(service[2], instagram_link, quantity)  # smm_id
            
            if 'order' in result:
                order_id = result['order']
                # Store order in database
                conn = sqlite3.connect('bot_database.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO orders (order_id, user_id, service_name, instagram_link, quantity, amount)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (order_id, user_id, service[1], instagram_link, quantity, cost))
                conn.commit()
                conn.close()
                
                await update.message.reply_text(
                    f"✅ **Order Placed Successfully!**\n\n"
                    f"🆔 Order ID: `{order_id}`\n"
                    f"🛒 Service: {service[1]}\n"
                    f"🔗 Link: {instagram_link}\n"
                    f"🔢 Quantity: {quantity}\n"
                    f"💰 Cost: ₹{cost:.2f}\n\n"
                    f"💰 Remaining Balance: ₹{user[2] - cost:.2f}",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # Refund balance if order failed
                update_user_balance(user_id, cost)
                await update.message.reply_text("❌ Failed to place order. Your balance has been refunded.")
            
            # Clear context
            del context.user_data['selected_service']
            del context.user_data['instagram_link']
            del context.user_data['waiting_for']
            return
            
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid quantity.")
            return
    
    elif waiting_for == 'order_id_check':
        # Check order status
        try:
            result = await check_smm_order_status(text)
            if 'error' in result:
                await update.message.reply_text("❌ Error checking order status. Please try again.")
            else:
                status = result.get('status', 'Unknown')
                if status.lower() in ['completed', 'complete']:
                    await update.message.reply_text(f"✅ Order {text} is completed!")
                else:
                    await update.message.reply_text(f"⏳ Order {text} is pending.")
        except:
            await update.message.reply_text("❌ Invalid order ID or error checking status.")
        
        del context.user_data['waiting_for']
    
    elif waiting_for == 'payment_amount':
        try:
            amount = float(text)
            context.user_data['payment_amount'] = amount
            context.user_data['waiting_for'] = 'payment_utr'
            await update.message.reply_text("💳 Please enter the UTR number:")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount.")
    
    elif waiting_for == 'payment_utr':
        utr = text
        amount = context.user_data.get('payment_amount')
        
        # Create payment request
        request_id = create_payment_request(user_id, amount, utr)
        
        # Notify user
        await update.message.reply_text("✅ Payment request sent! Please wait for admin approval.")
        
        # Notify all admins
        admins = []
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE is_admin = 1')
        admins = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        keyboard = [
            [InlineKeyboardButton("✅ Accept", callback_data=f"accept_payment_{request_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_payment_{request_id}")]
        ]
        
        for admin_id in admins:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"💳 **New Payment Request**\n\n"
                    f"👤 User ID: {user_id}\n"
                    f"💰 Amount: ₹{amount}\n"
                    f"🔢 UTR: {utr}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                continue
        
        # Clear context
        del context.user_data['waiting_for']
        del context.user_data['payment_amount']
    
    # Handle admin inputs
    elif waiting_for.startswith('admin_'):
        await handle_admin_input(update, context, waiting_for, text)

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE, waiting_for: str, text: str):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have admin permissions.")
        return
    
    if waiting_for == 'admin_check_balance_user':
        try:
            target_user_id = int(text)
            user = get_user(target_user_id)
            if user:
                balance = user[2]
                await update.message.reply_text(f"💰 User {target_user_id} balance: ₹{balance:.2f}")
            else:
                await update.message.reply_text("❌ User not found.")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid user ID.")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_edit_balance_user':
        try:
            target_user_id = int(text)
            if get_user(target_user_id):
                context.user_data['target_user_id'] = target_user_id
                await update.message.reply_text(
                    f"✏️ **Edit Balance for User {target_user_id}**",
                    reply_markup=edit_balance_keyboard()
                )
            else:
                await update.message.reply_text("❌ User not found.")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid user ID.")
        del context.user_data['waiting_for']
    
    elif waiting_for in ['balance_add_amount', 'balance_deduct_amount', 'balance_set_amount']:
        try:
            amount = float(text)
            target_user_id = context.user_data.get('target_user_id')
            
            if waiting_for == 'balance_add_amount':
                update_user_balance(target_user_id, amount)
                await update.message.reply_text(f"✅ Added ₹{amount} to user {target_user_id}")
            elif waiting_for == 'balance_deduct_amount':
                update_user_balance(target_user_id, -amount)
                await update.message.reply_text(f"✅ Deducted ₹{amount} from user {target_user_id}")
            elif waiting_for == 'balance_set_amount':
                set_user_balance(target_user_id, amount)
                await update.message.reply_text(f"✅ Set balance of user {target_user_id} to ₹{amount}")
            
            del context.user_data['target_user_id']
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount.")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_edit_help':
        if text.startswith('@'):
            set_setting('help_contact', text)
            await update.message.reply_text(f"✅ Help contact updated to {text}")
        else:
            await update.message.reply_text("❌ Please enter a valid username starting with @")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_edit_upi':
        set_setting('upi_id', text)
        await update.message.reply_text(f"✅ UPI ID updated to {text}")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_edit_refer_reward':
        try:
            amount = float(text)
            set_setting('refer_reward', amount)
            await update.message.reply_text(f"✅ Per refer reward updated to ₹{amount}")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount.")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_refer_limit':
        try:
            limit = int(text)
            set_setting('refer_limit', limit)
            if limit == -1:
                await update.message.reply_text("✅ Refer limit set to unlimited")
            else:
                await update.message.reply_text(f"✅ Refer limit set to {limit}")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number.")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_add_admin':
        try:
            admin_user_id = int(text)
            add_admin(admin_user_id)
            await update.message.reply_text(f"✅ User {admin_user_id} is now an admin")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid user ID.")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_remove_admin':
        try:
            admin_user_id = int(text)
            if remove_admin(admin_user_id):
                await update.message.reply_text(f"✅ User {admin_user_id} is no longer an admin")
            else:
                await update.message.reply_text("❌ Cannot remove primary admin")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid user ID.")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_add_channel':
        # Extract channel ID from link
        channel_id = text
        if 't.me/' in text:
            channel_id = '@' + text.split('/')[-1]
        add_required_channel(text, channel_id)
        await update.message.reply_text(f"✅ Channel {text} added to required channels")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_remove_channel':
        remove_required_channel(text)
        await update.message.reply_text(f"✅ Channel {text} removed from required channels")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_broadcast':
        users = get_all_users()
        success_count = 0
        for user_id in users:
            try:
                await context.bot.send_message(user_id, f"📢 **Broadcast Message**\n\n{text}", parse_mode=ParseMode.MARKDOWN)
                success_count += 1
            except:
                continue
        await update.message.reply_text(f"✅ Broadcast sent to {success_count} users")
        del context.user_data['waiting_for']
    
    elif waiting_for == 'admin_add_service_name':
        context.user_data['service_name'] = text
        context.user_data['waiting_for'] = 'admin_add_service_smm_id'
        await update.message.reply_text("🔢 Enter SMM ID for this service:")
    
    elif waiting_for == 'admin_add_service_smm_id':
        try:
            smm_id = int(text)
            context.user_data['service_smm_id'] = smm_id
            context.user_data['waiting_for'] = 'admin_add_service_price'
            await update.message.reply_text("💰 Enter price per 1000:")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid SMM ID.")
    
    elif waiting_for == 'admin_add_service_price':
        try:
            price = float(text)
            service_name = context.user_data['service_name']
            smm_id = context.user_data['service_smm_id']
            
            add_service(service_name, smm_id, price)
            await update.message.reply_text(f"✅ Service '{service_name}' added successfully!")
            
            # Clear context
            del context.user_data['service_name']
            del context.user_data['service_smm_id']
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid price.")
        del context.user_data['waiting_for']

# Callback query handlers
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Check maintenance mode for non-admins
    if get_setting('maintenance_mode') == 'True' and not is_admin(user_id) and not data.startswith('accept_') and not data.startswith('reject_'):
        await query.edit_message_text("🔧 Bot is under maintenance. Please wait until maintenance is over.")
        return
    
    # Handle different callback data
    if data == "check_membership":
        await check_membership_callback(update, context)
    
    elif data == "payment_paid":
        context.user_data['waiting_for'] = 'payment_amount'
        await query.edit_message_text("💰 Please enter the amount you paid:")
    
    elif data.startswith('accept_payment_'):
        request_id = int(data.split('_')[2])
        payment_request = get_payment_request(request_id)
        
        if payment_request and payment_request[4] == 'pending':  # status
            # Update payment status
            update_payment_request_status(request_id, 'approved')
            
            # Add balance to user
            user_id_to_credit = payment_request[1]
            amount = payment_request[2]
            update_user_balance(user_id_to_credit, amount)
            
            # Notify user
            try:
                await context.bot.send_message(
                    user_id_to_credit,
                    f"✅ Your payment of ₹{amount} has been approved!"
                )
            except:
                pass
            
            await query.edit_message_text(f"✅ Payment of ₹{amount} approved for user {user_id_to_credit}")
        else:
            await query.edit_message_text("❌ Payment request not found or already processed.")
    
    elif data.startswith('reject_payment_'):
        request_id = int(data.split('_')[2])
        payment_request = get_payment_request(request_id)
        
        if payment_request and payment_request[4] == 'pending':
            # Update payment status
            update_payment_request_status(request_id, 'rejected')
            
            # Notify user
            user_id_to_notify = payment_request[1]
            amount = payment_request[2]
            help_contact = get_setting('help_contact')
            
            try:
                await context.bot.send_message(
                    user_id_to_notify,
                    f"❌ Your payment of ₹{amount} was rejected. Any issue contact {help_contact}"
                )
            except:
                pass
            
            await query.edit_message_text(f"❌ Payment of ₹{amount} rejected for user {user_id_to_notify}")
        else:
            await query.edit_message_text("❌ Payment request not found or already processed.")
    
    elif data.startswith('buy_service_'):
        service_id = int(data.split('_')[2])
        services = get_services()
        service = next((s for s in services if s[0] == service_id), None)
        
        if service:
            context.user_data['selected_service'] = service
            context.user_data['waiting_for'] = 'instagram_link'
            await query.edit_message_text(f"🔗 Please enter the Instagram link for {service[1]}:")
        else:
            await query.edit_message_text("❌ Service not found.")
    
    # Admin panel callbacks
    elif data == "admin_panel":
        await query.edit_message_text(
            "⚙️ **Admin Panel**\n\nChoose an option:",
            reply_markup=admin_panel_keyboard()
        )
    
    elif data == "admin_check_balance":
        context.user_data['waiting_for'] = 'admin_check_balance_user'
        await query.edit_message_text("👤 Enter user ID to check balance:")
    
    elif data == "admin_edit_balance":
        context.user_data['waiting_for'] = 'admin_edit_balance_user'
        await query.edit_message_text("👤 Enter user ID to edit balance:")
    
    elif data == "admin_edit_help":
        context.user_data['waiting_for'] = 'admin_edit_help'
        await query.edit_message_text("❓ Enter new help contact (with @):")
    
    elif data == "admin_edit_upi":
        context.user_data['waiting_for'] = 'admin_edit_upi'
        await query.edit_message_text("💳 Enter new UPI ID:")
    
    elif data == "admin_edit_refer":
        context.user_data['waiting_for'] = 'admin_edit_refer_reward'
        await query.edit_message_text("🎁 Enter new per refer reward amount:")
    
    elif data == "admin_refer_limit":
        context.user_data['waiting_for'] = 'admin_refer_limit'
        await query.edit_message_text("🔢 Enter refer limit (-1 for unlimited):")
    
    elif data == "admin_edit_admins":
        await query.edit_message_text(
            "👤 **Edit Admins**\n\nChoose an option:",
            reply_markup=edit_admins_keyboard()
        )
    
    elif data == "add_admin":
        context.user_data['waiting_for'] = 'admin_add_admin'
        await query.edit_message_text("👤 Enter user ID to make admin:")
    
    elif data == "remove_admin":
        context.user_data['waiting_for'] = 'admin_remove_admin'
        await query.edit_message_text("👤 Enter user ID to remove from admin:")
    
    elif data == "admin_edit_channels":
        await query.edit_message_text(
            "📢 **Edit Required Channels**\n\nChoose an option:",
            reply_markup=edit_channels_keyboard()
        )
    
    elif data == "add_channel":
        context.user_data['waiting_for'] = 'admin_add_channel'
        await query.edit_message_text("📢 Enter channel/group link:")
    
    elif data == "remove_channel":
        context.user_data['waiting_for'] = 'admin_remove_channel'
        await query.edit_message_text("📢 Enter channel/group link to remove:")
    
    elif data == "admin_broadcast":
        context.user_data['waiting_for'] = 'admin_broadcast'
        await query.edit_message_text("📡 Enter message to broadcast:")
    
    elif data == "admin_toggle_refer":
        current_status = get_setting('refer_enabled') == 'True'
        new_status = not current_status
        set_setting('refer_enabled', str(new_status))
        status_text = "enabled" if new_status else "disabled"
        await query.edit_message_text(f"🎁 Referral system {status_text}")
    
    elif data == "admin_maintenance":
        current_status = get_setting('maintenance_mode') == 'True'
        new_status = not current_status
        set_setting('maintenance_mode', str(new_status))
        status_text = "enabled" if new_status else "disabled"
        await query.edit_message_text(f"🔧 Maintenance mode {status_text}")
    
    elif data == "admin_edit_services":
        await query.edit_message_text(
            "🛒 **Edit Services**\n\nChoose an option:",
            reply_markup=edit_services_keyboard()
        )
    
    elif data == "add_service":
        context.user_data['waiting_for'] = 'admin_add_service_name'
        await query.edit_message_text("📝 Enter service name:")
    
    elif data == "remove_service":
        await query.edit_message_text(
            "🗑️ **Remove Service**\n\nChoose a service to remove:",
            reply_markup=remove_services_keyboard()
        )
    
    elif data.startswith('delete_service_'):
        service_id = int(data.split('_')[2])
        remove_service(service_id)
        await query.edit_message_text("✅ Service removed successfully!")
    
    # Balance edit callbacks
    elif data == "balance_add":
        context.user_data['waiting_for'] = 'balance_add_amount'
        await query.edit_message_text("➕ Enter amount to add:")
    
    elif data == "balance_deduct":
        context.user_data['waiting_for'] = 'balance_deduct_amount'
        await query.edit_message_text("➖ Enter amount to deduct:")
    
    elif data == "balance_set":
        context.user_data['waiting_for'] = 'balance_set_amount'
        await query.edit_message_text("🔄 Enter amount to set:")
    
    elif data == "back_to_main":
        await query.edit_message_text(
            "🎉 Welcome to Instagram Services Bot!\n\n"
            "Choose an option from the menu below:"
        )

# Main function
def main():
    # Initialize database
    init_database()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    print("🤖 Bot started successfully!")
    application.run_polling()

if __name__ == '__main__':
    main()