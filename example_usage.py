import asyncio
import json
from decimal import Decimal
from order_book_engine import MarketDataIngestor


def metrics_callback(metrics):
    """Callback function to handle periodic metrics."""
    print(f"[METRICS CALLBACK] {metrics}")


async def simulate_market_data():
    """Simulate market data for testing purposes."""
    # In a real scenario, this would be replaced with actual WebSocket data
    # For demonstration, we'll create a mock that simulates market updates
    pass


async def main():
    # Example market ID for "Will Bitcoin hit $100k?"
    market_token_id = "bitcoin_100k_prediction"
    
    # Create the market data ingestor
    ingestor = MarketDataIngestor(
        market_token_id=market_token_id,
        # Using a mock WebSocket URL for demonstration
        # In real implementation, this would be the actual Polymarket WebSocket endpoint
    )
    
    # Set up metrics callback
    ingestor.set_metrics_callback(metrics_callback)
    
    # For demonstration purposes, let's initialize the order book with some sample data
    # This would normally come from the WebSocket stream
    sample_initial_data = {
        'bids': [
            {'price': '0.65', 'quantity': '100.0', 'action': 'add'},
            {'price': '0.64', 'quantity': '200.0', 'action': 'add'},
            {'price': '0.63', 'quantity': '150.0', 'action': 'add'},
        ],
        'asks': [
            {'price': '0.66', 'quantity': '80.0', 'action': 'add'},
            {'price': '0.67', 'quantity': '120.0', 'action': 'add'},
            {'price': '0.68', 'quantity': '90.0', 'action': 'add'},
        ]
    }
    
    # Apply initial data to the order book
    ingestor.order_book.update_from_delta(sample_initial_data)
    
    print("Initial order book state:")
    print(json.dumps(ingestor.order_book.get_order_book_state(), indent=2))
    
    # Simulate some delta updates
    delta_updates = [
        {
            'bids': [
                {'price': '0.65', 'quantity': '50.0', 'action': 'update'},  # Reduce bid quantity
                {'price': '0.62', 'quantity': '300.0', 'action': 'add'},   # Add new bid
            ],
            'asks': [
                {'price': '0.66', 'quantity': '0.0', 'action': 'remove'},  # Remove ask level
                {'price': '0.69', 'quantity': '75.0', 'action': 'add'},    # Add new ask
            ]
        },
        {
            'bids': [
                {'price': '0.64', 'quantity': '250.0', 'action': 'update'},  # Increase bid quantity
            ],
            'asks': [
                {'price': '0.67', 'quantity': '180.0', 'action': 'update'},  # Increase ask quantity
            ]
        }
    ]
    
    print("\nApplying delta updates...")
    for i, delta in enumerate(delta_updates):
        print(f"\nApplying delta update {i+1}:")
        print(json.dumps(delta, indent=2))
        
        # Buffer and apply the delta
        ingestor.buffer_delta(delta)
        ingestor.apply_deltas([delta])
        
        # Show current state
        print("Current order book state:")
        print(json.dumps(ingestor.order_book.get_order_book_state(), indent=2))
        
        # Calculate and show metrics
        mid_price = ingestor.order_book.calculate_mid_price()
        spread = ingestor.order_book.calculate_spread()
        relative_spread = ingestor.order_book.calculate_relative_spread()
        
        print(f"Mid-price: {mid_price}")
        print(f"Spread: {spread}")
        print(f"Relative Spread: {relative_spread}%")
    
    # Show recent deltas in buffer
    print(f"\nRecent deltas in buffer ({len(ingestor.delta_buffer)} total):")
    for i, buffered_delta in enumerate(ingestor.get_recent_deltas()):
        print(f"  Delta {i+1}: {json.dumps(buffered_delta, indent=2)[:100]}...")


if __name__ == "__main__":
    asyncio.run(main())