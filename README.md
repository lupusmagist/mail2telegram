# A email to Telegram forwarder.

Fetches emails fro a POP3 account, and sends them to a Telegram bot.

Create a .env file with:
```bash
# POP3 Configuration
POP3_SERVER=your_mail_server
POP3_PORT=110
POP3_USER=your_mail_user
POP3_PASSWORD=your_mail_password

# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chatID

# Database Configuration
DATABASE_URL=sqlite:///mail_bot.db

# Scheduler Configuration
CHECK_INTERVAL_MINUTES=5
```

Install with:
```bash
git clone https://github.com/lupusmagist/mail2telegram.git
cd mail2telegram
python -m venv .venv
source .venv/bin/activate
pip install -r requirments.txt
```

Run with:
```bash
cd mail2telegram

# Make sure your enviroment is active
source .venv/bin/activate

# Run app
python app.py
```