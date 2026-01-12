"""
Example usage of the PositionManager with CTF hedging
"""
import asyncio
import logging
from decimal import Decimal
from api_clients.chain_client import ChainClient
from api_clients.clob_client import CLOBClient
from api_clients.ctf_client import CTFClient
from utils.position_manager import PositionManager
from config.settings import Settings


async def example_usage():
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Load settings
    settings = Settings()
    
    # Initialize clients
    async with ChainClient(settings) as chain_client:
        clob_client = CLOBClient(settings)  # Assuming CLOBClient doesn't need async context
        
        # Initialize CTF client
        ctf_client = CTFClient(
            chain_client=chain_client,
            ctf_address=settings.CTF_ADDRESS,  # You would need to add this to settings
            collateral_token_address=settings.COLLATERAL_TOKEN_ADDRESS,  # You would need to add this to settings
            position_proxy_address=settings.POSITION_PROXY_ADDRESS  # You would need to add this to settings
        )
        
        # Initialize Position Manager for a specific market
        position_manager = PositionManager(
            ctf_client=ctf_client,
            clob_client=clob_client,
            market_id="0x1234567890abcdef",  # Example market ID
            condition_id="0xabcdef1234567890",  # Example condition ID
            collateral_token_address=settings.COLLATERAL_TOKEN_ADDRESS,
            position_proxy_address=settings.POSITION_PROXY_ADDRESS
        )
        
        # Simulate some trading activity - buying and selling YES/NO tokens
        print("Initial position:", position_manager.get_position_summary())
        
        # Buy 100 YES tokens
        position_manager.update_position('YES', Decimal('100'))
        print("After buying 100 YES:", position_manager.get_position_summary())
        
        # Buy 80 NO tokens
        position_manager.update_position('NO', Decimal('80'))
        print("After buying 80 NO:", position_manager.get_position_summary())
        
        # Now we have 100 YES and 80 NO, so we can hedge 80 of each
        print(f"Available to hedge: {position_manager.get_available_hedge_amount()}")
        
        # Merge the hedgeable positions (80 YES and 80 NO -> 80 USDC)
        merge_result = position_manager.merge_positions()
        print("Merge result:", merge_result)
        print("After merging:", position_manager.get_position_summary())
        
        # Now we have 20 YES, 0 NO, and 80 USDC collateral
        # We can split the collateral to rebalance
        split_result = position_manager.split_collateral(Decimal('20'))  # Split 20 USDC to get 20 YES and 20 NO
        print("Split result:", split_result)
        print("After splitting:", position_manager.get_position_summary())
        
        # Try to rebalance to neutral automatically
        rebalance_result = position_manager.rebalance_to_neutral()
        print("Rebalance result:", rebalance_result)


if __name__ == "__main__":
    asyncio.run(example_usage())