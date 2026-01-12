# Polymarket Market Maker Bot - Architecture & Implementation Guide

## Overview

This document describes the architecture and implementation of the Polymarket market maker bot. The bot is designed to connect to Polymarket's CLOB (Central Limit Order Book) and Chain APIs to facilitate high-frequency trading operations.

## Architecture

### Project Structure

```
polymarket-mm-bot/
├── api_clients/           # API client implementations
│   ├── __init__.py
│   ├── clob_client.py     # CLOB API client
│   └── chain_client.py    # Chain API client
├── connection/            # Connection management
│   ├── __init__.py
│   └── connection_manager.py # WebSocket connection manager
├── utils/                 # Utility modules
│   ├── __init__.py
│   └── rate_limiter.py    # Rate limiting implementation
├── config/                # Configuration management
│   ├── __init__.py
│   └── settings.py        # Settings and environment variables
├── main.py                # Main application entry point
├── test_bot.py            # Test implementation
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
└── .env                   # Environment variables (not committed)
```

## Components

### 1. Configuration (`config/settings.py`)

The settings module handles configuration and environment variables:

- API endpoints (CLOB and Chain)
- Authentication credentials (L2 API Key, private key, wallet address)
- Rate limiting parameters
- Connection settings (reconnect delay, heartbeat interval)

### 2. Rate Limiter (`utils/rate_limiter.py`)

Implements a token bucket rate limiting algorithm to comply with Polymarket's API limits:

- Configurable max requests and time window
- Async acquisition of request tokens
- Global rate limit manager for different API endpoints

### 3. Connection Manager (`connection/connection_manager.py`)

Manages WebSocket connections with:

- Automatic reconnection on disconnection
- Heartbeat/ping functionality to maintain connection
- Message handling and routing
- Rate limiting for WebSocket messages

### 4. CLOB Client (`api_clients/clob_client.py`)

Handles interactions with Polymarket's CLOB API:

- Authentication using private key signatures
- Rate limiting for API requests
- Order placement, cancellation, and management
- Market data retrieval (markets, orderbooks, fills)
- Account balance queries

### 5. Chain Client (`api_clients/chain_client.py`)

Handles blockchain interactions:

- Wallet balance queries
- Transaction history
- Gas price estimation
- Transaction sending
- Block information retrieval
- Contract event monitoring

## Usage

### Environment Setup

Create a `.env` file with the following variables:

```bash
# Polymarket API Configuration
POLYMARKET_CLOB_API_URL=https://clob.polymarket.com
POLYMARKET_CHAIN_API_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY

# Authentication
L2_API_KEY=your_l2_api_key_here
PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=your_wallet_address_here

# Rate limiting
RATE_LIMIT_REQUESTS=500
RATE_LIMIT_WINDOW=10

# Connection settings
WEBSOCKET_RECONNECT_DELAY=5
WEBSOCKET_HEARTBEAT_INTERVAL=30
```

### Installation

```bash
pip install -r requirements.txt
```

### Running the Bot

```bash
python main.py
```

## Key Features

### Authentication
- Secure authentication using L2 API Key and private key
- Message signing for API requests
- Proper header formatting

### Rate Limiting
- Compliance with Polymarket's rate limits (500 requests/10s for orders)
- Separate rate limiters for different API endpoints
- Automatic request throttling

### Connection Management
- WebSocket auto-reconnection with exponential backoff
- Heartbeat mechanism to maintain connection
- Proper error handling and recovery

### Security
- Private key never exposed in logs
- Secure message signing
- Environment-based configuration

## API Endpoints Implemented

### CLOB Client
- GET /markets - Retrieve all available markets
- GET /markets/{market_id} - Get specific market details
- GET /markets/{market_id}/orderbook - Get market orderbook
- POST /orders - Place a new order
- DELETE /orders/{order_id} - Cancel an order
- DELETE /orders/all - Cancel all orders
- GET /orders/open - Get open orders
- GET /orders/{order_id}/status - Get order status
- GET /fills - Get account fills
- GET /balances - Get account balances

### Chain Client
- eth_getBalance - Get wallet balance
- eth_getTransactionCount - Get transaction count
- eth_gasPrice - Get current gas price
- eth_estimateGas - Estimate gas for transactions
- eth_sendRawTransaction - Send transactions
- eth_getBlockByNumber - Get block information
- eth_getLogs - Get contract events

## Error Handling

- Comprehensive error handling for network issues
- Automatic reconnection for WebSocket connections
- Graceful degradation when API limits are reached
- Detailed logging for debugging

## Testing

A test file (`test_bot.py`) is provided to verify the functionality of each component before running the full bot.

## Security Considerations

- Store private keys securely, never commit to version control
- Use environment variables for sensitive information
- Implement proper access controls
- Regularly rotate API keys
- Monitor for suspicious activity

## Performance Considerations

- Asynchronous implementation for high-frequency operations
- Connection pooling for HTTP requests
- Efficient data structures for order management
- Proper resource cleanup