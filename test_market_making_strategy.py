import unittest
from decimal import Decimal
from market_making_strategy import MarketMakingStrategy, MarketMakingConfig, Order
from order_book_engine import LocalOrderBook
from utils.inventory_manager import InventoryManager


class TestMarketMakingStrategy(unittest.TestCase):
    
    def setUp(self):
        # Create mock order book with some sample data
        self.order_book = LocalOrderBook()
        # Add some sample orders to simulate market data
        self.order_book.add_order('market1_YES', 'buy', Decimal('0.60'), Decimal('10'))
        self.order_book.add_order('market1_YES', 'buy', Decimal('0.59'), Decimal('20'))
        self.order_book.add_order('market1_YES', 'sell', Decimal('0.62'), Decimal('15'))
        self.order_book.add_order('market1_YES', 'sell', Decimal('0.63'), Decimal('25'))
        
        self.order_book.add_order('market1_NO', 'buy', Decimal('0.38'), Decimal('12'))
        self.order_book.add_order('market1_NO', 'buy', Decimal('0.37'), Decimal('18'))
        self.order_book.add_order('market1_NO', 'sell', Decimal('0.40'), Decimal('14'))
        self.order_book.add_order('market1_NO', 'sell', Decimal('0.41'), Decimal('22'))
        
        self.inventory_manager = InventoryManager()
        
        # Configure the strategy
        self.config = MarketMakingConfig(
            target_spread=Decimal('0.02'),  # 2% spread
            max_order_size=Decimal('50'),
            min_order_size=Decimal('1'),
            inventory_skew_factor=Decimal('0.5'),
            max_inventory_threshold=Decimal('100'),
            num_levels=2
        )
        
        self.strategy = MarketMakingStrategy(
            self.order_book,
            self.inventory_manager,
            self.config
        )
    
    def test_calculate_fair_price(self):
        """Test fair price calculation"""
        fair_price = self.strategy.calculate_fair_price('market1_YES')
        expected = (Decimal('0.60') + Decimal('0.62')) / 2  # Mid between best bid and ask
        self.assertEqual(fair_price, expected)
    
    def test_calculate_inventory_skew_no_position(self):
        """Test inventory skew calculation with no position"""
        skew = self.strategy.calculate_inventory_skew('market1_YES', 'YES')
        self.assertEqual(skew, Decimal('0'))
    
    def test_calculate_inventory_skew_long_position(self):
        """Test inventory skew calculation with long position"""
        # Set a long position
        self.inventory_manager.update_position('market1_YES', 'YES', Decimal('50'))
        
        skew = self.strategy.calculate_inventory_skew('market1_YES', 'YES')
        # With 50/100 threshold, normalized skew should be 0.5, and since it's long, it should be positive
        self.assertGreater(skew, Decimal('0'))
        self.assertLessEqual(skew, Decimal('1'))
    
    def test_calculate_inventory_skew_short_position(self):
        """Test inventory skew calculation with short position"""
        # Set a short position
        self.inventory_manager.update_position('market1_YES', 'YES', Decimal('-50'))
        
        skew = self.strategy.calculate_inventory_skew('market1_YES', 'YES')
        # With -50/100 threshold, normalized skew should be 0.5, and since it's short, it should be negative
        self.assertLess(skew, Decimal('0'))
        self.assertGreaterEqual(skew, Decimal('-1'))
    
    def test_adjust_prices_for_skew_no_skew(self):
        """Test price adjustment with no skew"""
        base_buy = Decimal('0.58')
        base_sell = Decimal('0.60')
        
        adj_buy, adj_sell = self.strategy.adjust_prices_for_skew(base_buy, base_sell, 'market1_YES', 'YES')
        
        self.assertEqual(adj_buy, base_buy)
        self.assertEqual(adj_sell, base_sell)
    
    def test_adjust_prices_for_skew_with_long_position(self):
        """Test price adjustment with long position (should make it easier to sell)"""
        base_buy = Decimal('0.58')
        base_sell = Decimal('0.60')
        
        # Set a long position
        self.inventory_manager.update_position('market1_YES', 'YES', Decimal('75'))
        
        adj_buy, adj_sell = self.strategy.adjust_prices_for_skew(base_buy, base_sell, 'market1_YES', 'YES')
        
        # With long position, we should lower our bid and raise our ask
        self.assertLess(adj_buy, base_buy)  # Lower bid
        self.assertGreater(adj_sell, base_sell)  # Higher ask
    
    def test_adjust_prices_for_skew_with_short_position(self):
        """Test price adjustment with short position (should make it easier to buy)"""
        base_buy = Decimal('0.58')
        base_sell = Decimal('0.60')
        
        # Set a short position
        self.inventory_manager.update_position('market1_YES', 'YES', Decimal('-75'))
        
        adj_buy, adj_sell = self.strategy.adjust_prices_for_skew(base_buy, base_sell, 'market1_YES', 'YES')
        
        # With short position, we should raise our bid and lower our ask
        self.assertGreater(adj_buy, base_buy)  # Higher bid
        self.assertLess(adj_sell, base_sell)  # Lower ask
    
    def test_generate_orders_basic(self):
        """Test basic order generation"""
        orders = self.strategy.generate_orders('market1', ['YES', 'NO'])
        
        # Should generate orders for both YES and NO outcomes
        self.assertGreater(len(orders), 0)
        
        # Check that all orders have valid properties
        for order in orders:
            self.assertIsInstance(order, Order)
            self.assertIn(order.side, ['buy', 'sell'])
            self.assertGreaterEqual(order.price, Decimal('0'))
            self.assertLessEqual(order.price, Decimal('1'))
            self.assertGreater(order.quantity, Decimal('0'))
    
    def test_create_batch_order_payload(self):
        """Test creating batch order payload"""
        from market_making_strategy import create_batch_order_payload
        
        orders = [
            Order('market1_YES', 'buy', Decimal('0.58'), Decimal('10')),
            Order('market1_NO', 'sell', Decimal('0.40'), Decimal('15'))
        ]
        
        payload = create_batch_order_payload(orders)
        
        self.assertIn('orders', payload)
        self.assertEqual(len(payload['orders']), 2)
        self.assertEqual(payload['orders'][0]['market_id'], 'market1_YES')
        self.assertEqual(payload['orders'][0]['side'], 'buy')
        self.assertEqual(float(payload['orders'][0]['price']), 0.58)
        self.assertEqual(float(payload['orders'][0]['quantity']), 10)


if __name__ == '__main__':
    unittest.main()