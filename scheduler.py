from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from datetime import datetime

class MailCheckerScheduler:
    def __init__(self, mail_client, telegram_bot, db_manager, check_interval_minutes=5):
        self.mail_client = mail_client
        self.telegram_bot = telegram_bot
        self.db_manager = db_manager
        self.check_interval_minutes = check_interval_minutes
        self.logger = logging.getLogger(__name__)
        self.scheduler = BackgroundScheduler()
        self.running = False
    
    def check_and_process_emails(self):
        """Check for new emails and process them"""
        self.logger.info("Starting scheduled email check...")
        
        try:
            # Connect to mail server
            if not self.mail_client.connect():
                self.logger.error("Failed to connect to mail server")
                return
            
            # Get new emails
            emails = self.mail_client.get_new_emails()
            self.logger.info(f"Processing {len(emails)} emails")
            
            processed_count = 0
            for email_data in emails:
                try:
                    # Check if email already processed
                    if self.db_manager.is_email_processed(email_data['message_id']):
                        self.logger.info(f"Email already processed: {email_data['subject']}")
                        # Mark for deletion anyway (in case previous deletion failed)
                        self.mail_client.mark_for_deletion(email_data['pop3_message_num'])
                        continue
                    
                    # Save to database
                    has_images = len(email_data['images']) > 0
                    email_id = self.db_manager.save_email(
                        message_id=email_data['message_id'],
                        subject=email_data['subject'],
                        sender=email_data['sender'],
                        recipient=email_data['recipient'],
                        body=email_data['body'],
                        received_date=email_data['received_date'],
                        has_images=has_images,
                        image_count=len(email_data['images'])
                    )
                    
                    # Send to Telegram
                    success, error_message = self.telegram_bot.send_message(
                        subject=email_data['subject'],
                        body=email_data['body'],
                        sender=email_data['sender'],
                        images=email_data['images']
                    )
                    
                    # Update database with Telegram status
                    self.db_manager.mark_telegram_sent(
                        email_id,
                        success,
                        error_message
                    )
                    
                    # Always mark for deletion after processing (whether success or failure)
                    # This prevents the same email from being processed repeatedly
                    self.mail_client.mark_for_deletion(email_data['pop3_message_num'])
                    
                    processed_count += 1
                    self.logger.info(f"Processed email: {email_data['subject']} (Images: {len(email_data['images'])}) - Telegram: {'Success' if success else 'Failed'}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing email: {e}")
                    continue
            
            self.logger.info(f"Email check completed. Processed {processed_count} new emails")
            
        except Exception as e:
            self.logger.error(f"Error during email check: {e}")
        finally:
            # Always disconnect from mail server
            self.mail_client.disconnect()
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.logger.info(f"Starting APScheduler with {self.check_interval_minutes} minute interval")
        
        # Add the job to scheduler
        trigger = IntervalTrigger(minutes=self.check_interval_minutes)
        self.scheduler.add_job(
            self.check_and_process_emails,
            trigger=trigger,
            id='email_checker',
            name='Email Checker Job',
            replace_existing=True
        )
        
        # Start the scheduler
        self.scheduler.start()
        self.running = True
        
        # Run immediately on start
        self.logger.info("Running initial email check...")
        self.check_and_process_emails()
        
        self.logger.info("APScheduler started successfully")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.logger.info("Stopping APScheduler...")
            self.scheduler.shutdown()
            self.running = False
            self.logger.info("APScheduler stopped successfully")