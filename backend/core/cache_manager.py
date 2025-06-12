# backend/core/cache_manager.py
import redis.asyncio as redis
import json
import pickle
from typing import Optional, Any, Union
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Redis cache manager for performance optimization"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = await self.redis_client.get(key)
            if value:
                # Try to deserialize as JSON first
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # If not JSON, try pickle
                    try:
                        return pickle.loads(value.encode('latin1'))
                    except:
                        # Return as string
                        return value
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional expiration (in seconds)"""
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            elif isinstance(value, (str, int, float)):
                serialized = str(value)
            else:
                serialized = pickle.dumps(value).decode('latin1')
            
            if expire:
                await self.redis_client.setex(key, expire, serialized)
            else:
                await self.redis_client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key"""
        try:
            return await self.redis_client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False
    
    async def get_many(self, keys: list) -> dict:
        """Get multiple values at once"""
        try:
            values = await self.redis_client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except:
                        result[key] = value
            return result
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(self, mapping: dict, expire: Optional[int] = None) -> bool:
        """Set multiple values at once"""
        try:
            # Serialize values
            serialized = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    serialized[key] = json.dumps(value)
                else:
                    serialized[key] = str(value)
            
            await self.redis_client.mset(serialized)
            
            # Set expiration if needed
            if expire:
                for key in serialized.keys():
                    await self.redis_client.expire(key, expire)
            
            return True
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return 0
    
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement a counter"""
        try:
            return await self.redis_client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Cache decrement error for key {key}: {e}")
            return 0
    
    async def add_to_set(self, key: str, *values) -> int:
        """Add values to a set"""
        try:
            return await self.redis_client.sadd(key, *values)
        except Exception as e:
            logger.error(f"Cache add_to_set error for key {key}: {e}")
            return 0
    
    async def remove_from_set(self, key: str, *values) -> int:
        """Remove values from a set"""
        try:
            return await self.redis_client.srem(key, *values)
        except Exception as e:
            logger.error(f"Cache remove_from_set error for key {key}: {e}")
            return 0
    
    async def get_set(self, key: str) -> set:
        """Get all values from a set"""
        try:
            return await self.redis_client.smembers(key)
        except Exception as e:
            logger.error(f"Cache get_set error for key {key}: {e}")
            return set()
    
    async def is_healthy(self) -> bool:
        """Check if cache is healthy"""
        try:
            await self.redis_client.ping()
            return True
        except:
            return False
    
    # User-specific cache methods
    async def cache_user_data(
        self,
        user_id: str,
        data_type: str,
        data: Any,
        expire: int = 300
    ) -> bool:
        """Cache user-specific data"""
        key = f"user:{user_id}:{data_type}"
        return await self.set(key, data, expire)
    
    async def get_user_data(self, user_id: str, data_type: str) -> Optional[Any]:
        """Get user-specific cached data"""
        key = f"user:{user_id}:{data_type}"
        return await self.get(key)
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache for a user"""
        pattern = f"user:{user_id}:*"
        keys = await self.redis_client.keys(pattern)
        if keys:
            await self.redis_client.delete(*keys)


# backend/core/notification_service.py
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import UUID
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

from ..database.connection import DatabaseManager
from ..database.models.user import User, Notification
from .cache_manager import CacheManager

logger = logging.getLogger(__name__)

