import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config.settings import Settings
from api_clients.clob_client import ClobClient
from api_clients.chain_client import ChainClient
from connection.connection_manager import ConnectionManager
from order_book_engine import MarketDataIngestor


async def example_clob_client_usage():
    """
    Example of how to use the CLOB client for various operations.
    """
    print("=== CLOB Client Usage Examples ===")

    settings = Settings()
    settings.validate()  # This will raise an exception if required env vars are missing

    async with ClobClient(settings) as client:
        try:
            # 1. Get all available markets
            print("\n1. Retrieving all markets...")
            markets = await client.get_markets()
            print(f"Retrieved {len(markets)} markets")

            if markets:
                # Use the first market for examples
                first_market = markets[0]
                market_id = first_market.get('id', '')
                market_name = first_market.get('question', 'Unknown Market')

                print(f"Using market: {market_name} (ID: {market_id})")

                # 2. Get detailed market information
                print(f"\n2. Retrieving details for market {market_id}...")
                market_details = await client.get_market(market_id)
                print(f"Market details retrieved")

                # 3. Get the orderbook for this market
                print(f"\n3. Retrieving orderbook for market {market_id}...")
                orderbook = await client.get_orderbook(market_id)
                print(f"Orderbook retrieved with {len(orderbook.get('bids', []))} bids and {len(orderbook.get('asks', []))} asks")

                # 4. Get account balances
                print(f"\n4. Retrieving account balances...")
                balances = await client.get_balances()
                print(f"Account balances retrieved")

                # 5. Get open orders
                print(f"\n5. Retrieving open orders...")
                open_orders = await client.get_open_orders()
                print(f"Found {len(open_orders)} open orders")

                # 6. Get recent fills
                print(f"\n6. Retrieving recent fills...")
                fills = await client.get_fills()
                print(f"Retrieved {len(fills)} fills")

                # Example of placing an order (commented out to prevent actual trading)
                # print(f"\n7. Placing a sample order...")
                # try:
                #     order_result = await client.place_order(
                #         market_id=market_id,
                #         side="buy",
                #         price=0.5,  # Example price
                #         size=1.0    # Example size
                #     )
                #     print(f"Order placed successfully: {order_result}")
                # except Exception as e:
                #     print(f"Order placement failed (this is expected if parameters are invalid): {e}")

        except Exception as e:
            print(f"CLOB client example failed: {e}")


async def example_chain_client_usage():
    """
    Example of how to use the Chain client for blockchain operations.
    """
    print("\n=== Chain Client Usage Examples ===")

    settings = Settings()
    settings.validate()  # This will raise an exception if required env vars are missing

    async with ChainClient(settings) as client:
        try:
            # 1. Get wallet balance
            print("\n1. Retrieving wallet balance...")
            balance = await client.get_wallet_balance()
            print(f"Wallet balance retrieved")

            # 2. Get current gas price
            print(f"\n2. Retrieving current gas price...")
            gas_price = await client.get_gas_price()
            print(f"Current gas price retrieved")

            # 3. Get transaction history
            print(f"\n3. Retrieving transaction history...")
            tx_history = await client.get_transaction_history()
            print(f"Retrieved {len(tx_history)} transaction records")

            # 4. Get latest block information
            print(f"\n4. Retrieving latest block information...")
            block_info = await client.get_block_info()
            print(f"Latest block info retrieved")

        except Exception as e:
            print(f"Chain client example failed: {e}")


