#!/usr/bin/env python3
"""
Instagram Services Telegram Bot Launcher
"""

import sys
import subprocess
import importlib.util

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = {
        'telegram': 'python-telegram-bot',
        'aiohttp': 'aiohttp'
    }
    
    missing_packages = []
    
    for package, pip_name in required_packages.items():
        if importlib.util.find_spec(package) is None:
            missing_packages.append(pip_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Installing missing packages...")
        
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✅ All packages installed successfully!")
        except subprocess.CalledProcessError:
            print("❌ Failed to install packages. Please install manually:")
            print(f"   pip install {' '.join(missing_packages)}")
            return False
    
    return True

def main():
    """Main function to start the bot"""
    print("🤖 Instagram Services Telegram Bot")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Import and start the bot
    try:
        print("🚀 Starting bot...")
        from telegram_bot import main as start_bot
        start_bot()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()