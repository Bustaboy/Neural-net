# utils/notifications.py
from typing import Dict, Any
import smtplib
from email.mime.text import MIMEText
from config import ConfigManager

class EnhancedNotificationManager:
    def __init__(self, config: Dict):
        self.config = ConfigManager.get_config("email")
        self.logger = logging.getLogger(__name__)

    def send_email(self, subject: str, body: str, priority: str = "normal"):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.config["from_address"]
        msg['To'] = "admin@tradingbot.com"

        with smtplib.SMTP(self.config["smtp"]["host"], self.config["smtp"]["port"]) as server:
            server.starttls()
            server.login(self.config["smtp"]["user"], self.config["smtp"]["password"])
            server.send_message(msg)

    def send_critical_alert(self, message: str, context: Dict = None):
        self.send_email("Critical Alert", message, priority="high")
