import poplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import logging
from datetime import datetime
from bs4 import BeautifulSoup
import base64
import quopri

class POP3MailClient:
    def __init__(self, server, port, email, password):
        self.server = server
        self.port = port
        self.email = email
        self.password = password
        self.logger = logging.getLogger(__name__)
        self.connection = None
    
    def connect(self):
        """Connect to POP3 server"""
        try:
            if self.port == 995:
                self.connection = poplib.POP3_SSL(self.server, self.port)
            else:
                self.connection = poplib.POP3(self.server, self.port)
            
            self.connection.user(self.email)
            self.connection.pass_(self.password)
            self.logger.info(f"Connected to POP3 server: {self.server}:{self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Error connecting to POP3 server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from POP3 server"""
        try:
            if self.connection:
                self.connection.quit()
                self.logger.info("Disconnected from POP3 server")
        except Exception as e:
            self.logger.error(f"Error disconnecting from POP3 server: {e}")
    
    def get_new_emails(self):
        """Retrieve new emails from the server"""
        if not self.connection:
            self.logger.error("Not connected to POP3 server")
            return []
        
        try:
            # Get email statistics
            num_messages = len(self.connection.list()[1])
            self.logger.info(f"Found {num_messages} emails on server")
            
            emails = []
            for i in range(1, num_messages + 1):
                try:
                    # Retrieve email
                    response, lines, octets = self.connection.retr(i)
                    email_content = b'\r\n'.join(lines).decode('utf-8', errors='ignore')
                    
                    # Parse email
                    msg = email.message_from_string(email_content)
                    email_data = self._parse_email(msg, i)
                    
                    if email_data:
                        emails.append(email_data)
                    
                except Exception as e:
                    self.logger.error(f"Error processing email {i}: {e}")
                    continue
            
            return emails
        
        except Exception as e:
            self.logger.error(f"Error retrieving emails: {e}")
            return []
    
    def _parse_email(self, msg, message_num):
        """Parse email message and extract relevant data"""
        try:
            # Extract headers
            subject = self._decode_header(msg.get('Subject', 'No Subject'))
            sender = msg.get('From', 'Unknown Sender')
            recipient = msg.get('To', 'Unknown Recipient')
            date_str = msg.get('Date')
            
            # Parse date
            try:
                received_date = parsedate_to_datetime(date_str) if date_str else datetime.utcnow()
            except:
                received_date = datetime.utcnow()
            
            # Extract body and images
            body, images = self._extract_body_and_images(msg)
            
            return {
                'message_id': f"{message_num}_{received_date.timestamp()}",
                'subject': subject,
                'sender': sender,
                'recipient': recipient,
                'body': body,
                'images': images,
                'received_date': received_date,
                'pop3_message_num': message_num
            }
        
        except Exception as e:
            self.logger.error(f"Error parsing email: {e}")
            return None
    
    def _decode_header(self, header):
        """Decode email header"""
        try:
            decoded_parts = decode_header(header)
            decoded_header = ''
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_header += part.decode(encoding)
                    else:
                        decoded_header += part.decode('utf-8', errors='ignore')
                else:
                    decoded_header += part
            return decoded_header
        except:
            return str(header)
    
    def _extract_body_and_images(self, msg):
        """Extract email body and images from message"""
        body = ""
        images = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Handle images (both inline and attachments)
                if content_type.startswith('image/'):
                    image_data = self._extract_image(part)
                    if image_data:
                        images.append(image_data)
                    continue
                
                # Skip non-image attachments
                if "attachment" in content_disposition:
                    continue
                
                # Handle text parts
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                    except:
                        try:
                            body = part.get_payload()
                        except:
                            pass
                
                # Handle HTML parts (prefer HTML over plain text for better formatting)
                elif content_type == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')
                            # Convert HTML to plain text, preserving important content
                            html_body = self._html_to_plain_text(html_content)
                            if html_body:
                                body = html_body
                    except:
                        pass
        
        else:
            # Not multipart - simple email
            content_type = msg.get_content_type()
            if content_type == "text/plain":
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    body = msg.get_payload()
            elif content_type == "text/html":
                try:
                    html_content = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    body = self._html_to_plain_text(html_content)
                except:
                    body = msg.get_payload()
        
        return body.strip(), images
    
    def _html_to_plain_text(self, html_content):
        """Convert HTML to plain text while preserving structure"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            
            # Break into lines and remove leading/trailing space
            lines = (line.strip() for line in text.splitlines())
            
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            
            # Drop blank lines and join with newlines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            self.logger.warning(f"Error converting HTML to text: {e}")
            # Fallback: return raw text without HTML tags using basic replacement
            import re
            text = re.sub(r'<[^>]+>', '', html_content)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            return text.strip()
    
    def _extract_image(self, part):
        """Extract image data from email part"""
        try:
            content_type = part.get_content_type()
            filename = part.get_filename()
            
            if not filename:
                filename = f"image_{datetime.utcnow().timestamp()}.{content_type.split('/')[-1]}"
            
            # Decode the image data
            image_data = part.get_payload(decode=True)
            
            if image_data:
                return {
                    'filename': filename,
                    'content_type': content_type,
                    'data': image_data,
                    'size': len(image_data)
                }
        except Exception as e:
            self.logger.error(f"Error extracting image: {e}")
        
        return None
    
    def mark_for_deletion(self, message_num):
        """Mark email for deletion on server"""
        try:
            if self.connection:
                self.connection.dele(message_num)
                self.logger.info(f"Marked email {message_num} for deletion")
                return True
        except Exception as e:
            self.logger.error(f"Error marking email {message_num} for deletion: {e}")
            return False