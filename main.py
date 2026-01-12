import asyncio
import logging
from decimal import Decimal
from config.settings import Settings
from api_clients.clob_client import ClobClient
from api_clients.chain_client import ChainClient
from connection.connection_manager import ConnectionManager
from order_book_engine import MarketDataIngestor, LocalOrderBook
from utils.rate_limiter import rate_limit_manager
from market_making_strategy import MarketMakingStrategy, MarketMakingConfig, create_batch_order_payload
from utils.inventory_manager import InventoryManager


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PolymarketBot:
    """
    Main class for the Polymarket market maker bot.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.clob_client = None
        self.chain_client = None
        self.connection_manager = None
        self.market_data_ingestors = []
        self.local_order_books = {}  # Track local order books for each market
        self.inventory_manager = InventoryManager()
        self.market_making_strategies = {}  # Track strategies for each market

    async def initialize(self):
        """
        Initialize all clients and connections.
        """
        logger.info("Initializing Polymarket Bot...")

        # Validate settings
        self.settings.validate()

        # Initialize clients
        self.clob_client = ClobClient(self.settings)
        self.chain_client = ChainClient(self.settings)

        # Initialize connection manager for WebSocket
        ws_url = f"wss://clob.polymarket.com/ws"
        self.connection_manager = ConnectionManager(ws_url, self.settings)

        # Initialize market making strategy configuration
        self.mm_config = MarketMakingConfig(
            target_spread=Decimal('0.002'),  # 20 basis points
            max_order_size=Decimal('100'),
            min_order_size=Decimal('1'),
            inventory_skew_factor=Decimal('0.5'),
            max_inventory_threshold=Decimal('1000'),
            num_levels=3
        )

        logger.info("Initialization complete")

    async def start(self):
        """
        Start the bot operations.
        """
        logger.info("Starting Polymarket Bot...")

        # Connect to WebSocket
        await self.connection_manager.connect()

        # Example: Get markets and orderbook
        async with self.clob_client as clob:
            markets = await clob.get_markets()
            logger.info(f"Retrieved {len(markets)} markets")

            if markets:
                # Process first few markets for market making
                for i, market in enumerate(markets[:3]):  # Limit to first 3 markets for demo
                    market_id = market.get('id')
                    if market_id:
                        logger.info(f"Setting up market making for market {market_id}")

                        # Initialize local order book for this market
                        local_order_book = LocalOrderBook()
                        self.local_order_books[market_id] = local_order_book

                        # Initialize market making strategy for this market
                        strategy = MarketMakingStrategy(
                            local_order_book,
                            self.inventory_manager,
                            self.mm_config
                        )
                        self.market_making_strategies[market_id] = strategy

                        # Get initial orderbook for the market
                        orderbook = await clob.get_orderbook(market_id)
                        logger.info(f"Retrieved orderbook for market {market_id}")

                        # Initialize market data ingestor for this market
                        market_ingestor = MarketDataIngestor(
                            market_id,
                            connection_manager=self.connection_manager,
                            settings=self.settings
                        )

                        # Set up metrics callback
                        market_ingestor.set_metrics_callback(self._on_market_metrics)

                        # Connect to the market's orderbook stream
                        await market_ingestor.connect()

                        # Add to our list of ingestors
                        self.market_data_ingestors.append(market_ingestor)

                        # Start consuming data
                        asyncio.create_task(market_ingestor.consume_data())
                        asyncio.create_task(market_ingestor.start_periodic_calculations())

                        # Start market making loop for this market
                        asyncio.create_task(self.run_market_making_strategy(market_id, clob))

        # Keep the bot running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await self.shutdown()

    async def run_market_making_strategy(self, market_id: str, clob_client):
        """
        Run the market making strategy for a specific market
        """
        logger.info(f"Starting market making strategy for market {market_id}")

        # Wait a bit for initial data to populate
        await asyncio.sleep(2)

        while True:
            try:
                # Get the strategy for this market
                strategy = self.market_making_strategies.get(market_id)
                if not strategy:
                    logger.warning(f"No strategy found for market {market_id}")
                    break

                # Generate orders based on current market conditions and inventory
                orders = strategy.generate_orders(market_id, ['YES', 'NO'])  # Assuming YES/NO outcomes

                if orders:
                    logger.info(f"Generated {len(orders)} orders for market {market_id}")

                    # Create batch order payload
                    batch_payload = create_batch_order_payload(orders)

                    # In a real implementation, we would submit these orders to the exchange
                    # await clob_client.batch_place_orders(batch_payload)

                    logger.info(f"Would submit {len(batch_payload['orders'])} batch orders for market {market_id}")

                # Wait before the next iteration
                await asyncio.sleep(self.mm_config.refresh_interval)

            except Exception as e:
                logger.error(f"Error in market making strategy for market {market_id}: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying

    def _on_market_metrics(self, metrics):
        """
        Callback for market metrics updates.
        """
        logger.info(f"Market Metrics: {metrics}")

    async def shutdown(self):
        """
        Shutdown the bot and clean up resources.
        """
        logger.info("Shutting down Polymarket Bot...")

        # Stop all market data ingestors
        for ingestor in self.market_data_ingestors:
            await ingestor.disconnect()

        # Stop connection manager
        if self.connection_manager:
            self.connection_manager.stop()

        logger.info("Shutdown complete")


async def main():
    """
    Main entry point for the application.
    """
    settings = Settings()

    bot = PolymarketBot(settings)
    await bot.initialize()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())