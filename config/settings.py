import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Polymarket API Configuration
    POLYMARKET_CLOB_API_URL = os.getenv(
        "POLYMARKET_CLOB_API_URL", 
        "https://clob.polymarket.com"
    )
    
    POLYMARKET_CHAIN_API_URL = os.getenv(
        "POLYMARKET_CHAIN_API_URL", 
        "https://polygon-mainnet.g.alchemy.com"
    )
    
    # Authentication
    L2_API_KEY = os.getenv("L2_API_KEY")
    PRIVATE_KEY = os.getenv("PRIVATE_KEY")
    WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
    
    # Rate limiting
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 500))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 10))  # seconds
    
    # Connection settings
    WEBSOCKET_RECONNECT_DELAY = int(os.getenv("WEBSOCKET_RECONNECT_DELAY", 5))  # seconds
    WEBSOCKET_HEARTBEAT_INTERVAL = int(os.getenv("WEBSOCKET_HEARTBEAT_INTERVAL", 30))  # seconds
    
    # CTF and Hedging Configuration
    CTF_ADDRESS = os.getenv("CTF_ADDRESS", "0x2cbecae5e324f0d1d524721b9d9a7be377e494d5")  # Gnosis ConditionalTokens contract address
    COLLATERAL_TOKEN_ADDRESS = os.getenv("COLLATERAL_TOKEN_ADDRESS", "0x2791bca1f2de4661ed88a30c99a7a9449aa84174")  # USDC on Polygon
    POSITION_PROXY_ADDRESS = os.getenv("POSITION_PROXY_ADDRESS", "0x0000000000000000000000000000000000000000")  # Default to zero address if not set

    # Validation
    def validate(self):
        required_fields = [
            "L2_API_KEY",
            "PRIVATE_KEY",
            "WALLET_ADDRESS"
        ]

        missing_fields = []
        for field in required_fields:
            if getattr(self, field) is None:
                missing_fields.append(field)

        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")