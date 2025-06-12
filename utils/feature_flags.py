# utils/feature_flags.py
from typing import Dict, Any
import json

class FeatureFlags:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache = {}
        
    def set_flag(self, flag_name: str, enabled: bool, 
                rollout_percentage: int = 100, conditions: Dict = None):
        """Set feature flag with rollout control"""
        flag_data = {
            'enabled': enabled,
            'rollout_percentage': rollout_percentage,
            'conditions': conditions or {}
        }
        self.redis.set(f"feature_flag:{flag_name}", json.dumps(flag_data))
        
    def is_enabled(self, flag_name: str, user_context: Dict = None) -> bool:
        """Check if feature is enabled for user"""
        flag_data = self.redis.get(f"feature_flag:{flag_name}")
        if not flag_data:
            return False
            
        flag = json.loads(flag_data)
        
        # Check basic enabled state
        if not flag['enabled']:
            return False
            
        # Check rollout percentage
        if user_context and 'user_id' in user_context:
            user_hash = hash(user_context['user_id']) % 100
            if user_hash >= flag['rollout_percentage']:
                return False
                
        # Check conditions
        if flag['conditions'] and user_context:
            for key, value in flag['conditions'].items():
                if user_context.get(key) != value:
                    return False
                    
        return True
