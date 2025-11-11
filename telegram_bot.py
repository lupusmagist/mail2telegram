from telegram import Bot, InputFile
from telegram.error import TelegramError
import logging
import io
import asyncio

class TelegramBot:
    def __init__(self, token, chat_id, max_message_length=4000):
        self.token = token
        self.chat_id = chat_id
        self.max_message_length = max_message_length
        self.logger = logging.getLogger(__name__)
    
    def send_message(self, subject, body, sender, images=None):
        """Send message to Telegram with optional images"""
        return asyncio.run(self._send_message_async(subject, body, sender, images))
    
    async def _send_message_async(self, subject, body, sender, images=None):
        """Async method to send message to Telegram with optional images"""
        async with Bot(self.token) as bot:
            try:
                # Format the message
                message = self._format_message(subject, body, sender)
                
                # Send images if available
                if images and len(images) > 0:
                    return await self._send_message_with_images(bot, message, images)
                else:
                    # Send text-only message
                    await bot.send_message(chat_id=self.chat_id, text=message, parse_mode='HTML')
                    self.logger.info("Text message sent to Telegram successfully")
                    return True, None
            
            except TelegramError as e:
                error_msg = f"Telegram API error: {e}"
                self.logger.error(error_msg)
                return False, error_msg
            except Exception as e:
                error_msg = f"Unexpected error sending to Telegram: {e}"
                self.logger.error(error_msg)
                return False, error_msg
    
    async def _send_message_with_images(self, bot, message, images):
        """Async method to send message with images to Telegram"""
        try:
            # For multiple images, we'll send the first image with caption and the rest without
            # Telegram allows up to 10 photos in a media group, but we'll limit to 5 for safety
            
            max_images = 5
            images_to_send = images[:max_images]
            
            if len(images_to_send) == 1:
                # Single image - send with caption
                image = images_to_send[0]
                photo = InputFile(io.BytesIO(image['data']), filename=image['filename'])
                await bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=message,
                    parse_mode='HTML'
                )
                self.logger.info("Message with image sent to Telegram successfully")
            else:
                # Multiple images - send media group with first image having caption
                media_group = []
                for i, image in enumerate(images_to_send):
                    photo = InputFile(io.BytesIO(image['data']), filename=image['filename'])
                    media_item = {
                        'type': 'photo',
                        'media': photo
                    }
                    if i == 0:
                        # First image gets the caption
                        media_item['caption'] = message
                        media_item['parse_mode'] = 'HTML'
                    
                    media_group.append(media_item)
                
                await bot.send_media_group(chat_id=self.chat_id, media=media_group)
                self.logger.info(f"Message with {len(images_to_send)} images sent to Telegram successfully")
            
            # If there were more images than we sent, log it
            if len(images) > max_images:
                self.logger.warning(f"Only sent {max_images} out of {len(images)} images due to Telegram limits")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error sending images to Telegram: {e}"
            self.logger.error(error_msg)
            # Fallback: try sending text only
            try:
                await bot.send_message(chat_id=self.chat_id, text=message, parse_mode='HTML')
                self.logger.info("Fallback text message sent successfully")
                return True, None
            except Exception as fallback_error:
                return False, f"{error_msg}. Fallback also failed: {fallback_error}"
    
    def _format_message(self, subject, body, sender):
        """Format the message for Telegram"""
        # Escape HTML special characters
        def escape_html(text):
            if not text:
                return ""
            return (text.replace('&', '&amp;')
                      .replace('<', '&lt;')
                      .replace('>', '&gt;')
                      .replace('"', '&quot;'))
        
        subject = escape_html(subject)
        sender = escape_html(sender)
        
        # Truncate body if necessary
        max_body_length = self.max_message_length - 500  # Leave space for headers
        if body and len(body) > max_body_length:
            body = body[:max_body_length] + "\n\n... (message truncated)"
        
        body = escape_html(body) if body else "No content"
        
        message = f"📧 <b>New Email Received</b>\n\n"
        message += f"<b>From:</b> {sender}\n"
        message += f"<b>Subject:</b> {subject}\n"
        
        if body:
            message += f"<b>Content:</b>\n{body}"
        
        return message
    
    def test_connection(self):
        """Test Telegram bot connection"""
        return asyncio.run(self._test_connection_async())
    
    async def _test_connection_async(self):
        """Async method to test Telegram bot connection"""
        try:
            async with Bot(self.token) as bot:
                user = await bot.get_me()
                self.logger.info(f"Telegram bot connected: @{user.username}")
                return True
        except Exception as e:
            self.logger.error(f"Telegram bot connection test failed: {e}")
            return False