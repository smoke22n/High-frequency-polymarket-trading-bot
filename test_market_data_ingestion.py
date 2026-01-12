"""
Test script for the market data ingestion engine
"""
import asyncio
import random
from decimal import Decimal
from market_data_ingestion import MarketDataIngestionEngine, DeltaUpdate, OrderBookEntry


async def simulate_websocket_server():
    """
    Simulate a WebSocket server that sends order book updates
    This is just for testing purposes
    """
    import websockets
    import json
    import time
    
    async def handler(websocket, path):
        print("WebSocket client connected")
        try:
            async for message in websocket:
                data = json.loads(message)
                print(f"Received: {data}")
                
                # If it's a subscription message, start sending mock data
                if data.get("type") == "subscribe" and data.get("channel") == "orderbook":
                    market_id = data.get("market_token_id", "test-market")
                    print(f"Subscribed to market: {market_id}")
                    
                    # Send mock order book updates periodically
                    while True:
                        try:
                            # Generate mock order book update
                            mock_update = {
                                "timestamp": time.time(),
                                "market_id": market_id,
                                "bids": [
                                    {"price": str(49999.0 + random.uniform(-10, 10)), "size": str(random.uniform(0.1, 5.0))},
                                    {"price": str(49995.0 + random.uniform(-10, 10)), "size": str(random.uniform(0.1, 5.0))},
                                    {"price": str(49990.0 + random.uniform(-10, 10)), "size": str(random.uniform(0.1, 5.0))}
                                ],
                                "asks": [
                                    {"price": str(50001.0 + random.uniform(-10, 10)), "size": str(random.uniform(0.1, 5.0))},
                                    {"price": str(50005.0 + random.uniform(-10, 10)), "size": str(random.uniform(0.1, 5.0))},
                                    {"price": str(50010.0 + random.uniform(-10, 10)), "size": str(random.uniform(0.1, 5.0))}
                                ]
                            }
                            
                            await websocket.send(json.dumps(mock_update))
                            await asyncio.sleep(0.5)  # Send update every 500ms for testing
                        except websockets.exceptions.ConnectionClosed:
                            print("Client disconnected")
                            break
        except Exception as e:
            print(f"Error in WebSocket handler: {e}")
    
    # Start the server on port 8765
    server = await websockets.serve(handler, "localhost", 8765)
    print("WebSocket server started on ws://localhost:8765")
    return server


async def run_test():
    """
    Test the market data ingestion engine
    """
    print("Starting market data ingestion engine test...")
    
    # Start the mock WebSocket server in the background
    server = await simulate_websocket_server()
    
    # Create the market data ingestion engine
    engine = MarketDataIngestionEngine(
        market_token_id="Will Bitcoin hit $100k?",
        websocket_url="ws://localhost:8765"
    )
    
    try:
        # Run the engine for 5 seconds for testing
        await asyncio.wait_for(engine.start_engine(), timeout=5.0)
    except asyncio.TimeoutError:
        print("Test timeout reached, stopping engine")
        await engine.stop_engine()
    except KeyboardInterrupt:
        print("Test interrupted by user")
        await engine.stop_engine()
    finally:
        server.close()
        await server.wait_closed()


def test_local_order_book():
    """
    Test the LocalOrderBook functionality directly
    """
    print("\nTesting LocalOrderBook functionality...")
    
    # Create a local order book
    order_book = LocalOrderBook("test-market")
    
    # Create some initial delta updates
    initial_delta = DeltaUpdate(
        market_id="test-market",
        timestamp=1.0,
        bids=[
            OrderBookEntry(price=Decimal('49999.0'), size=Decimal('1.5'), side='bid'),
            OrderBookEntry(price=Decimal('49995.0'), size=Decimal('2.0'), side='bid'),
            OrderBookEntry(price=Decimal('49990.0'), size=Decimal('3.0'), side='bid')
        ],
        asks=[
            OrderBookEntry(price=Decimal('50001.0'), size=Decimal('1.2'), side='ask'),
            OrderBookEntry(price=Decimal('50005.0'), size=Decimal('2.5'), side='ask'),
            OrderBookEntry(price=Decimal('50010.0'), size=Decimal('1.8'), side='ask')
        ],
        deleted_bids=[],
        deleted_asks=[]
    )
    
    # Apply the initial delta
    order_book.apply_delta(initial_delta)
    
    print(f"Best bid: {order_book.get_best_bid().price}")
    print(f"Best ask: {order_book.get_best_ask().price}")
    print(f"Mid-price: {order_book.get_mid_price()}")
    print(f"Spread: {order_book.get_spread()}")
    
    # Create an update that modifies some entries
    update_delta = DeltaUpdate(
        market_id="test-market",
        timestamp=2.0,
        bids=[
            OrderBookEntry(price=Decimal('50000.0'), size=Decimal('1.0'), side='bid'),  # New bid
            OrderBookEntry(price=Decimal('49995.0'), size=Decimal('3.0'), side='bid')   # Updated size
        ],
        asks=[
            OrderBookEntry(price=Decimal('50002.0'), size=Decimal('1.5'), side='ask'),  # New ask
        ],
        deleted_bids=[Decimal('49990.0')],  # Remove lowest bid
        deleted_asks=[]  # No asks to remove
    )
    
    # Apply the update
    order_book.apply_delta(update_delta)
    
    print(f"After update - Best bid: {order_book.get_best_bid().price}")
    print(f"After update - Best ask: {order_book.get_best_ask().price}")
    print(f"After update - Mid-price: {order_book.get_mid_price()}")
    print(f"After update - Spread: {order_book.get_spread()}")


if __name__ == "__main__":
    # First run the direct unit tests
    test_local_order_book()
    
    # Then run the integration test (uncomment to run)
    # asyncio.run(run_test())