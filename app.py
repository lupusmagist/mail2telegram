import logging
import re
import signal
import sys
from logging.handlers import RotatingFileHandler
from config import Config
from database import DatabaseManager
from mail_client import POP3MailClient
from telegram_bot import TelegramBot
from scheduler import MailCheckerScheduler

def log_namer(name):
    """Custom namer for log rotation to use .old+n format"""
    if name.endswith('.log.1'):
        return name.replace('.log.1', '.log.old1')
    match = re.search(r'\.log\.(\d+)$', name)
    if match:
        num = int(match.group(1))
        return name.replace(f'.log.{num}', f'.log.old{num}')
    return name

# Configure logging
log_handler = RotatingFileHandler(
    'mail_bot.log',
    maxBytes=Config.LOG_SIZE,
    backupCount=Config.LOG_ARCHIVE,
    encoding='utf-8'
)
log_handler.namer = log_namer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        log_handler,
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class MailBotApp:
    def __init__(self):
        self.scheduler = None
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        if self.scheduler:
            self.scheduler.stop()
        sys.exit(0)
    
    def run(self):
        """Main application entry point"""
        try:
            # Validate configuration
            Config.validate_config()
            logger.info("Configuration validated successfully")
            
            # Initialize components
            db_manager = DatabaseManager(Config.DATABASE_URL)
            mail_client = POP3MailClient(
                Config.POP3_SERVER,
                Config.POP3_PORT,
                Config.POP3_EMAIL,
                Config.POP3_PASSWORD
            )
            telegram_bot = TelegramBot(
                Config.TELEGRAM_BOT_TOKEN,
                Config.TELEGRAM_CHAT_ID,
                Config.MAX_EMAIL_LENGTH
            )
            
            # Initialize database
            db_manager.init_database()
            
            # Test Telegram connection
            if not telegram_bot.test_connection():
                logger.error("Telegram bot connection test failed")
                return
            
            # Create and start scheduler
            self.scheduler = MailCheckerScheduler(
                mail_client,
                telegram_bot,
                db_manager,
                Config.CHECK_INTERVAL_MINUTES
            )
            
            logger.info("Mail Bot application started successfully")
            self.scheduler.start()
            
            # Keep the main thread alive
            try:
                while True:
                    signal.pause()
            except KeyboardInterrupt:
                self.signal_handler(signal.SIGINT, None)
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            sys.exit(1)

if __name__ == "__main__":
    app = MailBotApp()
    app.run()