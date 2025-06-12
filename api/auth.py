# api/auth.py - Enhanced JWT implementation
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import timedelta
import bcrypt

class AuthManager:
    def __init__(self, app):
        self.app = app
        self.setup_jwt()
        
    def setup_jwt(self):
        self.app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
        self.app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
        self.app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
        
    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_tokens(self, user_id: int, is_admin: bool = False):
        identity = {'user_id': user_id, 'is_admin': is_admin}
        access_token = create_access_token(identity=identity)
        refresh_token = create_refresh_token(identity=identity)
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer'
        }
