#!/usr/bin/env python3
"""
Example usage of the High Frequency Market Making Strategy
"""

from decimal import Decimal
from market_making_strategy import MarketMakingStrategy, MarketMakingConfig, create_batch_order_payload
from order_book_engine import LocalOrderBook
from utils.inventory_manager import InventoryManager


def main():
    print("Initializing High Frequency Market Making Strategy...")
    
    # Create local order book (this would typically be populated with real market data)
    local_order_book = LocalOrderBook()
    
    # Add some sample market data to the order book
    # For example, in market1_YES:
    local_order_book.add_order('market1_YES', 'buy', Decimal('0.58'), Decimal('50'))
    local_order_book.add_order('market1_YES', 'buy', Decimal('0.57'), Decimal('40'))
    local_order_book.add_order('market1_YES', 'sell', Decimal('0.60'), Decimal('45'))
    local_order_book.add_order('market1_YES', 'sell', Decimal('0.61'), Decimal('55'))
    
    # And in market1_NO:
    local_order_book.add_order('market1_NO', 'buy', Decimal('0.40'), Decimal('48'))
    local_order_book.add_order('market1_NO', 'buy', Decimal('0.39'), Decimal('42'))
    local_order_book.add_order('market1_NO', 'sell', Decimal('0.42'), Decimal('46'))
    local_order_book.add_order('market1_NO', 'sell', Decimal('0.43'), Decimal('52'))
    
    # Create inventory manager
    inventory_manager = InventoryManager()
    
    # Configure the market making strategy
    config = MarketMakingConfig(
        target_spread=Decimal('0.002'),  # 20 basis points
        max_order_size=Decimal('100'),
        min_order_size=Decimal('1'),
        inventory_skew_factor=Decimal('0.5'),
        max_inventory_threshold=Decimal('1000'),
        num_levels=3
    )
    
    # Create the strategy
    strategy = MarketMakingStrategy(local_order_book, inventory_manager, config)
    
    print("Market Making Strategy initialized successfully!")
    
    # Calculate fair prices
    fair_price_yes = strategy.calculate_fair_price('market1_YES')
    fair_price_no = strategy.calculate_fair_price('market1_NO')
    
    print(f"Fair price for YES: {fair_price_yes}")
    print(f"Fair price for NO: {fair_price_no}")
    
    # Generate orders for market1 with YES and NO outcomes
    orders = strategy.generate_orders('market1', ['YES', 'NO'])
    
    print(f"\nGenerated {len(orders)} orders:")
    for i, order in enumerate(orders[:10]):  # Show first 10 orders
        print(f"  {i+1}. {order.side.upper()} {order.quantity} @ {order.price} for {order.market_id}")
    
    if len(orders) > 10:
        print(f"  ... and {len(orders) - 10} more orders")
    
    # Create batch order payload
    batch_payload = create_batch_order_payload(orders)
    print(f"\nBatch order payload created with {len(batch_payload['orders'])} orders")
    
    # Demonstrate inventory skew effect
    print("\nDemonstrating inventory skew effect:")
    
    # Simulate holding many YES tokens (long position)
    inventory_manager.update_position('market1_YES', 'YES', Decimal('500'))  # Large long position
    
    print(f"Updated inventory: YES position = {inventory_manager.get_position('market1_YES', 'YES')}")
    
    # Recalculate orders with the new inventory position
    orders_with_skew = strategy.generate_orders('market1', ['YES', 'NO'])
    
    print(f"Orders after applying inventory skew: {len(orders_with_skew)} orders")
    
    # Show how the strategy adjusts prices based on inventory
    base_buy = Decimal('0.58')
    base_sell = Decimal('0.60')
    
    print(f"\nOriginal prices: Buy {base_buy}, Sell {base_sell}")
    
    adjusted_buy, adjusted_sell = strategy.adjust_prices_for_skew(base_buy, base_sell, 'market1_YES', 'YES')
    print(f"With inventory skew: Buy {adjusted_buy}, Sell {adjusted_sell}")
    
    print("\nHigh Frequency Market Making Strategy example completed!")


if __name__ == "__main__":
    main()