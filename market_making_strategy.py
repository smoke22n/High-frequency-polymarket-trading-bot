import math
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from dataclasses import dataclass
from order_book_engine import LocalOrderBook
from utils.inventory_manager import InventoryManager


@dataclass
class Order:
    """Represents a single order"""
    market_id: str
    side: str  # 'buy' or 'sell'
    price: Decimal
    quantity: Decimal
    order_type: str = 'limit'


@dataclass
class MarketMakingConfig:
    """Configuration for market making strategy"""
    target_spread: Decimal = Decimal('0.002')  # 20 basis points = 0.2%
    max_order_size: Decimal = Decimal('100')
    min_order_size: Decimal = Decimal('1')
    inventory_skew_factor: Decimal = Decimal('0.5')  # How much to adjust prices based on inventory
    max_inventory_threshold: Decimal = Decimal('1000')  # Max position size before aggressive rebalancing
    num_levels: int = 3  # Number of price levels to quote
    refresh_interval: float = 1.0  # Refresh interval in seconds


class MarketMakingStrategy:
    """
    High Frequency Market Making Strategy
    
    This strategy places orders to capture the spread while managing inventory risk.
    It adjusts quoting prices based on inventory skew to maintain neutrality.
    """
    
    def __init__(self, 
                 local_order_book: LocalOrderBook,
                 inventory_manager: InventoryManager,
                 config: MarketMakingConfig):
        """
        Initialize the market making strategy
        
        Args:
            local_order_book: The local order book with market data
            inventory_manager: Manages current positions/inventory
            config: Configuration parameters for the strategy
        """
        self.local_order_book = local_order_book
        self.inventory_manager = inventory_manager
        self.config = config
        
    def calculate_fair_price(self, market_id: str) -> Optional[Decimal]:
        """
        Calculate the fair mid-price for a market based on the order book
        
        Args:
            market_id: The market identifier
            
        Returns:
            Fair mid-price or None if insufficient data
        """
        bids = self.local_order_book.get_top_bids(market_id, 1)
        asks = self.local_order_book.get_top_asks(market_id, 1)
        
        if not bids or not asks:
            return None
            
        best_bid = bids[0][0]  # Price is first element of tuple (price, quantity)
        best_ask = asks[0][0]
        
        fair_price = (best_bid + best_ask) / 2
        return fair_price
    
    def calculate_inventory_skew(self, market_id: str, outcome: str) -> Decimal:
        """
        Calculate inventory skew for a specific market outcome
        
        Args:
            market_id: The market identifier
            outcome: The outcome ('YES' or 'NO')
            
        Returns:
            Skew factor (-1 to 1), negative if over-weighted in outcome, positive if under-weighted
        """
        position = self.inventory_manager.get_position(market_id, outcome)
        total_position = abs(position)
        
        if total_position == 0:
            return Decimal('0')
        
        # Normalize the skew based on maximum threshold
        normalized_skew = min(total_position / self.config.max_inventory_threshold, 1)
        
        # Return signed skew based on position direction
        if position < 0:  # Short position
            return Decimal(str(-normalized_skew))
        else:  # Long position
            return Decimal(str(normalized_skew))
    
    def adjust_prices_for_skew(self, 
                              base_buy_price: Decimal, 
                              base_sell_price: Decimal, 
                              market_id: str, 
                              outcome: str) -> Tuple[Decimal, Decimal]:
        """
        Adjust buy/sell prices based on inventory skew
        
        Args:
            base_buy_price: Base buy price without skew adjustment
            base_sell_price: Base sell price without skew adjustment
            market_id: The market identifier
            outcome: The outcome ('YES' or 'NO')
            
        Returns:
            Adjusted (buy_price, sell_price)
        """
        skew = self.calculate_inventory_skew(market_id, outcome)
        
        if skew == 0:
            return base_buy_price, base_sell_price
        
        # If we're long (positive skew), lower our bid and raise our ask to encourage selling
        if skew > 0:
            # Lower bid price to make buying less attractive
            adjusted_buy = base_buy_price * (1 - abs(skew) * self.config.inventory_skew_factor)
            # Raise ask price to make selling more attractive
            adjusted_sell = base_sell_price * (1 + abs(skew) * self.config.inventory_skew_factor)
        else:
            # If we're short (negative skew), raise our bid and lower our ask to encourage buying
            # Raise bid price to make buying more attractive
            adjusted_buy = base_buy_price * (1 + abs(skew) * self.config.inventory_skew_factor)
            # Lower ask price to make selling less attractive
            adjusted_sell = base_sell_price * (1 - abs(skew) * self.config.inventory_skew_factor)
        
        # Ensure we don't cross the spread (buy price should be less than sell price)
        if adjusted_buy >= adjusted_sell:
            mid_price = (adjusted_buy + adjusted_sell) / 2
            half_spread = self.config.target_spread / 2
            adjusted_buy = mid_price - half_spread
            adjusted_sell = mid_price + half_spread
        
        return adjusted_buy, adjusted_sell
    
    def generate_orders(self, market_id: str, outcomes: List[str]) -> List[Order]:
        """
        Generate a batch of limit orders for market making
        
        Args:
            market_id: The market identifier
            outcomes: List of outcomes to quote for (e.g., ['YES', 'NO'])
            
        Returns:
            List of orders to place
        """
        orders = []
        
        for outcome in outcomes:
            # Calculate fair price for this outcome
            fair_price = self.calculate_fair_price(f"{market_id}_{outcome}")
            if fair_price is None:
                continue
                
            # Calculate base buy and sell prices based on target spread
            half_spread = self.config.target_spread / 2
            base_buy_price = fair_price - half_spread
            base_sell_price = fair_price + half_spread
            
            # Apply inventory skew adjustment
            adjusted_buy_price, adjusted_sell_price = self.adjust_prices_for_skew(
                base_buy_price, base_sell_price, market_id, outcome
            )
            
            # Ensure prices are valid (between 0 and 1 for binary options)
            adjusted_buy_price = max(Decimal('0'), min(Decimal('1'), adjusted_buy_price))
            adjusted_sell_price = max(Decimal('0'), min(Decimal('1'), adjusted_sell_price))
            
            # Generate multiple levels of orders
            for level in range(self.config.num_levels):
                # Calculate order size (decrease size for deeper levels)
                level_multiplier = Decimal(str(1.0 - (level * 0.2)))  # Reduce size by 20% per level
                order_size = min(
                    self.config.max_order_size * level_multiplier,
                    max(self.config.min_order_size, 
                        self.config.max_order_size * level_multiplier)
                )
                
                # Create buy order (bid)
                buy_price = adjusted_buy_price - (half_spread * Decimal(str(level * 0.1)))
                buy_price = max(Decimal('0.001'), min(Decimal('0.999'), buy_price))  # Keep within bounds
                if buy_price < adjusted_sell_price:  # Only place if profitable
                    orders.append(Order(
                        market_id=f"{market_id}_{outcome}",
                        side='buy',
                        price=buy_price,
                        quantity=order_size
                    ))
                
                # Create sell order (ask)
                sell_price = adjusted_sell_price + (half_spread * Decimal(str(level * 0.1)))
                sell_price = max(Decimal('0.001'), min(Decimal('0.999'), sell_price))  # Keep within bounds
                if sell_price > adjusted_buy_price:  # Only place if profitable
                    orders.append(Order(
                        market_id=f"{market_id}_{outcome}",
                        side='sell',
                        price=sell_price,
                        quantity=order_size
                    ))
        
        return orders
    
    def update_inventory_and_adjust_quotes(self):
        """
        Update inventory and adjust quotes based on current positions
        This should be called periodically to maintain market neutrality
        """
        # The inventory manager should be updated externally as trades happen
        # This method could be used to trigger recalculation of quotes
        pass


def create_batch_order_payload(orders: List[Order]) -> dict:
    """
    Create a batch order payload compatible with Polymarket's POST /orders endpoint
    
    Args:
        orders: List of Order objects to batch
        
    Returns:
        Dictionary payload for batch order submission
    """
    order_list = []
    for order in orders:
        order_dict = {
            'market_id': order.market_id,
            'side': order.side,
            'price': float(order.price),
            'quantity': float(order.quantity),
            'type': order.order_type
        }
        order_list.append(order_dict)
    
    return {
        'orders': order_list
    }