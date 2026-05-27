import json
import logging
import uuid
from typing import Dict, List, Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.client = None
        self.ttl_seconds = 86400  # 24 hours

    async def connect(self):
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            await self.client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Session management will be disabled or fallback to in-memory.")
            self.client = None

    async def get_session(self, session_id: str) -> Optional[Dict]:
        if not self.client:
            return None
        
        try:
            data = await self.client.get(f"session:{session_id}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None

    async def save_session(self, session_id: str, data: Dict):
        if not self.client:
            return
        
        try:
            await self.client.setex(
                f"session:{session_id}",
                self.ttl_seconds,
                json.dumps(data)
            )
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}")

    def generate_session_id(self) -> str:
        return str(uuid.uuid4())
