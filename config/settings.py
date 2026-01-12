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