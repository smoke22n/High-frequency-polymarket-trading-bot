import asyncio
import json
import logging
import websockets
from typing import Callable, Dict, Optional
from utils.rate_limiter import rate_limit_manager
from config.settings import Settings


logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with heartbeat and auto-reconnect capabilities.
    """
    
    def __init__(self, url: str, settings: Settings):
        self.url = url
        self.settings = settings
        self.websocket = None
        self.is_connected = False
        self.reconnect_delay = settings.WEBSOCKET_RECONNECT_DELAY
        self.heartbeat_interval = settings.WEBSOCKET_HEARTBEAT_INTERVAL
        self.heartbeat_task = None
        self.message_handlers: Dict[str, Callable] = {}
        self._stop_event = asyncio.Event()
        
    async def connect(self):
        """
        Establish a WebSocket connection.
        """
        try:
            logger.info(f"Connecting to {self.url}")
            self.websocket = await websockets.connect(
                self.url,
                extra_headers={
                    "Authorization": f"Bearer {self.settings.L2_API_KEY}"
                }
            )
            self.is_connected = True
            logger.info("Connected successfully")
            
            # Start heartbeat
            self.heartbeat_task = asyncio.create_task(self._heartbeat())
            
            # Start listening for messages
            await self._listen()
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            await self.disconnect()
            await self._reconnect()
    
    async def disconnect(self):
        """
        Disconnect the WebSocket connection.
        """
        self.is_connected = False
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        if self.websocket:
            await self.websocket.close()
        logger.info("Disconnected")
    
    async def _reconnect(self):
        """
        Reconnect to the WebSocket with exponential backoff.
        """
        if self._stop_event.is_set():
            return
            
        logger.info(f"Attempting to reconnect in {self.reconnect_delay} seconds...")
        await asyncio.sleep(self.reconnect_delay)
        await self.connect()
    
    async def _heartbeat(self):
        """
        Send periodic ping messages to keep the connection alive.
        """
        while self.is_connected and not self._stop_event.is_set():
            try:
                await self.send_ping()
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
                await self.disconnect()
                await self._reconnect()
                break
    
    async def send_ping(self):
        """
        Send a ping message to the server.
        """
        if self.websocket:
            try:
                await self.websocket.ping()
                logger.debug("Ping sent")
            except Exception as e:
                logger.error(f"Ping failed: {e}")
    
    async def _listen(self):
        """
        Listen for incoming messages and dispatch them to handlers.
        """
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed by server")
            await self.disconnect()
            await self._reconnect()
        except Exception as e:
            logger.error(f"Listening error: {e}")
            await self.disconnect()
            await self._reconnect()
    
    async def _handle_message(self, message: str):
        """
        Handle an incoming message by dispatching to the appropriate handler.
        """
        try:
            data = json.loads(message)
            message_type = data.get("type", "unknown")
            
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                await handler(data)
            else:
                logger.debug(f"No handler for message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Failed to decode message: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def register_handler(self, message_type: str, handler: Callable):
        """
        Register a handler for a specific message type.
        """
        self.message_handlers[message_type] = handler
    
    async def send_message(self, message: dict):
        """
        Send a message through the WebSocket connection.
        """
        if not self.is_connected or not self.websocket:
            raise ConnectionError("Not connected to WebSocket")
        
        # Apply rate limiting for sending messages
        await rate_limit_manager.get_limiter(
            "websocket_send", 
            self.settings.RATE_LIMIT_REQUESTS, 
            self.settings.RATE_LIMIT_WINDOW
        ).acquire()
        
        await self.websocket.send(json.dumps(message))
    
    def stop(self):
        """
        Stop the connection manager.
        """
        self._stop_event.set()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()