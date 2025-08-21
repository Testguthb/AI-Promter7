import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# File processing settings
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
SUPPORTED_FORMATS = ['.txt', '.docx']

# AI settings
GPT_MODEL = "gpt-4.1"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

required_vars = [TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ANTHROPIC_API_KEY]
if not all(required_vars):
    raise ValueError("Missing required environment variables. Check .env file.")