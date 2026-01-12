# Polymarket Market Maker Bot

A high-frequency trading bot for Polymarket using CLOB and Chain APIs.

## Architecture

```
polymarket-mm-bot/
├── api_clients/
│   ├── __init__.py
│   ├── clob_client.py
│   └── chain_client.py
├── connection/
│   ├── __init__.py
│   └── connection_manager.py
├── utils/
│   ├── __init__.py
│   └── rate_limiter.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── main.py
└── requirements.txt
```

## Features

- REST client for placing/cancelling orders
- WebSocket client for streaming Orderbook (L2) data
- Connection manager with heartbeat and auto-reconnect
- Rate limiter compliant with Polymarket limits
- Secure authentication with L2 API Key and private key