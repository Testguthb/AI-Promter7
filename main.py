#!/usr/bin/env python3
"""
Main entry point for the Telegram Text Processor Bot.
This script uses the refactored modular structure.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path


current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from src.core import app


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )


def check_environment():
    """Check if all required environment variables are set."""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease check your .env file or set these variables manually.")
        return False
    
    return True


async def main():
    """Main function to run the bot."""
    print("🤖 Starting Telegram Text Processor Bot...")
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    if not check_environment():
        sys.exit(1)
    
    try:
        await app.start()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
        print("\n👋 Bot stopped gracefully")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Bot crashed with error: {e}")
        sys.exit(1)
    
    finally:
        # Ensure proper cleanup
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass