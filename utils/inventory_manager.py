from typing import Dict, Optional
from decimal import Decimal


class InventoryManager:
    """
    Manages the trading bot's inventory/positions across different markets and outcomes
    """
    
    def __init__(self):
        # Dictionary to store positions: {(market_id, outcome): position_size}
        self.positions: Dict[tuple, Decimal] = {}
    
    def update_position(self, market_id: str, outcome: str, delta: Decimal) -> Decimal:
        """
        Update the position for a specific market and outcome
        
        Args:
            market_id: The market identifier
            outcome: The outcome ('YES' or 'NO')
            delta: Change in position (positive for increase, negative for decrease)
            
        Returns:
            New position size
        """
        key = (market_id, outcome)
        current_position = self.positions.get(key, Decimal('0'))
        new_position = current_position + delta
        self.positions[key] = new_position
        return new_position
    
    def get_position(self, market_id: str, outcome: str) -> Decimal:
        """
        Get the current position for a specific market and outcome
        
        Args:
            market_id: The market identifier
            outcome: The outcome ('YES' or 'NO')
            
        Returns:
            Current position size
        """
        key = (market_id, outcome)
        return self.positions.get(key, Decimal('0'))
    
    def get_all_positions(self) -> Dict[tuple, Decimal]:
        """
        Get all current positions
        
        Returns:
            Dictionary of all positions
        """
        return self.positions.copy()
    
    def reset_position(self, market_id: str, outcome: str) -> None:
        """
        Reset the position for a specific market and outcome to zero
        
        Args:
            market_id: The market identifier
            outcome: The outcome ('YES' or 'NO')
        """
        key = (market_id, outcome)
        self.positions[key] = Decimal('0')
    
    def get_net_position(self, market_id: str) -> Decimal:
        """
        Get the net position for a market (YES position + NO position)
        Assuming that YES and NO positions offset each other
        
        Args:
            market_id: The market identifier
            
        Returns:
            Net position for the market
        """
        yes_position = self.get_position(market_id, 'YES')
        no_position = self.get_position(market_id, 'NO')
        return yes_position + no_position