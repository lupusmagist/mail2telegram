from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

Base = declarative_base()

class EmailMessage(Base):
    __tablename__ = 'email_messages'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(String(500), unique=True, nullable=False)
    subject = Column(String(1000))
    sender = Column(String(500), nullable=False)
    recipient = Column(String(500), nullable=False)
    body = Column(Text)
    has_images = Column(Boolean, default=False)
    image_count = Column(Integer, default=0)
    received_date = Column(DateTime, nullable=False)
    processed_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    sent_to_telegram = Column(Boolean, default=False)
    telegram_sent_date = Column(DateTime)
    telegram_error = Column(Text)
    
    def __repr__(self):
        return f"<EmailMessage(id={self.id}, subject='{self.subject}', sent_to_telegram={self.sent_to_telegram})>"

class DatabaseManager:
    def __init__(self, database_url):
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(__name__)
        
    def init_database(self):
        """Initialize database tables"""
        try:
            Base.metadata.create_all(self.engine)
            self.logger.info("Database tables created successfully")
        except Exception as e:
            self.logger.error(f"Error creating database tables: {e}")
            raise
    
    def save_email(self, message_id, subject, sender, recipient, body, received_date, has_images=False, image_count=0):
        """Save email to database"""
        session = self.Session()
        try:
            email = EmailMessage(
                message_id=message_id,
                subject=subject,
                sender=sender,
                recipient=recipient,
                body=body,
                received_date=received_date,
                has_images=has_images,
                image_count=image_count
            )
            session.add(email)
            session.commit()
            # Get the ID before closing the session
            email_id = email.id
            self.logger.info(f"Email saved to database: {subject} (Images: {image_count})")
            return email_id
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error saving email to database: {e}")
            raise
        finally:
            session.close()
    
    def mark_telegram_sent(self, email_id, success=True, error_message=None):
        """Mark email as sent to Telegram"""
        session = self.Session()
        try:
            email = session.query(EmailMessage).filter(EmailMessage.id == email_id).first()
            if email:
                email.sent_to_telegram = success
                email.telegram_sent_date = datetime.utcnow() if success else None
                email.telegram_error = error_message
                session.commit()
                self.logger.info(f"Email {email_id} marked as {'sent' if success else 'failed'} to Telegram")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating email status: {e}")
            raise
        finally:
            session.close()
    
    def is_email_processed(self, message_id):
        """Check if email has already been processed"""
        session = self.Session()
        try:
            email = session.query(EmailMessage).filter(EmailMessage.message_id == message_id).first()
            return email is not None
        except Exception as e:
            self.logger.error(f"Error checking email existence: {e}")
            return False
        finally:
            session.close()