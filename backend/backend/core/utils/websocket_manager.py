# WebSocket handler utility

from typing import Dict, Any
from aiohttp import web

class WebSocketManager:
    """WebSocket connection manager"""

    def __init__(self):
        self.connections: Dict[str, web.WebSocketResponse] = {}

    async def send_message(self, connection_id: str, message: Dict[str, Any]) -> None:
        """Send message to WebSocket client"""
        if connection_id in self.connections:
            await self.connections[connection_id].send_json(message)

    async def close_connection(self, connection_id: str) -> None:
        """Close WebSocket connection"""
        if connection_id in self.connections:
            await self.connections[connection_id].close()
            del self.connections[connection_id]