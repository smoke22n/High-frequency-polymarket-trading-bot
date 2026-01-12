import asyncio
import json
import time
from collections import deque
from typing import Dict, List, Optional, Any
from decimal import Decimal
import websockets


class OrderBook:
    """
    Maintains a local, real-time mirror of the order book for a specific market.
    """
    
    def __init__(self, market_id: str):
        self.market_id = market_id
        self.bids: Dict[Decimal, Decimal] = {}  # price -> quantity
        self.asks: Dict[Decimal, Decimal] = {}  # price -> quantity
        self.last_update_time = None
        self.is_active = False
        
    def update_from_delta(self, delta: Dict[str, Any]) -> None:
        """
        Apply a delta update to the order book.
        
        Delta format example:
        {
            'bids': [
                {'price': '100.50', 'quantity': '10.0', 'action': 'add'|'remove'|'update'},
                ...
            ],
            'asks': [
                {'price': '101.20', 'quantity': '5.0', 'action': 'add'|'remove'|'update'},
                ...
            ]
        }
        """
        if 'bids' in delta:
            for bid_update in delta['bids']:
                price = Decimal(bid_update['price'])
                quantity = Decimal(bid_update['quantity'])
                action = bid_update.get('action', 'update')
                
                if action == 'remove' or quantity == 0:
                    self.bids.pop(price, None)
                elif action == 'add':
                    self.bids[price] = self.bids.get(price, Decimal('0')) + quantity
                else:  # update
                    self.bids[price] = quantity
        
        if 'asks' in delta:
            for ask_update in delta['asks']:
                price = Decimal(ask_update['price'])
                quantity = Decimal(ask_update['quantity'])
                action = ask_update.get('action', 'update')
                
                if action == 'remove' or quantity == 0:
                    self.asks.pop(price, None)
                elif action == 'add':
                    self.asks[price] = self.asks.get(price, Decimal('0')) + quantity
                else:  # update
                    self.asks[price] = quantity
        
        self.last_update_time = time.time()
    
    def get_best_bid(self) -> Optional[Decimal]:
        """Return the highest bid price."""
        if not self.bids:
            return None
        return max(self.bids.keys())
    
    def get_best_ask(self) -> Optional[Decimal]:
        """Return the lowest ask price."""
        if not self.asks:
            return None
        return min(self.asks.keys())
    
    def calculate_mid_price(self) -> Optional[Decimal]:
        """Calculate the mid-price between best bid and best ask."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid is not None and best_ask is not None:
            return (best_bid + best_ask) / 2
        return None
    
    def calculate_spread(self) -> Optional[Decimal]:
        """Calculate the absolute spread between best bid and best ask."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid is not None and best_ask is not None:
            return best_ask - best_bid
        return None
    
    def calculate_relative_spread(self) -> Optional[Decimal]:
        """Calculate the relative spread as percentage."""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid is not None and best_ask is not None and best_bid > 0:
            absolute_spread = best_ask - best_bid
            mid_price = (best_bid + best_ask) / 2
            return (absolute_spread / mid_price) * 100
        return None
    
    def get_order_book_state(self) -> Dict[str, Any]:
        """Return the current state of the order book."""
        return {
            'market_id': self.market_id,
            'bids': {str(price): str(quantity) for price, quantity in self.bids.items()},
            'asks': {str(price): str(quantity) for price, quantity in self.asks.items()},
            'last_update_time': self.last_update_time
        }
    
    def reset(self) -> None:
        """Reset the order book to empty state."""
        self.bids.clear()
        self.asks.clear()
        self.last_update_time = None


