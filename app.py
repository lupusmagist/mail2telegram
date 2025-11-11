import logging
import signal
import sys
from config import Config
from database import DatabaseManager
from mail_client import POP3MailClient
from telegram_bot import TelegramBot
from scheduler import MailCheckerScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mail_bot.log'),
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