"""
Market Data Ingestion Engine
Maintains a real-time mirror of the order book for a specific market ID
"""
import asyncio
import json
import logging
from collections import deque
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class OrderBookEntry:
    """Represents a single entry in the order book (price level)"""
    price: Decimal
    size: Decimal
    side: str  # 'bid' or 'ask'


@dataclass
class DeltaUpdate:
    """Represents a delta update to the order book"""
    market_id: str
    timestamp: float
    bids: List[OrderBookEntry]  # New or updated bid entries
    asks: List[OrderBookEntry]  # New or updated ask entries
    deleted_bids: List[Decimal]  # Price levels to remove from bids
    deleted_asks: List[Decimal]  # Price levels to remove from asks


class LocalOrderBook:
    """
    Maintains a local, real-time mirror of the order book
    """
    def __init__(self, market_id: str):
        self.market_id = market_id
        self.bids: Dict[Decimal, OrderBookEntry] = {}  # price -> OrderBookEntry
        self.asks: Dict[Decimal, OrderBookEntry] = {}  # price -> OrderBookEntry
        self.last_update_time = None
        
    def apply_delta(self, delta: DeltaUpdate):
        """Apply a delta update to the local order book"""
        # Apply bid updates
        for bid in delta.bids:
            self.bids[bid.price] = bid
            
        # Apply ask updates
        for ask in delta.asks:
            self.asks[ask.price] = ask
            
        # Remove deleted bids
        for price in delta.deleted_bids:
            self.bids.pop(price, None)
            
        # Remove deleted asks
        for price in delta.deleted_asks:
            self.asks.pop(price, None)
            
        self.last_update_time = delta.timestamp
    
    def get_best_bid(self) -> Optional[OrderBookEntry]:
        """Get the best bid (highest bid price)"""
        if not self.bids:
            return None
        best_price = max(self.bids.keys())
        return self.bids[best_price]
    
    def get_best_ask(self) -> Optional[OrderBookEntry]:
        """Get the best ask (lowest ask price)"""
        if not self.asks:
            return None
        best_price = min(self.asks.keys())
        return self.asks[best_price]
    
    def get_mid_price(self) -> Optional[Decimal]:
        """Calculate the mid-price between best bid and ask"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return (best_bid.price + best_ask.price) / 2
        elif best_bid:
            return best_bid.price
        elif best_ask:
            return best_ask.price
        else:
            return None
    
    def get_spread(self) -> Optional[Decimal]:
        """Calculate the spread between best bid and ask"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return best_ask.price - best_bid.price
        else:
            return None
    
    def get_order_book_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of the current order book"""
        return {
            'market_id': self.market_id,
            'bids': sorted([{'price': float(entry.price), 'size': float(entry.size)} 
                           for entry in self.bids.values()], 
                          key=lambda x: x['price'], reverse=True),
            'asks': sorted([{'price': float(entry.price), 'size': float(entry.size)} 
                           for entry in self.asks.values()], 
                          key=lambda x: x['price']),
            'last_update_time': self.last_update_time
        }


class MarketDataIngestionEngine:
    """
    Main engine for ingesting market data and maintaining local order book
    """
    def __init__(self, market_token_id: str, websocket_url: str):
        self.market_token_id = market_token_id
        self.websocket_url = websocket_url
        self.local_order_book = LocalOrderBook(market_token_id)
        self.delta_buffer = deque(maxlen=1000)  # Buffer for incoming deltas
        self.is_running = False
        self.websocket_connection = None
        self.logger = logging.getLogger(__name__)
        
    async def connect_websocket(self):
        """Connect to the WebSocket channel for the market token ID"""
        try:
            import websockets
            self.websocket_connection = await websockets.connect(self.websocket_url)
            self.logger.info(f"Connected to WebSocket for market: {self.market_token_id}")
        except ImportError:
            self.logger.error("websockets library not installed. Install with 'pip install websockets'")
            raise
        except Exception as e:
            self.logger.error(f"Failed to connect to WebSocket: {e}")
            raise
    
    async def subscribe_to_market(self):
        """Subscribe to the relevant WebSocket channel for the market token ID"""
        if not self.websocket_connection:
            await self.connect_websocket()
            
        # Send subscription message
        subscription_msg = {
            "type": "subscribe",
            "channel": "orderbook",
            "market_token_id": self.market_token_id
        }
        
        await self.websocket_connection.send(json.dumps(subscription_msg))
        self.logger.info(f"Subscribed to order book for market: {self.market_token_id}")
    
    async def start_listening(self):
        """Start listening for WebSocket messages"""
        if not self.websocket_connection:
            await self.subscribe_to_market()
            
        self.is_running = True
        try:
            async for message in self.websocket_connection:
                await self.process_incoming_message(message)
        except Exception as e:
            self.logger.error(f"Error in WebSocket listener: {e}")
        finally:
            self.is_running = False
    
    async def process_incoming_message(self, message: str):
        """Process incoming WebSocket message and add to delta buffer"""
        try:
            data = json.loads(message)
            
            # Convert raw message to DeltaUpdate object
            delta = self._parse_delta_update(data)
            self.delta_buffer.append(delta)
            
            # Apply the delta to the local order book
            self.local_order_book.apply_delta(delta)
            
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON received: {message}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    def _parse_delta_update(self, data: Dict) -> DeltaUpdate:
        """Parse raw WebSocket data into a DeltaUpdate object"""
        # This is a simplified parser - in practice, you'd need to adapt this
        # to the specific format of your exchange's WebSocket messages
        timestamp = data.get('timestamp', 0)
        
        bids = []
        asks = []
        deleted_bids = []
        deleted_asks = []
        
        # Parse bid updates
        for bid_data in data.get('bids', []):
            price = Decimal(str(bid_data['price']))
            size = Decimal(str(bid_data['size']))
            bids.append(OrderBookEntry(price=price, size=size, side='bid'))
        
        # Parse ask updates
        for ask_data in data.get('asks', []):
            price = Decimal(str(ask_data['price']))
            size = Decimal(str(ask_data['size']))
            asks.append(OrderBookEntry(price=price, size=size, side='ask'))
        
        # Parse deletions if present
        for price_str in data.get('deleted_bids', []):
            deleted_bids.append(Decimal(str(price_str)))
        
        for price_str in data.get('deleted_asks', []):
            deleted_asks.append(Decimal(str(price_str)))
        
        return DeltaUpdate(
            market_id=self.market_token_id,
            timestamp=timestamp,
            bids=bids,
            asks=asks,
            deleted_bids=deleted_bids,
            deleted_asks=deleted_asks
        )
    
    def get_current_mid_price(self) -> Optional[Decimal]:
        """Get the current mid-price"""
        return self.local_order_book.get_mid_price()
    
    def get_current_spread(self) -> Optional[Decimal]:
        """Get the current spread"""
        return self.local_order_book.get_spread()
    
    async def start_calculations(self):
        """Start periodic calculation of mid-price and spread"""
        while self.is_running:
            try:
                mid_price = self.get_current_mid_price()
                spread = self.get_current_spread()
                
                if mid_price is not None:
                    print(f"Mid-price for {self.market_token_id}: {mid_price}")
                if spread is not None:
                    print(f"Spread for {self.market_token_id}: {spread}")
                    
                # Wait for 100ms before next calculation
                await asyncio.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error in calculation loop: {e}")
    
    async def start_engine(self):
        """Start the market data ingestion engine"""
        await self.connect_websocket()
        await self.subscribe_to_market()
        
        # Run the WebSocket listener and calculation loop concurrently
        await asyncio.gather(
            self.start_listening(),
            self.start_calculations()
        )
    
    async def stop_engine(self):
        """Stop the market data ingestion engine"""
        self.is_running = False
        if self.websocket_connection:
            await self.websocket_connection.close()