class MarketDataIngestor:
    """
    Market data ingestion engine that maintains a real-time mirror of the order book.
    """

    def __init__(self, market_token_id: str, connection_manager=None, settings=None):
        self.market_token_id = market_token_id
        self.order_book = OrderBook(market_token_id)
        self.delta_buffer = deque(maxlen=1000)  # Buffer up to 1000 deltas
        self.is_running = False
        self.metrics_callback = None
        self.connection_manager = connection_manager
        self.settings = settings
        self._message_handler_registered = False

    async def connect(self):
        """Connect to the WebSocket channel for the market using ConnectionManager."""
        if not self.connection_manager:
            # If no connection manager provided, create one
            from connection.connection_manager import ConnectionManager
            from config.settings import Settings

            if not self.settings:
                self.settings = Settings()

            ws_url = f"wss://clob.polymarket.com/ws"
            self.connection_manager = ConnectionManager(ws_url, self.settings)

        # Register message handler for orderbook updates
        self.connection_manager.register_handler("orderbook_update", self._handle_orderbook_update)
        self.connection_manager.register_handler("l2_data", self._handle_l2_data)
        self._message_handler_registered = True

        # Subscribe to orderbook updates for the specific market
        subscribe_msg = {
            "type": "subscribe",
            "channel": "l2_book",
            "market_token_id": self.market_token_id
        }

        await self.connection_manager.send_message(subscribe_msg)
        self.is_running = True
        print(f"Connected to WebSocket for market: {self.market_token_id}")

    async def disconnect(self):
        """Disconnect from the WebSocket."""
        self.is_running = False
        if self.connection_manager and self._message_handler_registered:
            # Unsubscribe from orderbook updates
            unsubscribe_msg = {
                "type": "unsubscribe",
                "channel": "l2_book",
                "market_token_id": self.market_token_id
            }
            await self.connection_manager.send_message(unsubscribe_msg)
        print("Disconnected from WebSocket")

    async def _handle_orderbook_update(self, data: Dict):
        """Handle orderbook update messages."""
        try:
            # Extract market ID and deltas from the message
            market_id = data.get('market_id', self.market_token_id)
            if market_id != self.market_token_id:
                return  # Not for this market

            delta = data.get('data', {})
            if delta:
                self.buffer_delta(delta)
                # Apply delta immediately to maintain real-time sync
                self.apply_deltas([delta])
        except Exception as e:
            print(f"Error handling orderbook update: {e}")

    async def _handle_l2_data(self, data: Dict):
        """Handle L2 book data messages."""
        try:
            # Process L2 book data (price, size, order count)
            market_id = data.get('market_id', self.market_token_id)
            if market_id != self.market_token_id:
                return  # Not for this market

            l2_updates = data.get('l2_updates', [])
            for update in l2_updates:
                # Convert L2 data to our delta format
                delta = self._convert_l2_to_delta(update)
                if delta:
                    self.buffer_delta(delta)
                    self.apply_deltas([delta])
        except Exception as e:
            print(f"Error handling L2 data: {e}")

    def _convert_l2_to_delta(self, l2_data: Dict) -> Dict:
        """Convert L2 data format to our internal delta format."""
        bids = []
        asks = []

        # Process bids
        if 'bids' in l2_data:
            for bid in l2_data['bids']:
                bids.append({
                    'price': str(bid['price']),
                    'quantity': str(bid['size']),
                    'action': 'update'
                })

        # Process asks
        if 'asks' in l2_data:
            for ask in l2_data['asks']:
                asks.append({
                    'price': str(ask['price']),
                    'quantity': str(ask['size']),
                    'action': 'update'
                })

        return {'bids': bids, 'asks': asks} if bids or asks else {}

    async def consume_data(self):
        """Consume incoming WebSocket data and buffer deltas."""
        # This method is now handled by the connection manager's message handlers
        # Just keep the loop running while the connection is active
        while self.is_running:
            await asyncio.sleep(0.1)  # Small sleep to prevent busy waiting

    def buffer_delta(self, delta: Dict[str, Any]):
        """Buffer incoming delta updates."""
        timestamp = time.time()
        self.delta_buffer.append({
            'timestamp': timestamp,
            'delta': delta
        })

    def get_recent_deltas(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent deltas from the buffer."""
        return list(self.delta_buffer)[-count:]

    def apply_deltas(self, deltas: List[Dict[str, Any]]):
        """Apply a list of deltas to the local order book snapshot."""
        for delta in deltas:
            self.order_book.update_from_delta(delta)

    def set_metrics_callback(self, callback):
        """Set a callback function to receive periodic metrics."""
        self.metrics_callback = callback

    async def start_periodic_calculations(self, interval_ms: int = 100):
        """Start periodic calculation of mid-price and spread."""
        while self.is_running:
            try:
                mid_price = self.order_book.calculate_mid_price()
                spread = self.order_book.calculate_spread()
                relative_spread = self.order_book.calculate_relative_spread()

                metrics = {
                    'timestamp': time.time(),
                    'mid_price': float(mid_price) if mid_price is not None else None,
                    'spread': float(spread) if spread is not None else None,
                    'relative_spread': float(relative_spread) if relative_spread is not None else None,
                    'market_id': self.market_token_id
                }

                if self.metrics_callback:
                    self.metrics_callback(metrics)

                # Print metrics for demonstration
                if mid_price is not None and spread is not None:
                    print(f"Market: {self.market_token_id} | Mid-price: {mid_price} | Spread: {spread} | "
                          f"Relative Spread: {relative_spread:.4f}%")

                await asyncio.sleep(interval_ms / 1000.0)  # Convert ms to seconds

            except Exception as e:
                print(f"Error in periodic calculations: {e}")
                await asyncio.sleep(interval_ms / 1000.0)

    async def run(self):
        """Main run loop that starts data consumption and periodic calculations."""
        await self.connect()

        # Run data consumption and periodic calculations concurrently
        await asyncio.gather(
            self.consume_data(),
            self.start_periodic_calculations()
        )