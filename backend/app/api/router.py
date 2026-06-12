from fastapi import APIRouter
from app.api.endpoints import nmap, chat, websocket

api_router = APIRouter()

api_router.include_router(nmap.router)
api_router.include_router(chat.router)
api_router.include_router(websocket.router)
