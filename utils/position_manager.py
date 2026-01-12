"""
Position Manager for managing YES/NO token positions and hedging using CTF
"""
import asyncio
import logging
from typing import Dict, Optional
from decimal import Decimal
from api_clients.clob_client import CLOBClient
from api_clients.ctf_client import CTFClient


class PositionManager:
    """
    Manages YES/NO token positions for a specific market and provides hedging functionality
    using the Gnosis Conditional Tokens Framework (CTF).
    """
    
    def __init__(self,
                 ctf_client: CTFClient,
                 clob_client: CLOBClient,
                 market_id: str,
                 condition_id: str,
                 collateral_token_address: str,
                 position_proxy_address: str):
        """
        Initialize the Position Manager

        Args:
            ctf_client: Client for interacting with the Conditional Tokens Framework
            clob_client: Client for interacting with the CLOB
            market_id: Unique identifier for the market
            condition_id: Condition ID for the conditional tokens
            collateral_token_address: Address of the collateral token (USDC)
            position_proxy_address: Address of the position proxy contract
        """
        self.ctf_client = ctf_client
        self.clob_client = clob_client
        self.market_id = market_id
        self.condition_id = condition_id
        self.collateral_token_address = collateral_token_address
        self.position_proxy_address = position_proxy_address
        self.logger = logging.getLogger(__name__)

        # Track positions
        self.yes_balance = Decimal('0')
        self.no_balance = Decimal('0')
        self.collateral_balance = Decimal('0')
    
    def update_position(self, outcome: str, amount: Decimal) -> None:
        """
        Update the position for a specific outcome
        
        Args:
            outcome: 'YES' or 'NO'
            amount: Amount to add to the position (can be negative for sells)
        """
        if outcome.upper() == 'YES':
            self.yes_balance += amount
        elif outcome.upper() == 'NO':
            self.no_balance += amount
        else:
            raise ValueError(f"Invalid outcome: {outcome}. Expected 'YES' or 'NO'")
        
        self.logger.info(f"Updated {outcome} position by {amount}. New balance: YES={self.yes_balance}, NO={self.no_balance}")
    
    def get_available_hedge_amount(self) -> Decimal:
        """
        Calculate the maximum amount that can be hedged (merged)
        
        Returns:
            The minimum of YES and NO balances (the amount that can be hedged)
        """
        return min(self.yes_balance, self.no_balance)
    
    def can_merge(self) -> bool:
        """
        Check if positions can be merged (have equal or unequal amounts of YES and NO)
        
        Returns:
            True if there are both YES and NO tokens to merge
        """
        return self.yes_balance > 0 and self.no_balance > 0
    
    def can_split(self) -> bool:
        """
        Check if collateral can be split into YES/NO tokens
        
        Returns:
            True if there is collateral available to split
        """
        return self.collateral_balance > 0
    
    def merge_positions(self, amount: Optional[Decimal] = None) -> Dict:
        """
        Merge equal amounts of YES and NO tokens into collateral (USDC)

        Args:
            amount: Optional amount to merge. If None, merges the maximum possible

        Returns:
            Transaction result dictionary
        """
        if amount is None:
            amount = self.get_available_hedge_amount()

        if amount <= 0:
            self.logger.warning("No positions available to merge")
            return {"success": False, "message": "No positions available to merge"}

        # Determine the actual amount to merge (limited by available balances)
        actual_amount = min(amount, self.yes_balance, self.no_balance)

        if actual_amount <= 0:
            self.logger.warning("Insufficient positions to merge")
            return {"success": False, "message": "Insufficient positions to merge"}

        try:
            # Use the CTF client to merge positions
            # For binary outcomes (YES/NO), partition is [1, 1] representing both outcomes
            result = asyncio.run(self.ctf_client.merge_positions(
                condition_id=self.condition_id,
                partition=[1, 2],  # For binary outcomes: YES=1, NO=2
                amount=int(actual_amount * 10**6)  # Assuming 6 decimals for USDC
            ))

            if result.get("success"):
                # Update local balances
                self.yes_balance -= actual_amount
                self.no_balance -= actual_amount
                self.collateral_balance += actual_amount  # Assuming 1:1 conversion

                self.logger.info(f"Successfully merged {actual_amount} YES and NO tokens into collateral")

                return {
                    "success": True,
                    "amount_merged": actual_amount,
                    "transaction_hash": result.get("transaction_hash"),
                    "new_balances": {
                        "yes": self.yes_balance,
                        "no": self.no_balance,
                        "collateral": self.collateral_balance
                    }
                }
            else:
                self.logger.error(f"Failed to merge positions: {result.get('message', 'Unknown error')}")
                return {"success": False, "message": result.get("message", "Unknown error")}

        except Exception as e:
            self.logger.error(f"Error merging positions: {str(e)}")
            return {"success": False, "message": f"Exception occurred: {str(e)}"}
    
    def split_collateral(self, amount: Optional[Decimal] = None) -> Dict:
        """
        Split collateral (USDC) into equal amounts of YES and NO tokens

        Args:
            amount: Optional amount of collateral to split. If None, splits all available

        Returns:
            Transaction result dictionary
        """
        if amount is None:
            amount = self.collateral_balance

        if amount <= 0:
            self.logger.warning("No collateral available to split")
            return {"success": False, "message": "No collateral available to split"}

        # Determine the actual amount to split (limited by available collateral)
        actual_amount = min(amount, self.collateral_balance)

        if actual_amount <= 0:
            self.logger.warning("Insufficient collateral to split")
            return {"success": False, "message": "Insufficient collateral to split"}

        try:
            # Use the CTF client to split collateral into YES/NO tokens
            # For binary outcomes (YES/NO), partition is [1, 1] representing both outcomes equally
            result = asyncio.run(self.ctf_client.split_position(
                condition_id=self.condition_id,
                partition=[1, 2],  # For binary outcomes: YES=1, NO=2
                amount=int(actual_amount * 10**6)  # Assuming 6 decimals for USDC
            ))

            if result.get("success"):
                # Update local balances
                self.collateral_balance -= actual_amount
                self.yes_balance += actual_amount
                self.no_balance += actual_amount  # Equal amounts of YES and NO

                self.logger.info(f"Successfully split {actual_amount} collateral into YES and NO tokens")

                return {
                    "success": True,
                    "amount_split": actual_amount,
                    "transaction_hash": result.get("transaction_hash"),
                    "new_balances": {
                        "yes": self.yes_balance,
                        "no": self.no_balance,
                        "collateral": self.collateral_balance
                    }
                }
            else:
                self.logger.error(f"Failed to split collateral: {result.get('message', 'Unknown error')}")
                return {"success": False, "message": result.get("message", "Unknown error")}

        except Exception as e:
            self.logger.error(f"Error splitting collateral: {str(e)}")
            return {"success": False, "message": f"Exception occurred: {str(e)}"}
    
    def get_position_summary(self) -> Dict:
        """
        Get a summary of current positions
        
        Returns:
            Dictionary with current position balances
        """
        return {
            "market_id": self.market_id,
            "yes_balance": self.yes_balance,
            "no_balance": self.no_balance,
            "collateral_balance": self.collateral_balance,
            "hedgeable_amount": self.get_available_hedge_amount(),
            "net_exposure": self.yes_balance - self.no_balance
        }
    
    def rebalance_to_neutral(self) -> Dict:
        """
        Automatically rebalance positions to neutral (equal YES and NO)
        
        Returns:
            Result of rebalancing operations
        """
        if self.yes_balance == self.no_balance:
            return {"success": True, "message": "Positions already balanced"}
        
        result = {
            "merge_result": None,
            "split_result": None,
            "final_balances": None
        }
        
        # First, merge any hedgeable positions
        hedgeable_amount = self.get_available_hedge_amount()
        if hedgeable_amount > 0:
            result["merge_result"] = self.merge_positions(hedgeable_amount)
        
        # Then, if needed, split collateral to balance positions
        net_exposure = self.yes_balance - self.no_balance
        if abs(net_exposure) > 0 and self.collateral_balance > 0:
            # Need to split collateral to balance positions
            split_amount = abs(net_exposure) / 2
            if split_amount <= self.collateral_balance:
                result["split_result"] = self.split_collateral(split_amount)
        
        result["final_balances"] = self.get_position_summary()
        return result