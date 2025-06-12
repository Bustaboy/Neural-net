# api/auth.py
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import timedelta
import bcrypt
import os
import smtplib
from email.mime.text import MIMEText
from pyotp import TOTP
from typing import Dict
from config import ConfigManager
from core.database import EnhancedDatabaseManager

class AuthManager:
    def __init__(self, app, db_manager: EnhancedDatabaseManager = None):
        self.app = app
        self.db_manager = db_manager
        self.setup_jwt()
    
    def setup_jwt(self):
        secret_key = os.environ.get('JWT_SECRET_KEY')
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY environment variable is not set")
        self.app.config['JWT_SECRET_KEY'] = secret_key
        self.app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
        self.app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)  # Adjusted per config.yaml
    
    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_tokens(self, user_id: int, is_admin: bool = False, subscription_tier: str = None) -> Dict:
        identity = {'user_id': user_id, 'is_admin': is_admin, 'subscription_tier': subscription_tier}
        access_token = create_access_token(identity=identity)
        refresh_token = create_refresh_token(identity=identity)
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer'
        }
    
    def enable_2fa(self, user_id: int) -> str:
        secret = TOTP().provisioning_uri(name=f"user_{user_id}", issuer_name="TradingBot")
        self.db_manager.execute(
            "UPDATE users SET two_factor_secret = ? WHERE id = ?",
            (secret, user_id)
        )
        return secret
    
    def verify_2fa(self, user_id: int, code: str) -> bool:
        secret = self.db_manager.fetch_one(
            "SELECT two_factor_secret FROM users WHERE id = ?", (user_id,)
        )[0]
        if not secret:
            return False
        return TOTP(secret).verify(code)
    
    def send_verification_email(self, user_id: int, email: str):
        token = create_access_token(
            identity={'user_id': user_id, 'verify_email': True},
            expires_delta=timedelta(hours=24)
        )
        verification_url = f"https://your-client-app.com/verify?token={token}"
        msg = MIMEText(f"Please verify your email by clicking here: {verification_url}")
        msg['Subject'] = "Email Verification"
        msg['From'] = ConfigManager.get_config("email.from_address")
        msg['To'] = email

        with smtplib.SMTP(
            ConfigManager.get_config("email.smtp.host"),
            ConfigManager.get_config("email.smtp.port")
        ) as server:
            server.starttls()
            server.login(
                ConfigManager.get_config("email.smtp.user"),
                ConfigManager.get_config("email.smtp.password")
            )
            server.send_message(msg)
