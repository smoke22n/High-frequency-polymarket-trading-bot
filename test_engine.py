import asyncio
from decimal import Decimal
from order_book_engine import OrderBook, MarketDataIngestor


def test_order_book():
    """Test the OrderBook class functionality."""
    print("Testing OrderBook class...")
    
    # Create an order book
    ob = OrderBook("test_market")
    
    # Add some initial data
    initial_data = {
        'bids': [
            {'price': '100.50', 'quantity': '10.0', 'action': 'add'},
            {'price': '100.00', 'quantity': '20.0', 'action': 'add'},
            {'price': '99.50', 'quantity': '15.0', 'action': 'add'},
        ],
        'asks': [
            {'price': '101.00', 'quantity': '5.0', 'action': 'add'},
            {'price': '101.50', 'quantity': '8.0', 'action': 'add'},
            {'price': '102.00', 'quantity': '12.0', 'action': 'add'},
        ]
    }
    
    ob.update_from_delta(initial_data)
    
    # Verify best bid and ask
    best_bid = ob.get_best_bid()
    best_ask = ob.get_best_ask()
    
    print(f"Best bid: {best_bid}")
    print(f"Best ask: {best_ask}")
    
    assert best_bid == Decimal('100.50'), f"Expected 100.50, got {best_bid}"
    assert best_ask == Decimal('101.00'), f"Expected 101.00, got {best_ask}"
    
    # Test mid-price and spread
    mid_price = ob.calculate_mid_price()
    spread = ob.calculate_spread()
    
    print(f"Mid-price: {mid_price}")
    print(f"Spread: {spread}")
    
    expected_mid = (Decimal('100.50') + Decimal('101.00')) / 2
    expected_spread = Decimal('101.00') - Decimal('100.50')
    
    assert mid_price == expected_mid, f"Expected {expected_mid}, got {mid_price}"
    assert spread == expected_spread, f"Expected {expected_spread}, got {spread}"
    
    # Test update operations
    update_data = {
        'bids': [
            {'price': '100.50', 'quantity': '5.0', 'action': 'update'},  # Reduce quantity
            {'price': '99.00', 'quantity': '25.0', 'action': 'add'},    # Add new level
        ],
        'asks': [
            {'price': '101.00', 'quantity': '0.0', 'action': 'remove'}, # Remove level
        ]
    }
    
    ob.update_from_delta(update_data)
    
    # Verify updates
    new_best_bid = ob.get_best_bid()
    new_best_ask = ob.get_best_ask()
    
    print(f"After updates - Best bid: {new_best_bid}, Best ask: {new_best_ask}")
    
    assert new_best_bid == Decimal('100.50'), f"Expected 100.50, got {new_best_bid}"
    # The best ask should now be 101.50 since 101.00 was removed
    assert new_best_ask == Decimal('101.50'), f"Expected 101.50, got {new_best_ask}"
    
    print("OrderBook tests passed!\n")


def test_market_data_ingestor():
    """Test the MarketDataIngestor class functionality."""
    print("Testing MarketDataIngestor class...")
    
    # Create a MarketDataIngestor (without connecting to actual WebSocket for testing)
    ingestor = MarketDataIngestor("test_market_token")
    
    # Add initial data
    initial_data = {
        'bids': [
            {'price': '0.70', 'quantity': '100.0', 'action': 'add'},
            {'price': '0.69', 'quantity': '200.0', 'action': 'add'},
        ],
        'asks': [
            {'price': '0.71', 'quantity': '150.0', 'action': 'add'},
            {'price': '0.72', 'quantity': '80.0', 'action': 'add'},
        ]
    }
    
    ingestor.order_book.update_from_delta(initial_data)
    
    # Verify initial state
    best_bid = ingestor.order_book.get_best_bid()
    best_ask = ingestor.order_book.get_best_ask()
    
    assert best_bid == Decimal('0.70'), f"Expected 0.70, got {best_bid}"
    assert best_ask == Decimal('0.71'), f"Expected 0.71, got {best_ask}"
    
    # Test delta buffering
    delta1 = {
        'bids': [{'price': '0.68', 'quantity': '300.0', 'action': 'add'}],
        'asks': []
    }
    
    ingestor.buffer_delta(delta1)
    
    # Verify buffer contains the delta
    recent_deltas = ingestor.get_recent_deltas(1)
    assert len(recent_deltas) == 1, f"Expected 1 delta in buffer, got {len(recent_deltas)}"
    assert recent_deltas[0]['delta'] == delta1, "Delta in buffer doesn't match expected"
    
    # Test applying deltas
    delta2 = {
        'bids': [],
        'asks': [{'price': '0.73', 'quantity': '120.0', 'action': 'add'}]
    }
    
    ingestor.apply_deltas([delta2])
    
    # Verify the ask was added
    new_best_ask = ingestor.order_book.get_best_ask()
    assert new_best_ask == Decimal('0.71'), f"Expected 0.71 (unchanged), got {new_best_ask}"  # 0.71 still best
    
    # Check if 0.73 was added to asks
    assert Decimal('0.73') in ingestor.order_book.asks, "Price 0.73 should be in asks"
    
    print("MarketDataIngestor tests passed!\n")


def test_calculations():
    """Test mid-price and spread calculations."""
    print("Testing calculations...")
    
    ob = OrderBook("calc_test")
    
    # Add data for calculation testing
    data = {
        'bids': [
            {'price': '50.25', 'quantity': '10.0', 'action': 'add'},
            {'price': '50.00', 'quantity': '20.0', 'action': 'add'},
        ],
        'asks': [
            {'price': '50.75', 'quantity': '15.0', 'action': 'add'},
            {'price': '51.00', 'quantity': '25.0', 'action': 'add'},
        ]
    }
    
    ob.update_from_delta(data)
    
    mid_price = ob.calculate_mid_price()
    spread = ob.calculate_spread()
    rel_spread = ob.calculate_relative_spread()
    
    expected_mid = (Decimal('50.25') + Decimal('50.75')) / 2  # best bid and ask
    expected_spread = Decimal('50.75') - Decimal('50.25')
    expected_rel_spread = (expected_spread / expected_mid) * 100
    
    print(f"Calculated mid-price: {mid_price}, Expected: {expected_mid}")
    print(f"Calculated spread: {spread}, Expected: {expected_spread}")
    print(f"Calculated relative spread: {rel_spread}, Expected: {expected_rel_spread}")
    
    assert mid_price == expected_mid, f"Mid-price mismatch: {mid_price} != {expected_mid}"
    assert spread == expected_spread, f"Spread mismatch: {spread} != {expected_spread}"
    assert abs(rel_spread - expected_rel_spread) < Decimal('0.0001'), \
           f"Relative spread mismatch: {rel_spread} != {expected_rel_spread}"
    
    print("Calculation tests passed!\n")


async def run_tests():
    """Run all tests."""
    print("Running tests for market data ingestion engine...\n")
    
    test_order_book()
    test_market_data_ingestor()
    test_calculations()
    
    print("All tests passed!")


if __name__ == "__main__":
    asyncio.run(run_tests())