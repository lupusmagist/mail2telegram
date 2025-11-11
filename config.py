import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # POP3 Configuration
    POP3_SERVER = os.getenv('POP3_SERVER')
    POP3_PORT = int(os.getenv('POP3_PORT', 110))
    POP3_EMAIL = os.getenv('POP3_USER')
    POP3_PASSWORD = os.getenv('POP3_PASSWORD')
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///mail_bot.db')
    
    # Scheduler Configuration
    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', 5))
    
    # App Configuration
    MAX_EMAIL_LENGTH = 4000  # Telegram message limit

    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present"""
        required_vars = [
            'POP3_USER', 'POP3_PASSWORD', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'
        ]
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")