class NotificationService:
    """Multi-channel notification service"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.cache_manager = CacheManager()
        self.websocket_clients: Dict[str, Any] = {}
        self.email_config = {
            'host': 'smtp.gmail.com',
            'port': 587,
            'username': None,
            'password': None,
            'use_tls': True
        }
        
    async def send_notification(
        self,
        user_id: UUID,
        notification_type: str,
        data: Dict[str, Any],
        channels: Optional[List[str]] = None,
        priority: str = "normal"
    ):
        """Send notification through multiple channels"""
        try:
            # Default channels
            if channels is None:
                channels = ["in_app", "websocket"]
            
            # Get user preferences
            user_prefs = await self._get_user_notification_prefs(user_id)
            
            # Create notification record
            notification = await self._create_notification(
                user_id=user_id,
                notification_type=notification_type,
                data=data,
                channels=channels,
                priority=priority
            )
            
            # Send through each channel
            tasks = []
            if "in_app" in channels:
                tasks.append(self._send_in_app(notification))
            
            if "websocket" in channels:
                tasks.append(self._send_websocket(user_id, notification))
            
            if "email" in channels and user_prefs.get("email_enabled"):
                tasks.append(self._send_email(user_id, notification))
            
            if "sms" in channels and user_prefs.get("sms_enabled"):
                tasks.append(self._send_sms(user_id, notification))
            
            if "push" in channels and user_prefs.get("push_enabled"):
                tasks.append(self._send_push(user_id, notification))
            
            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any errors
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Notification error: {result}")
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    async def _create_notification(
        self,
        user_id: UUID,
        notification_type: str,
        data: Dict[str, Any],
        channels: List[str],
        priority: str
    ) -> Notification:
        """Create notification in database"""
        with self.db_manager.get_db() as db:
            # Generate title and message based on type
            title, message = self._generate_notification_content(
                notification_type,
                data
            )
            
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message,
                data=data,
                channels=channels,
                priority=priority,
                created_at=datetime.utcnow()
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            return notification
    
    def _generate_notification_content(
        self,
        notification_type: str,
        data: Dict[str, Any]
    ) -> tuple:
        """Generate notification title and message"""
        templates = {
            "bot_started": (
                "Trading Bot Started",
                f"Your {data.get('bot_name', 'trading bot')} has been started successfully."
            ),
            "bot_stopped": (
                "Trading Bot Stopped",
                f"Your trading bot has been stopped."
            ),
            "bot_error": (
                "Trading Bot Error",
                f"An error occurred: {data.get('error', 'Unknown error')}"
            ),
            "trade_executed": (
                "Trade Executed",
                f"{data.get('side', 'Order')} {data.get('quantity', '')} {data.get('symbol', '')} at {data.get('price', '')}"
            ),
            "position_closed": (
                "Position Closed",
                f"Closed {data.get('symbol', '')} position with P&L: {data.get('pnl', '0')}"
            ),
            "risk_alert": (
                "Risk Alert",
                f"Risk limit reached: {data.get('message', '')}"
            ),
            "market_alert": (
                "Market Alert",
                f"{data.get('symbol', '')}: {data.get('message', '')}"
            ),
        }
        
        return templates.get(
            notification_type,
            ("Notification", json.dumps(data))
        )
    
    async def _send_in_app(self, notification: Notification):
        """Store notification for in-app display"""
        # Already stored in database
        # Cache for quick access
        await self.cache_manager.add_to_set(
            f"notifications:{notification.user_id}",
            str(notification.id)
        )
        await self.cache_manager.expire(
            f"notifications:{notification.user_id}",
            86400  # 24 hours
        )
    
    async def _send_websocket(self, user_id: UUID, notification: Notification):
        """Send notification through WebSocket"""
        # This will be handled by WebSocket manager
        websocket_data = {
            "type": "notification",
            "data": {
                "id": str(notification.id),
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority,
                "timestamp": notification.created_at.isoformat()
            }
        }
        
        # Cache for WebSocket manager to pick up
        await self.cache_manager.set(
            f"ws_notification:{user_id}:{notification.id}",
            websocket_data,
            60  # 1 minute TTL
        )
    
    async def _send_email(self, user_id: UUID, notification: Notification):
        """Send email notification"""
        try:
            # Get user email
            with self.db_manager.get_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not user.email:
                    return
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.email_config['username']
            msg['To'] = user.email
            msg['Subject'] = notification.title
            
            # Email body
            body = f"""
            <html>
                <body>
                    <h2>{notification.title}</h2>
                    <p>{notification.message}</p>
                    <hr>
                    <p><small>This is an automated notification from Trading Platform.</small></p>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            async with aiosmtplib.SMTP(
                hostname=self.email_config['host'],
                port=self.email_config['port'],
                use_tls=self.email_config['use_tls']
            ) as smtp:
                await smtp.login(
                    self.email_config['username'],
                    self.email_config['password']
                )
                await smtp.send_message(msg)
            
            # Update notification status
            with self.db_manager.get_db() as db:
                db_notification = db.query(Notification).filter(
                    Notification.id == notification.id
                ).first()
                db_notification.is_sent = True
                db_notification.sent_at = datetime.utcnow()
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    async def _send_sms(self, user_id: UUID, notification: Notification):
        """Send SMS notification (placeholder)"""
        # Implement SMS provider integration (Twilio, etc.)
        logger.info(f"SMS notification for user {user_id}: {notification.message}")
    
    async def _send_push(self, user_id: UUID, notification: Notification):
        """Send push notification (placeholder)"""
        # Implement push notification service (Firebase, etc.)
        logger.info(f"Push notification for user {user_id}: {notification.message}")
    
    async def _get_user_notification_prefs(self, user_id: UUID) -> Dict[str, Any]:
        """Get user notification preferences"""
        # Try cache first
        cached = await self.cache_manager.get_user_data(
            str(user_id),
            "notification_prefs"
        )
        if cached:
            return cached
        
        # Get from database
        with self.db_manager.get_db() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                prefs = {
                    "email_enabled": True,  # Default settings
                    "sms_enabled": False,
                    "push_enabled": True,
                    "quiet_hours_start": None,
                    "quiet_hours_end": None
                }
                
                # Cache for future use
                await self.cache_manager.cache_user_data(
                    str(user_id),
                    "notification_prefs",
                    prefs,
                    3600  # 1 hour
                )
                
                return prefs
        
        return {}
    
    async def get_user_notifications(
        self,
        user_id: UUID,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Notification]:
        """Get user notifications"""
        with self.db_manager.get_db() as db:
            query = db.query(Notification).filter(
                Notification.user_id == user_id
            )
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
            
            return query.order_by(
                Notification.created_at.desc()
            ).limit(limit).all()
    
    async def mark_as_read(self, user_id: UUID, notification_id: UUID):
        """Mark notification as read"""
        with self.db_manager.get_db() as db:
            notification = db.query(Notification).filter(
                Notification.id == notification_id,
                Notification.user_id == user_id
            ).first()
            
            if notification:
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                db.commit()
                
                # Remove from cache
                await self.cache_manager.remove_from_set(
                    f"notifications:{user_id}",
                    str(notification_id)
                )