async def example_market_data_ingestor_usage():
    """
    Example of how to use the Market Data Ingestor for real-time orderbook data.
    """
    print("\n=== Market Data Ingestor Usage Examples ===")

    settings = Settings()
    settings.validate()

    # Get a market to subscribe to
    async with ClobClient(settings) as clob_client:
        markets = await clob_client.get_markets()
        if not markets:
            print("No markets available to demonstrate orderbook streaming")
            return

        first_market = markets[0]
        market_id = first_market.get('id', '')
        market_name = first_market.get('question', 'Unknown Market')

        if not market_id:
            print("No valid market ID found")
            return

        print(f"Setting up real-time orderbook for market: {market_name} (ID: {market_id})")

        # Create a connection manager
        connection_manager = ConnectionManager("wss://clob.polymarket.com/ws", settings)

        try:
            # Connect to WebSocket
            await connection_manager.connect()

            # Create market data ingestor
            market_ingestor = MarketDataIngestor(
                market_id,
                connection_manager=connection_manager,
                settings=settings
            )

            # Set up a callback to handle metrics
            def metrics_callback(metrics):
                print(f"Real-time metrics for {market_id}: Mid-price={metrics.get('mid_price')}, "
                      f"Spread={metrics.get('spread')}, Relative Spread={metrics.get('relative_spread'):.4f}%")

            market_ingestor.set_metrics_callback(metrics_callback)

            # Connect to the market's orderbook stream
            await market_ingestor.connect()

            print(f"Connected to real-time orderbook for {market_id}")
            print("Waiting for orderbook updates (this will run for 10 seconds)...")

            # Run for 10 seconds to demonstrate real-time updates
            await asyncio.sleep(10)

            # Disconnect
            await market_ingestor.disconnect()
            connection_manager.stop()

        except Exception as e:
            print(f"Market data ingestor example failed: {e}")
            if 'connection_manager' in locals():
                connection_manager.stop()


async def example_complete_bot_workflow():
    """
    Example of a complete bot workflow combining all components.
    """
    print("\n=== Complete Bot Workflow Example ===")

    settings = Settings()
    settings.validate()

    # Initialize all components
    clob_client = ClobClient(settings)
    chain_client = ChainClient(settings)
    connection_manager = ConnectionManager("wss://clob.polymarket.com/ws", settings)

    try:
        # Connect to WebSocket
        await connection_manager.connect()

        # Get markets
        async with clob_client as clob:
            markets = await clob.get_markets()
            if not markets:
                print("No markets available")
                return

            # Use the first market
            first_market = markets[0]
            market_id = first_market.get('id', '')
            market_name = first_market.get('question', 'Unknown Market')

            if not market_id:
                print("No valid market ID found")
                return

            print(f"Selected market: {market_name} (ID: {market_id})")

            # Get initial market data
            orderbook = await clob.get_orderbook(market_id)
            print(f"Initial orderbook retrieved")

            # Set up real-time orderbook monitoring
            market_ingestor = MarketDataIngestor(
                market_id,
                connection_manager=connection_manager,
                settings=settings
            )

            # Track market metrics
            metrics_updates = []

            def metrics_callback(metrics):
                metrics_updates.append(metrics)
                print(f"Market update: Mid-price={metrics.get('mid_price')}, "
                      f"Spread={metrics.get('spread'):.6f}")

            market_ingestor.set_metrics_callback(metrics_callback)
            await market_ingestor.connect()

            # Start consuming data
            consume_task = asyncio.create_task(market_ingestor.consume_data())
            calc_task = asyncio.create_task(market_ingestor.start_periodic_calculations(interval_ms=500))

            print("Monitoring market for 15 seconds...")
            await asyncio.sleep(15)

            # Stop monitoring
            await market_ingestor.disconnect()

            # Cancel tasks
            consume_task.cancel()
            calc_task.cancel()

            print(f"Collected {len(metrics_updates)} market metric updates")

    except Exception as e:
        print(f"Complete bot workflow example failed: {e}")
    finally:
        # Clean up
        connection_manager.stop()


async def run_examples():
    """
    Run all examples to demonstrate the API clients.
    """
    print("Running examples for Polymarket Bot components...\n")

    await example_clob_client_usage()
    await example_chain_client_usage()
    await example_market_data_ingestor_usage()
    await example_complete_bot_workflow()

    print("\nAll examples completed!")


if __name__ == "__main__":
    asyncio.run(run_examples())