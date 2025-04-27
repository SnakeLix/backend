import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # user_id -> List[WebSocket connections]
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.lock = asyncio.Lock()
        
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self.lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        async with self.lock:
            if user_id in self.active_connections and websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
                if len(self.active_connections[user_id]) == 0:
                    del self.active_connections[user_id]
    
    async def send_document_update(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(json.dumps(message))
    
    async def broadcast(self, message: dict):
        for user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(json.dumps(message))

# Create a global connection manager instance
manager = ConnectionManager() 