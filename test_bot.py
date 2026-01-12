import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config.settings import Settings
from api_clients.clob_client import ClobClient
from api_clients.chain_client import ChainClient
from connection.connection_manager import ConnectionManager


async def test_clob_client():
    """
    Test the CLOB client functionality.
    """
    print("Testing CLOB Client...")
    
    settings = Settings()
    settings.validate()  # This will raise an exception if required env vars are missing
    
    async with ClobClient(settings) as client:
        try:
            # Test getting markets
            markets = await client.get_markets()
            print(f"Retrieved {len(markets)} markets")
            
            if markets:
                # Test getting orderbook for first market
                first_market = markets[0]
                market_id = first_market.get('id', '')
                if market_id:
                    orderbook = await client.get_orderbook(market_id)
                    print(f"Retrieved orderbook for market {market_id}")
                    
                    # Test getting market details
                    market_details = await client.get_market(market_id)
                    print(f"Retrieved details for market {market_id}")
            
            # Test getting balances
            balances = await client.get_balances()
            print(f"Retrieved account balances")
            
        except Exception as e:
            print(f"CLOB client test failed: {e}")


async def test_chain_client():
    """
    Test the Chain client functionality.
    """
    print("\nTesting Chain Client...")
    
    settings = Settings()
    settings.validate()  # This will raise an exception if required env vars are missing
    
    async with ChainClient(settings) as client:
        try:
            # Test getting wallet balance
            balance = await client.get_wallet_balance()
            print(f"Retrieved wallet balance")
            
            # Test getting gas price
            gas_price = await client.get_gas_price()
            print(f"Retrieved current gas price")
            
        except Exception as e:
            print(f"Chain client test failed: {e}")


async def test_connection_manager():
    """
    Test the Connection Manager functionality.
    """
    print("\nTesting Connection Manager...")
    
    settings = Settings()
    settings.validate()  # This will raise an exception if required env vars are missing
    
    # Note: This is a simplified test - in practice, you'd need a valid WebSocket endpoint
    # For now, we'll just test the instantiation
    try:
        conn_manager = ConnectionManager(
            f"wss://clob.polymarket.com/ws",  # This is likely not the real WS endpoint
            settings
        )
        print("Connection manager instantiated successfully")
        
        # Clean up
        conn_manager.stop()
    except Exception as e:
        print(f"Connection manager test failed: {e}")


async def run_tests():
    """
    Run all tests.
    """
    print("Running tests for Polymarket Bot components...\n")
    
    await test_clob_client()
    await test_chain_client()
    await test_connection_manager()
    
    print("\nTests completed!")


if __name__ == "__main__":
    asyncio.run(run_tests())