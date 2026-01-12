import asyncio
import logging
from config.settings import Settings
from api_clients.clob_client import ClobClient
from api_clients.chain_client import ChainClient
from connection.connection_manager import ConnectionManager
from utils.rate_limiter import rate_limit_manager


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
        self.connection_manager = ConnectionManager(
            f"{self.settings.POLYMARKET_CLOB_API_URL.replace('https://', 'wss://')}/ws",
            self.settings
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
                # Get orderbook for the first market as an example
                first_market = markets[0]
                market_id = first_market.get('id')
                if market_id:
                    orderbook = await clob.get_orderbook(market_id)
                    logger.info(f"Retrieved orderbook for market {market_id}")
        
        # Keep the bot running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await self.shutdown()
    
    async def shutdown(self):
        """
        Shutdown the bot and clean up resources.
        """
        logger.info("Shutting down Polymarket Bot...")
        
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