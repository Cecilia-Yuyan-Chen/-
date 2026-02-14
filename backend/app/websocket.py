"""
WebSocket连接管理
"""
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
import json

class ConnectionManager:
    def __init__(self):
        # 游戏房间：{game_id: {player_id: websocket}}
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}
        # 玩家到游戏的映射：{player_id: game_id}
        self.player_games: Dict[int, int] = {}
    
    async def connect(self, websocket: WebSocket, game_id: int, player_id: int):
        await websocket.accept()
        
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}
        
        self.active_connections[game_id][player_id] = websocket
        self.player_games[player_id] = game_id
    
    def disconnect(self, game_id: int, player_id: int):
        if game_id in self.active_connections:
            if player_id in self.active_connections[game_id]:
                del self.active_connections[game_id][player_id]
        
        if player_id in self.player_games:
            del self.player_games[player_id]
    
    async def send_personal_message(self, message: dict, game_id: int, player_id: int):
        if game_id in self.active_connections:
            if player_id in self.active_connections[game_id]:
                try:
                    await self.active_connections[game_id][player_id].send_json(message)
                except:
                    pass
    
    async def broadcast_to_game(self, message: dict, game_id: int, exclude_player: int = None):
        """向游戏内所有玩家广播消息"""
        if game_id in self.active_connections:
            for pid, websocket in self.active_connections[game_id].items():
                if pid != exclude_player:
                    try:
                        await websocket.send_json(message)
                    except:
                        pass
    
    async def broadcast_to_all_in_game(self, message: dict, game_id: int):
        """向游戏内所有玩家广播（包括发送者）"""
        if game_id in self.active_connections:
            for pid, websocket in self.active_connections[game_id].items():
                try:
                    await websocket.send_json(message)
                except:
                    pass

manager = ConnectionManager()
