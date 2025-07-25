# Instagram Services Telegram Bot Configuration

# Bot Token from BotFather
BOT_TOKEN = "8055477611:AAE2E18M_YYqpE-WZI52tmHa3mumbF3dl2U"

# SMM Panel Configuration
SMM_API_URL = "https://dllsmm.com/api/v2"
SMM_API_KEY = "fb02ac19e4054c14da8c3a12cac1edee"

# Primary Admin User ID (cannot be removed)
PRIMARY_ADMIN = 5078131670

# Default Settings (can be changed via admin panel)
DEFAULT_SETTINGS = {
    'help_contact': '@admin',      # Admin contact username
    'upi_id': 'example@upi',       # UPI ID for payments
    'refer_reward': 10,            # Reward amount per referral
    'refer_limit': -1,             # Max referrals per user (-1 = unlimited)
    'maintenance_mode': False,     # Maintenance mode status
    'refer_enabled': True          # Referral system status
}

# Database Configuration
DATABASE_NAME = 'bot_database.db'

# Message Templates
MESSAGES = {
    'welcome': "🎉 Welcome to Instagram Services Bot!\n\nChoose an option from the menu below:",
    'maintenance': "🔧 Bot is under maintenance. Please wait until maintenance is over.",
    'channel_join': "🔒 To use this bot, you need to join the required channels first:",
    'insufficient_balance': "❌ Insufficient balance. Required: ₹{required:.2f}, Available: ₹{available:.2f}",
    'order_success': "✅ **Order Placed Successfully!**\n\n🆔 Order ID: `{order_id}`\n🛒 Service: {service}\n🔗 Link: {link}\n🔢 Quantity: {quantity}\n💰 Cost: ₹{cost:.2f}\n\n💰 Remaining Balance: ₹{balance:.2f}",
    'payment_approved': "✅ Your payment of ₹{amount} has been approved!",
    'payment_rejected': "❌ Your payment of ₹{amount} was rejected. Any issue contact {contact}",
    'refer_notification': "🎉 {amount} Rs added to your balance by referring user {user_id}!"
}

# Button Emojis
EMOJIS = {
    'balance': '💰',
    'refer': '👥',
    'help': '❓',
    'add_funds': '💳',
    'buy_services': '🛒',
    'order_status': '📋',
    'admin_panel': '⚙️',
    'back': '🔙',
    'add': '➕',
    'remove': '➖',
    'edit': '✏️',
    'check': '✅',
    'reject': '❌',
    'broadcast': '📡',
    'maintenance': '🔧',
    'toggle': '🎁'
}