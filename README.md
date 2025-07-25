# Instagram Services Telegram Bot 🤖

A comprehensive Telegram bot for managing Instagram services with SMM panel integration, user management, admin controls, and payment processing.

## Features ✨

### User Features
- 💰 **Balance Management** - Check and manage account balance
- 👥 **Referral System** - Earn rewards by referring friends
- 🛒 **Service Purchase** - Buy Instagram likes, views, followers, etc.
- 📋 **Order Tracking** - Check order status with order ID
- 💳 **Payment Integration** - Add funds via UPI with admin approval
- ❓ **Help Support** - Contact admin for assistance

### Admin Features
- ⚙️ **Complete Admin Panel** with all management tools
- 💰 **User Balance Management** - Add, deduct, or set user balances
- 🛒 **Service Management** - Add/remove services with SMM panel integration
- 👤 **Admin Management** - Add/remove admin users
- 📢 **Channel Management** - Set required channels for bot access
- 📡 **Broadcast System** - Send messages to all users
- 🎁 **Referral Controls** - Toggle referral system and set limits
- 🔧 **Maintenance Mode** - Enable/disable bot temporarily
- 💳 **Payment Approval** - Approve/reject user payment requests

## Setup Instructions 🚀

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configuration
The bot is pre-configured with the provided credentials:
- **Bot Token**: `8055477611:AAE2E18M_YYqpE-WZI52tmHa3mumbF3dl2U`
- **SMM API URL**: `https://dllsmm.com/api/v2`
- **SMM API Key**: `fb02ac19e4054c14da8c3a12cac1edee`
- **Primary Admin**: `5078131670`

### 3. Run the Bot
```bash
python telegram_bot.py
```

The bot will automatically:
- Initialize the SQLite database (`bot_database.db`)
- Create all necessary tables
- Set up default settings
- Add the primary admin

## Database Structure 🗄️

The bot uses SQLite with the following tables:
- **users** - User information, balance, referrals
- **orders** - Service orders and status
- **services** - Available Instagram services
- **required_channels** - Channels users must join
- **payment_requests** - Payment approval requests
- **settings** - Bot configuration settings

## Usage Guide 📖

### For Users
1. Start the bot with `/start`
2. Join required channels (if any)
3. Use the menu buttons to:
   - Check balance
   - View referral link
   - Add funds
   - Buy services
   - Check order status

### For Admins
1. Access **Admin Panel** from the main menu
2. Use various admin tools:
   - Manage user balances
   - Add/remove services
   - Configure bot settings
   - Approve payments
   - Broadcast messages

## Key Features Details 🔍

### Referral System
- Users get reward for each successful referral
- Configurable reward amount and referral limits
- Can be toggled on/off by admins

### Payment System
- Users pay via UPI and submit payment details
- Admins receive payment requests with approve/reject buttons
- Automatic balance updates upon approval

### Service Integration
- Direct integration with DLLSMM panel API
- Real-time order placement and status checking
- Automatic balance deduction and refunds

### Security
- Primary admin cannot be removed
- Maintenance mode for bot updates
- Required channel verification
- Input validation and error handling

## Admin Commands Overview 🛠️

| Function | Description |
|----------|-------------|
| Check Balance | View any user's balance |
| Edit Balance | Add, deduct, or set user balance |
| Edit Help | Change help contact username |
| Edit UPI ID | Update payment UPI ID |
| Edit Per Refer | Set referral reward amount |
| Set Refer Limit | Set maximum referrals per user |
| Edit Admins | Add/remove admin users |
| Edit Channels | Manage required channels |
| Broadcast | Send message to all users |
| Toggle Refer | Enable/disable referral system |
| Maintenance | Enable/disable maintenance mode |
| Edit Services | Add/remove Instagram services |

## Error Handling 🛡️

The bot includes comprehensive error handling for:
- Invalid user inputs
- API failures
- Database errors
- Network issues
- Permission checks

## Support 💬

For any issues or questions, contact the admin through the bot's help feature or directly.

---

**Note**: This bot is ready to run immediately with all features implemented and tested. The database will be created automatically on first run.